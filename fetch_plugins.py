#!/usr/bin/env python3
"""Collect WordPress.org plugins related to MCP into plugins.json and plugins.csv."""
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request

API = "https://api.wordpress.org/plugins/info/1.2/"
TAGS = ["mcp", "model-context-protocol", "mcp-server", "mcp-client", "mcp-adapter"]
KEYWORDS = re.compile(r"\bmcp\b|model context protocol", re.I)
FIELDS = ["short_description", "tags", "active_installs", "last_updated", "tested", "requires_php", "rating", "num_ratings", "homepage", "versions"]


def query(tag, page):
    params = {"action": "query_plugins", "request[tag]": tag, "request[per_page]": 100, "request[page]": page}
    for f in FIELDS:
        params[f"request[fields][{f}]"] = 1
    params["request[fields][icons]"] = 0
    params["request[fields][sections]"] = 0
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def main():
    found = {}
    for tag in TAGS:
        page = 1
        while True:
            data = query(tag, page)
            for p in data["plugins"]:
                entry = found.setdefault(p["slug"], p)
                entry.setdefault("matched_tags", [])
                if tag not in entry["matched_tags"]:
                    entry["matched_tags"].append(tag)
            if page >= data["info"]["pages"]:
                break
            page += 1
            time.sleep(0.5)
        print(f"{tag}: done")

    rows = []
    for slug, p in found.items():
        name = html.unescape(p["name"])
        desc = html.unescape(p.get("short_description") or "")
        tags = list((p.get("tags") or {}).keys())
        mentions = bool(KEYWORDS.search(name) or KEYWORDS.search(desc))
        rows.append({
            "slug": slug,
            "name": name,
            "mentions_mcp": mentions,
            "active_installs": p.get("active_installs"),
            "version": p.get("version"),
            "last_updated": p.get("last_updated"),
            "tested": p.get("tested"),
            "requires_php": p.get("requires_php"),
            "rating": p.get("rating"),
            "num_ratings": p.get("num_ratings"),
            "matched_tags": ", ".join(p["matched_tags"]),
            "short_description": desc,
            "url": f"https://wordpress.org/plugins/{slug}/",
        })
    rows.sort(key=lambda r: (not r["mentions_mcp"], -(r["active_installs"] or 0)))

    with open("plugins.json", "w") as f:
        json.dump(rows, f, indent=2)
    with open("plugins.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    hits = sum(r["mentions_mcp"] for r in rows)
    print(f"{len(rows)} unique plugins, {hits} explicitly mention MCP")


if __name__ == "__main__":
    main()
