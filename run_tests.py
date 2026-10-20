#!/usr/bin/env python3
"""Run the automatable checks against each plugin's Studio site and record them in results.json.

Usage:
  python3 run_tests.py [slug ...]        default: every slug in shortlist_slugs.txt with a site
  python3 run_tests.py --no-enable ...   only the checks that do not change the site

Checks (IDs match the manual sheet where they overlap):
  S1     plugin installed and active, version
  A2     REST routes matching /mcp/ before anything is enabled
  A3pre  unauthenticated initialize + tools/list before enabling
  EN     switch MCP on with enable_php from test_config.json
  A3     unauthenticated initialize + tools/list after enabling (tools returned = hard fail,
         unless test_config.json marks the endpoint public_by_design from the source code)
  AUTH   authenticated initialize + tools/list: auth method, tool count, tool names
         (plus the abilities behind MCP Adapter meta-tools, via discover-abilities)
  BR     breadth: which content areas the tool and ability names cover
  ABIL   source uses the Abilities API / MCP Adapter

Per-plugin setup (enable switch, endpoint, credentials, companion plugins) lives in test_config.json.
Every entry has source "auto". Entries with source "manual" (from import_manual.py) are never overwritten.
Sites are left running with MCP enabled so the manual sheet can carry on from step A4.
No dependencies beyond the standard library and the studio CLI.
"""
import argparse
import base64
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("MCP_TEST_ROOT", Path.home() / "Studio" / "mcp-tests"))
RESULTS = HERE / "results.json"
CONFIG = HERE / "test_config.json"
SLUGS = HERE / "shortlist_slugs.txt"
ADMIN = "admin"
APP_PASSWORD_NAME = "run_tests"
ENABLED_MARKER = "run_tests_mcp_enabled_at"  # option set on the site by EN; pre-enable checks are skipped once it exists
PROTOCOL = "2025-06-18"
DISCOVER_TOOL = "mcp-adapter-discover-abilities"  # MCP Adapter meta-tool
TIMEOUT = 30

# Content areas from criteria.md (Capabilities > breadth), matched against tool names
AREAS = {
    "posts": r"post|article",
    "pages": r"page",
    "media": r"media|image|upload|attachment",
    "taxonomies": r"categor|tag|term|taxonom",
    "users": r"user|author",
    "plugins": r"plugin",
    "settings": r"setting|option",
    "blocks": r"block|pattern",
    "woocommerce": r"woo|product|order|coupon|customer",
}


# ------------------------------------------------------------------ site helpers

def wp(path, *args):
    """Run a WP-CLI command on a Studio site; returns (ok, stdout)."""
    r = subprocess.run(["studio", "wp", "--path", str(path), *args], capture_output=True, text=True)
    return (True, r.stdout.strip()) if r.returncode == 0 else (False, (r.stdout + r.stderr).strip())


