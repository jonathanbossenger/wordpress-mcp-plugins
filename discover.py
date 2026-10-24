#!/usr/bin/env python3
"""Find MCP plugins on WordPress.org and pre-screen them, the way shortlist.csv was built (SELECTION.md).

Usage:
  python3 discover.py                     collect, enrich and classify into discovery/
  python3 discover.py --as-of 2026-10-15  judge "updated within N days" from that date (default: today)
  python3 discover.py --wp-version 7.0    the "tested up to current" bar (default: latest WordPress release)
  python3 discover.py --refresh           fetch plugin details again instead of reusing discovery/details.json
  python3 discover.py --write-shortlist   also rewrite shortlist.csv with today's numbers, same slugs and lanes

Writes discovery/plugins.json (every tagged plugin), discovery/details.json (full plugin_information)
and discovery/candidates.csv (one row each, with the role, the filters and the challenger signal count).
The role is a heuristic plus the manual OVERRIDES below. Picking the challengers was a judgement call:
candidates.csv gives the numbers to choose from, shortlist.csv records what was chosen.
"""
import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "discovery"
SHORTLIST = HERE / "shortlist.csv"
API = "https://api.wordpress.org/plugins/info/1.2/"
CORE = "https://api.wordpress.org/core/version-check/1.7/"
TAGS = ["mcp", "model-context-protocol", "mcp-server", "mcp-client", "mcp-adapter"]
KEYWORDS = re.compile(r"\bmcp\b|model context protocol", re.I)
FIELDS = ["short_description", "tags", "active_installs", "last_updated", "tested", "requires_php", "rating", "num_ratings", "homepage"]
UPDATED_WITHIN = 183  # filter 3: updated within the last 6 months
ESTABLISHED = 100  # active installs for the established lane

# Manual judgement from reading descriptions: MCP is a side feature of a non-MCP product, or the heuristic gets it wrong
OVERRIDES = {
    "elementor": "not-mcp-primary", "premium-addons-for-elementor": "not-mcp-primary",
    "atomic-elements": "not-mcp-primary", "notification-for-telegram": "not-mcp-primary",
    "bubuku-media-library": "not-mcp-primary", "xspeed": "not-mcp-primary",
    "woo-bulk-editor": "not-mcp-primary", "woocommerce-export-orders": "not-mcp-primary",
    "everybooking": "not-mcp-primary", "schedopia": "not-mcp-primary",
    "corsen-context": "seo-visibility", "inhale-mcp-abilities": "guardrail",
    "enable-abilities-for-mcp": "abilities-pack", "miniorange-ai-agent": "client",
    # shortlisted challengers the heuristic misses: servers on reading their descriptions
    "saddle": "server", "acadium-agent-publisher": "server", "aicom": "server", "mcp-for-woocommerce": "server",
}


def get(url, params):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)


def collect():
    """Every plugin with one of TAGS, with the matched tags recorded."""
    found = {}
    for tag in TAGS:
        page = 1
        while True:
            params = {"action": "query_plugins", "request[tag]": tag, "request[per_page]": 100, "request[page]": page,
                      "request[fields][icons]": 0, "request[fields][sections]": 0}
            params.update({f"request[fields][{f}]": 1 for f in FIELDS})
            data = get(API, params)
            for p in data["plugins"]:
                found.setdefault(p["slug"], {**p, "matched_tags": []})["matched_tags"].append(tag)
            if page >= data["info"]["pages"]:
                break
            page += 1
            time.sleep(0.5)
        print(f"tag {tag}: {sum(tag in p['matched_tags'] for p in found.values())} plugins")
    return found


def enrich(slugs, cached):
    """Full plugin_information for each slug not already in cached."""
    details = dict(cached)
    todo = [s for s in slugs if s not in details]
    for i, slug in enumerate(todo, 1):
        params = {"action": "plugin_information", "request[slug]": slug}
        params.update({f"request[fields][{f}]": 1 for f in ("sections", "support_threads", "added", "tested")})
        try:
            d = get(API, params)
            sections = d.get("sections") or {}
            details[slug] = {
                "added": d.get("added"), "tested": d.get("tested"), "support_threads": d.get("support_threads"),
                "description": sections.get("description", ""), "installation": sections.get("installation", ""),
            }
        except Exception as e:  # keep going: a closed plugin should not stop the rest
            print(f"{slug}: FAILED ({e})")
        if i % 25 == 0:
            print(f"details: {i} / {len(todo)}")
        time.sleep(0.3)
    return details


def role(name, short, text):
    blob = f"{name} {short}".lower()
    if re.search(r"mcp server|mcp plugin|mcp connector|mcp bridge|connect (claude|chatgpt)|(claude|chatgpt).{0,40}(to|with) wordpress|to wordpress", blob):
        return "server"
    if re.search(r"mcp client|connect(s)? (to )?external mcp|consume.*mcp", blob):
        return "client"
    if re.search(r"llms\.txt|ai visibility|ai readiness|crawler|geo\b|aeo\b|agent.?ready|agentic optimization", blob):
        return "seo-visibility"
    if re.search(r"firewall|guardrail|governance|audit|approval|permissions|abilities (guard|manager)|logs\b|ability controls", blob):
        return "guardrail"
    if re.search(r"connect(or)?\b.*(claude|chatgpt)|(claude|chatgpt).*(connect|manage)|mcp (connector|bridge|adapter)|ai connector|server for", blob):
        return "server"
    if "mcp server" in text.lower():
        return "server?"
    return "other?"


