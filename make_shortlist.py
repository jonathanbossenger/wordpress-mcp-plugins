#!/usr/bin/env python3
"""Build shortlist.csv and shortlist_slugs.txt from candidates.json.

Lanes: established (100+ installs), challenger (<100 installs, hand-picked from the
pre-screen), baseline (reference only: documented in the workbook, not scored or installed).
"""
import csv
import json

ESTABLISHED = """ai-engine vibe-ai easy-mcp-ai royal-mcp miniorange-secure-mcp-server
wsp-mcp-ai-agents-connector cowboy-mcp stifli-flex-mcp agent-abilities-for-mcp diviops-agent
ai-workflow-automation-ai-agent-hub nibwp mountdev-ai-mcp-connector iato-mcp siteskite
invizo-mcp ylabs-ai-assistant-connector""".split()
# ylabs-connector-for-wpwriter removed 2026-10-20: closed on WordPress.org, cannot be installed

CHALLENGERS = """albert-ai-butler acrossai-mcp-manager sokket-site-connector-for-mcp webo-mcp
alphabridge-mcp track-debug admindra-mcp devcubic-ai-bridge-for-mcp abilities-bridge
strifebridge-mcp bcs-mcp-manager saddle acadium-agent-publisher aicom
rectus-content-access-for-mcp mcp-for-woocommerce counterhand-mcp-for-woocommerce
publishio""".split()

BASELINE = ["mcp-adapter"]


def main():
    cands = {r["slug"]: r for r in json.load(open("candidates.json"))}
    rows = []
    for lane, slugs in (("established", ESTABLISHED), ("challenger", CHALLENGERS), ("baseline", BASELINE)):
        for s in slugs:
            r = cands[s]
            rows.append({
                "lane": lane,
                "slug": s,
                "name": r["name"],
                "active_installs": r["active_installs"],
                "last_updated": r["last_updated"][:10],
                "rating": r["rating"],
                "num_ratings": r["num_ratings"],
                "tested_current": "Y" if r["tested_current"] else "N",
                "mentions_abilities": "Y" if r["mentions_abilities"] else "N",
                "signals": r["signals"],
                "url": r["url"],
                "short_description": r["short_description"],
            })
    with open("shortlist.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open("shortlist_slugs.txt", "w") as f:
        f.write("\n".join(r["slug"] for r in rows if r["lane"] != "baseline") + "\n")
    print({lane: sum(r["lane"] == lane for r in rows) for lane in ("established", "challenger", "baseline")})


if __name__ == "__main__":
    main()