def site_url(path):
    """Start the site if needed and return its URL without a trailing slash."""
    def status():
        r = subprocess.run(["studio", "status", "--path", str(path), "--format", "json"], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {}
    s = status()
    if not s.get("isOnline"):
        subprocess.run(["studio", "start", "--path", str(path), "--skip-browser"], capture_output=True)
        s = status()
    return (s.get("siteUrl") or "").rstrip("/")


def mcp_routes(path):
    ok, out = wp(path, "eval", 'foreach (array_keys(rest_get_server()->get_routes()) as $r) { if (preg_match("/mcp/i", $r)) echo $r . PHP_EOL; }')
    return [line for line in out.splitlines() if line.startswith("/")] if ok else []


def app_password(path):
    """Replace this script's application password for admin and return it."""
    _, uuids = wp(path, "user", "application-password", "list", ADMIN, f"--name={APP_PASSWORD_NAME}", "--field=uuid")
    for uuid in uuids.split():
        wp(path, "user", "application-password", "delete", ADMIN, uuid)
    ok, pw = wp(path, "user", "application-password", "create", ADMIN, APP_PASSWORD_NAME, "--porcelain")
    return pw.splitlines()[-1] if ok and pw else None


def source_markers(path, slug):
    """Look for Abilities API / MCP Adapter usage in the plugin's own PHP (vendor copies count: they are bundled)."""
    found = set()
    patterns = {
        "registers-abilities": re.compile(r"wp_register_ability\s*\("),
        "reads-abilities": re.compile(r"wp_get_abilit(y|ies)\s*\("),  # exposes abilities registered by other plugins as tools
        "mcp-adapter": re.compile(r"WP\\\\MCP\\\\|mcp-adapter|McpAdapter"),
    }
    for f in (path / "wp-content" / "plugins" / slug).rglob("*.php"):
        try:
            text = f.read_text(errors="ignore")
        except OSError:
            continue
        found |= {name for name, rx in patterns.items() if rx.search(text)}
    return sorted(found)


# ------------------------------------------------------------------ MCP over HTTP

def http_post(url, body, headers):
    """POST JSON; returns (status, response headers, text). Never raises for HTTP errors."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream", **headers})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, dict(r.headers), r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode(errors="replace")
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {}, str(e)


def parse_rpc(text):
    """Return the JSON-RPC message from a JSON or SSE body, or None."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
    return None


def error_of(msg):
    """Error text from a JSON-RPC error or a WordPress REST error body."""
    if not isinstance(msg, dict):
        return None
    if isinstance(msg.get("error"), dict):
        return msg["error"].get("message")
    return msg.get("message") or msg.get("error_description") or (msg.get("error") if isinstance(msg.get("error"), str) else None)


def list_tools(endpoint, headers):
    """initialize -> notifications/initialized -> tools/list (all pages).

    Returns dict(init_status, list_status, tools, error)."""
    out = {"init_status": None, "list_status": None, "tools": None, "error": None}
    status, h, text = http_post(endpoint, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "run_tests", "version": "0.1"}}}, headers)
    out["init_status"] = status
    msg = parse_rpc(text)
    session = {k: v for k, v in h.items() if k.lower() == "mcp-session-id"}
    if session:
        headers = {**headers, "Mcp-Session-Id": next(iter(session.values()))}
    if status == 200 and msg and "result" in msg:
        # The spec requires the negotiated version on every request after initialize
        headers = {**headers, "MCP-Protocol-Version": msg["result"].get("protocolVersion", PROTOCOL)}
        http_post(endpoint, {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers)
    else:
        out["error"] = error_of(msg)

    tools, cursor, rpc_id = [], None, 2
    while True:
        status, _, text = http_post(endpoint, {"jsonrpc": "2.0", "id": rpc_id, "method": "tools/list",
                                               "params": {"cursor": cursor} if cursor else {}}, headers)
        out["list_status"] = status
        msg = parse_rpc(text)
        if status != 200 or not msg or "result" not in msg:
            out["error"] = error_of(msg) or out["error"] or (None if msg else text[:200])
            break
        tools += msg["result"].get("tools", [])
        cursor = msg["result"].get("nextCursor")
        rpc_id += 1
        if not cursor or rpc_id > 50:
            out["tools"] = tools
            break

    # MCP Adapter servers can expose only meta-tools; ask the discover tool for the abilities behind them
    if any(t.get("name") == DISCOVER_TOOL for t in out["tools"] or []):
        _, _, text = http_post(endpoint, {"jsonrpc": "2.0", "id": rpc_id + 1, "method": "tools/call",
                                          "params": {"name": DISCOVER_TOOL, "arguments": {}}}, headers)
        out["abilities"] = ability_names(parse_rpc(text))
    return out


def ability_names(msg):
    """Ability names from a discover-abilities result (structuredContent or JSON in a text block)."""
    result = (msg or {}).get("result") or {}
    data = result.get("structuredContent")
    if data is None:
        for block in result.get("content", []):
            try:
                data = json.loads(block.get("text", ""))
                break
            except (json.JSONDecodeError, AttributeError):
                continue
    items = data.get("abilities", data) if isinstance(data, dict) else data
    return [a.get("name", "") for a in items if isinstance(a, dict)] if isinstance(items, list) else None


def auth_headers(auth, token, path):
    kind = auth.get("type", "none")
    if kind == "basic":
        pw = app_password(path)
        if not pw:
            return None
        return {"Authorization": "Basic " + base64.b64encode(f"{ADMIN}:{pw}".encode()).decode()}
    if kind == "bearer":
        return {"Authorization": "Bearer " + auth["value"].replace("{token}", token)}
    if kind == "header":
        return {auth["name"]: auth["value"].replace("{token}", token)}
    return {}


def pick_endpoint(url, configured, routes):
    if configured:
        return configured if configured.startswith("http") else f"{url}/wp-json/{configured.lstrip('/')}"
    # Prefer routes that look like a Streamable HTTP endpoint; no match means no guess
    for rx in (r"/mcp$", r"/streamable$", r"/http$", r"/endpoint$", r"/messages?$", r"/router$", r"^/mcp/[^/]+$"):
        for r in routes:
            # r.count("/") > 1 skips bare namespace indexes such as /mcp
            if re.search(rx, r) and r.count("/") > 1 and "(?P<" not in r and ".well-known" not in r:
                return f"{url}/wp-json{r}"
    return None


# ------------------------------------------------------------------ store

def load_results():
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else {}


def record(results, slug, check, status, value=None, detail=""):
    entry = results.setdefault(slug, {}).get(check)
    if entry and entry.get("source") == "manual":
        return
    results[slug][check] = {"status": status, "value": value, "detail": detail, "source": "auto",
                            "at": datetime.now().astimezone().isoformat(timespec="seconds")}


def probe_summary(p):
    tools = p["tools"]
    return f"initialize {p['init_status']}, tools/list {p['list_status']}" + (f", {len(tools)} tools" if tools is not None else "") + (f" ({p['error']})" if p["error"] else "")


# ------------------------------------------------------------------ run

def pre_enable_checks(results, slug, url, cfg, routes):
    record(results, slug, "A2", "Pass" if routes else "Disabled", routes, f"{len(routes)} MCP route(s) before enabling")
    print(f"  A2    {len(routes)} MCP route(s) before enabling")
    endpoint = pick_endpoint(url, cfg.get("endpoint"), routes)
    if endpoint and routes:
        p = list_tools(endpoint, {})
        exposed = p["tools"] is not None
        public = exposed and bool(cfg.get("public_by_design"))
        # 404 (route not registered yet) or 503 (plugin says it is switched off) means disabled out of the box
        off = not exposed and p["init_status"] in (404, 503)
        record(results, slug, "A3pre", "Public by design" if public else "Fail" if exposed else "Disabled" if off else "Pass",
               {"hard_fail": exposed and not public, **p}, f"{endpoint}: {probe_summary(p)}")
        print(f"  A3pre {probe_summary(p)}")
    else:
        record(results, slug, "A3pre", "Disabled", {"hard_fail": False}, "no MCP endpoint before enabling")
        print("  A3pre no endpoint before enabling")


def run(slug, cfg, results, enable=True):
    path = ROOT / slug
    print(f"=== {slug}")
    if not path.exists():
        print("  no site (run ./setup_test_sites.sh setup first)")
        record(results, slug, "S1", "Fail", None, f"no site at {path}")
        return

    ok, version = wp(path, "plugin", "get", slug, "--field=version")
    active, _ = wp(path, "plugin", "is-active", slug)
    record(results, slug, "S1", "Pass" if active else "Fail", version if ok else None, "active" if active else "not active")
    print(f"  S1    {'active' if active else 'NOT active'}" + (f" v{version}" if ok else ""))
    if not active:
        return

    url = site_url(path)
    has_marker, enabled_at = wp(path, "option", "get", ENABLED_MARKER)
    enabled_at = enabled_at if has_marker else ""
    if enabled_at:
        # A2 and A3pre describe the out-of-the-box state, which is gone once EN has run on this site
        print(f"  A2    skipped: MCP enabled by an earlier run ({enabled_at}); recreate the site to re-check defaults")
    else:
        pre_enable_checks(results, slug, url, cfg, mcp_routes(path))

    record(results, slug, "ABIL", "Y" if (m := source_markers(path, slug)) else "N", m, ", ".join(m) or "no markers found")
    print(f"  ABIL  {', '.join(m) or 'none'}")

    if not enable:
        return
    if cfg.get("transport") == "external":
        # The MCP server runs outside WordPress (npm package or hosted relay): nothing on the site to probe
        for check in ("EN", "A3", "AUTH"):
            record(results, slug, check, "N/A", None, f"MCP server runs outside WordPress. {cfg.get('notes', '')}".strip())
        print("  EN    n/a: MCP server runs outside WordPress")
        return
    if "enable_php" not in cfg:
        record(results, slug, "EN", "Manual", None, "no enable_php in test_config.json")
        print("  EN    no config, enable manually and re-run")
        return

    # Companion plugins the setup asks the user to install (e.g. the MCP Adapter), not declared in Requires Plugins
    for dep in cfg.get("install_plugins", []):
        if not wp(path, "plugin", "is-active", dep)[0]:
            wp(path, "plugin", "install", dep, "--activate")

    # enable_php is "" for plugins whose endpoint is on as soon as they are activated
    token = secrets.token_hex(16)
    ok, out = wp(path, f"--user={ADMIN}", "eval", cfg["enable_php"].replace("{token}", token)) if cfg["enable_php"] else (True, "")
    # enable_php can create a key with the plugin's own API and hand it back as "token:<value>"
    for line in out.splitlines():
        if line.startswith("token:"):
            token = line[6:].strip()
    if ok and not enabled_at:
        wp(path, "option", "update", ENABLED_MARKER, datetime.now().astimezone().isoformat(timespec="seconds"))
    routes = mcp_routes(path)
    endpoint = pick_endpoint(url, cfg.get("endpoint"), routes)
    record(results, slug, "EN", "Pass" if ok and endpoint else "Fail", endpoint, out[-200:] if not ok else f"{len(routes)} MCP route(s) after enabling")
    print(f"  EN    {'ok' if ok else 'FAILED'} -> {endpoint}")
    if not endpoint:
        return

    p = list_tools(endpoint, {})
    exposed = p["tools"] is not None
    # A deliberately public endpoint (per the plugin's source) is not a hard fail
    public = exposed and bool(cfg.get("public_by_design"))
    status = "Public by design" if public else "Fail" if exposed else "Pass"
    detail = probe_summary(p) + (f". Evidence: {cfg.get('public_evidence', 'not given')}" if public else "")
    record(results, slug, "A3", status, {"hard_fail": exposed and not public, **{k: v for k, v in p.items() if k != "tools"}}, detail)
    flag = "  (public by design, not a hard fail)" if public else "  <-- tools without credentials: hard fail" if exposed else ""
    print(f"  A3    {probe_summary(p)}{flag}")

    auth = cfg.get("auth", {"type": "basic"})
    if auth.get("type") == "oauth":
        record(results, slug, "AUTH", "Manual", {"auth_method": "oauth"}, "OAuth only: needs the browser consent flow, use the manual sheet")
        print("  AUTH  OAuth only, manual")
        return
    headers = auth_headers(auth, token, path)
    if headers is None:
        record(results, slug, "AUTH", "Fail", {"auth_method": auth.get("type")}, "could not create application password")
        return
    p = list_tools(endpoint, headers)
    tools = p["tools"]
    names = [t.get("name", "") for t in tools or []]
    abilities = p.get("abilities")
    detail = probe_summary(p) + (f", {len(abilities)} abilities behind the Adapter meta-tools" if abilities is not None else "")
    record(results, slug, "AUTH", "Pass" if tools is not None else "Fail",
           {"auth_method": auth.get("type"), "tool_count": len(names) if tools is not None else None, "tools": names,
            "ability_count": len(abilities) if abilities is not None else None, "abilities": abilities}, detail)
    print(f"  AUTH  ({auth.get('type')}) {detail}")

    if tools is not None:
        covered = [a for a, rx in AREAS.items() if any(re.search(rx, n, re.I) for n in names + (abilities or []))]
        record(results, slug, "BR", f"{len(covered)}/{len(AREAS)}", covered, ", ".join(covered))
        print(f"  BR    {len(covered)}/{len(AREAS)}: {', '.join(covered)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--no-enable", action="store_true", help="skip EN, A3, AUTH and BR (leave the site as it is)")
    args = ap.parse_args()

    config = {k: v for k, v in json.loads(CONFIG.read_text()).items() if not k.startswith("_")} if CONFIG.exists() else {}
    slugs = args.slugs or [s for s in SLUGS.read_text().split() if (ROOT / s).exists()]
    if not slugs:
        sys.exit(f"No sites found under {ROOT}")

    results = load_results()
    for slug in slugs:
        try:
            run(slug, config.get(slug, {}), results, enable=not args.no_enable)
        finally:
            RESULTS.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"Results: {RESULTS}")


if __name__ == "__main__":
    main()