def ver(v):
    try:
        return tuple(int(x) for x in (v or "0").split(".")[:2])
    except ValueError:
        return (0, 0)


def classify(p, d, as_of, wp, shortlisted):
    name = html.unescape(p["name"])
    short = html.unescape(p.get("short_description") or "")
    text = re.sub(r"<[^>]+>", " ", d.get("description", "") + " " + d.get("installation", ""))
    days = (as_of - datetime.strptime(p["last_updated"][:10], "%Y-%m-%d").date()).days
    tested = d.get("tested") or p.get("tested")
    r = {
        "slug": p["slug"],
        "name": name,
        "role": OVERRIDES.get(p["slug"]) or role(name, short, text),
        "mentions_mcp": bool(KEYWORDS.search(name) or KEYWORDS.search(short)),
        "active_installs": p.get("active_installs") or 0,
        "last_updated": p["last_updated"][:10],
        "days_since_update": days,
        "tested": tested,
        "tested_current": ver(tested) >= wp,
        "rating": p.get("rating"),
        "num_ratings": p.get("num_ratings") or 0,
        "support_threads": d.get("support_threads") or 0,
        "mentions_abilities": bool(re.search(r"abilities api|mcp adapter|wp_register_ability", text, re.I)),
    }
    # challenger pre-screen: one point each
    r["signals"] = sum([
        days <= 60,
        r["tested_current"],
        len(text) > 1500,
        bool(re.search(r"security|permission|authenticat|oauth|capabilit|read-only|read only", text, re.I)),
        bool(re.search(r"claude desktop|install|setup|connect", d.get("installation", ""), re.I)) and len(d.get("installation", "")) > 200,
        r["mentions_abilities"],
        r["num_ratings"] > 0,
        r["support_threads"] > 0,
    ])
    r["passes_filters"] = r["mentions_mcp"] and r["role"] == "server" and days <= UPDATED_WITHIN and r["tested_current"]
    r["suggested_lane"] = ("established" if r["active_installs"] >= ESTABLISHED else "challenger") if r["passes_filters"] else ""
    r["in_shortlist"] = shortlisted.get(p["slug"], "")
    r["matched_tags"] = ", ".join(p["matched_tags"])
    r["url"] = f"https://wordpress.org/plugins/{p['slug']}/"
    r["short_description"] = short
    return r


def write_shortlist(rows):
    """Same slugs and lanes as shortlist.csv, with today's WordPress.org numbers."""
    by_slug = {r["slug"]: r for r in rows}
    old = list(csv.DictReader(SHORTLIST.open()))
    yn = lambda b: "Y" if b else "N"
    for o in old:
        r = by_slug.get(o["slug"])
        if not r:
            print(f"{o['slug']}: not found on WordPress.org any more, row kept as it was")
            continue
        o.update(name=r["name"], active_installs=r["active_installs"], last_updated=r["last_updated"], rating=r["rating"],
                 num_ratings=r["num_ratings"], tested_current=yn(r["tested_current"]),
                 mentions_abilities=yn(r["mentions_abilities"]), signals=r["signals"], short_description=r["short_description"])
    with SHORTLIST.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(old[0]))
        w.writeheader()
        w.writerows(old)
    print(f"shortlist.csv: {len(old)} rows refreshed")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    ap.add_argument("--wp-version", help="e.g. 7.0 (default: the latest release from api.wordpress.org)")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--write-shortlist", action="store_true")
    args = ap.parse_args()

    wp = args.wp_version or get(CORE, {})["offers"][0]["current"]
    OUT.mkdir(exist_ok=True)
    found = collect()
    (OUT / "plugins.json").write_text(json.dumps(found, indent=2) + "\n")
    cache = OUT / "details.json"
    cached = {} if args.refresh or not cache.exists() else json.loads(cache.read_text())
    details = enrich(sorted(found), cached)
    cache.write_text(json.dumps(details) + "\n")

    shortlisted = {r["slug"]: r["lane"] for r in csv.DictReader(SHORTLIST.open())}
    rows = [classify(p, details.get(s, {}), args.as_of, ver(wp), shortlisted) for s, p in found.items()]
    rows.sort(key=lambda r: (not r["passes_filters"], r["role"], -r["active_installs"]))
    with (OUT / "candidates.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    roles = {}
    for r in rows:
        roles[r["role"]] = roles.get(r["role"], 0) + 1
    passing = [r for r in rows if r["passes_filters"]]
    print(f"{len(rows)} plugins (as of {args.as_of}, current WordPress {wp}): "
          + ", ".join(f"{n} {k}" for k, n in sorted(roles.items(), key=lambda x: -x[1])))
    print(f"{len(passing)} pass the filters: {sum(r['suggested_lane'] == 'established' for r in passing)} established, "
          f"{sum(r['suggested_lane'] == 'challenger' for r in passing)} challenger candidates")
    new = [r["slug"] for r in passing if r["suggested_lane"] == "established" and not r["in_shortlist"]]
    if new:
        print("established, not in shortlist.csv: " + ", ".join(new))
    print(f"-> {OUT.relative_to(HERE)}/candidates.csv")
    if args.write_shortlist:
        write_shortlist(rows)


if __name__ == "__main__":
    main()
