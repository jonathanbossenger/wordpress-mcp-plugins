#!/usr/bin/env python3
"""Heuristic role classification + lane assignment. Writes candidates.json."""
import json
import re
from datetime import datetime

NOW = datetime(2026, 10, 15)
CURRENT_WP = (7, 0)  # treat tested-up-to >= 7.0 as current


def days_since(s):
    return (NOW - datetime.strptime(s[:10], "%Y-%m-%d")).days


def ver(v):
    try:
        return tuple(int(x) for x in (v or "0").split(".")[:2])
    except ValueError:
        return (0, 0)


def role(name, short, text):
    blob = f"{name} {short}".lower()
    full = (blob + " " + text.lower())
    strong_server = re.search(r"mcp server|mcp plugin|mcp connector|mcp bridge|connect (claude|chatgpt)|(claude|chatgpt).{0,40}(to|with) wordpress|to wordpress", blob)
    if strong_server:
        return "server"
    if re.search(r"mcp client|connect(s)? (to )?external mcp|consume.*mcp", blob):
        return "client"
    if re.search(r"llms\.txt|ai visibility|ai readiness|crawler|geo\b|aeo\b|agent.?ready|agentic optimization", blob) and not re.search(r"mcp server", blob):
        return "seo-visibility"
    if re.search(r"firewall|guardrail|governance|audit|approval|permissions|abilities (guard|manager)|logs\b|ability controls", blob) and not re.search(r"mcp server", blob):
        return "guardrail"
    if re.search(r"mcp server|connect(or)?\b.*(claude|chatgpt)|(claude|chatgpt).*(connect|manage)|mcp (connector|bridge|adapter)|ai connector|server for", blob):
        return "server"
    if "mcp server" in full:
        return "server?"
    return "other?"


# Manual judgement from reading descriptions: MCP is a side feature of a non-MCP product
OVERRIDES = {
    "elementor": "not-mcp-primary", "premium-addons-for-elementor": "not-mcp-primary",
    "atomic-elements": "not-mcp-primary", "notification-for-telegram": "not-mcp-primary",
    "bubuku-media-library": "not-mcp-primary", "xspeed": "not-mcp-primary",
    "woo-bulk-editor": "not-mcp-primary", "woocommerce-export-orders": "not-mcp-primary",
    "everybooking": "not-mcp-primary", "schedopia": "not-mcp-primary",
    "corsen-context": "seo-visibility", "inhale-mcp-abilities": "guardrail",
    "enable-abilities-for-mcp": "abilities-pack", "miniorange-ai-agent": "client",
}


def main():
    rows = json.load(open("plugins.json"))
    det = json.load(open("details.json"))
    out = []
    for r in rows:
        d = det.get(r["slug"], {})
        text = re.sub(r"<[^>]+>", " ", d.get("description", "") + " " + d.get("installation", ""))
        r["role"] = OVERRIDES.get(r["slug"]) or role(r["name"], r["short_description"], text)
        r["days_since_update"] = days_since(r["last_updated"])
        r["days_since_added"] = days_since(d["added"]) if d.get("added") else None
        r["readme_len"] = len(text)
        r["mentions_security"] = bool(re.search(r"security|permission|authenticat|oauth|capabilit|read-only|read only", text, re.I))
        r["mentions_abilities"] = bool(re.search(r"abilities api|mcp adapter|wp_register_ability", text, re.I))
        r["has_setup_steps"] = bool(re.search(r"claude desktop|install|setup|connect", d.get("installation", ""), re.I)) and len(d.get("installation", "")) > 200
        r["support_threads"] = d.get("support_threads") or 0
        r["tested_current"] = ver(d.get("tested")) >= CURRENT_WP
        r["homepage"] = d.get("homepage")
        # challenger pre-screen signal count
        sig = [
            r["days_since_update"] <= 60,
            r["tested_current"],
            r["readme_len"] > 1500,
            r["mentions_security"],
            r["has_setup_steps"],
            r["mentions_abilities"],
            (r["num_ratings"] or 0) > 0,
            r["support_threads"] > 0,
        ]
        r["signals"] = sum(sig)
        out.append(r)
    json.dump(out, open("candidates.json", "w"), indent=2)


if __name__ == "__main__":
    main()
