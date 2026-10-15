#!/usr/bin/env python3
"""Fetch full plugin_information for every plugin in plugins.json into details.json."""
import json
import time
import urllib.parse
import urllib.request

API = "https://api.wordpress.org/plugins/info/1.2/"


def info(slug):
    params = {"action": "plugin_information", "request[slug]": slug}
    for f in ("sections", "tags", "donate_link", "contributors", "support_threads", "support_threads_resolved", "versions", "added", "requires", "requires_php", "tested", "homepage"):
        params[f"request[fields][{f}]"] = 1
    with urllib.request.urlopen(API + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)


def main():
    rows = json.load(open("plugins.json"))
    details = {}
    for i, r in enumerate(rows, 1):
        try:
            d = info(r["slug"])
            details[r["slug"]] = {
                "added": d.get("added"),
                "requires": d.get("requires"),
                "tested": d.get("tested"),
                "requires_php": d.get("requires_php"),
                "homepage": d.get("homepage"),
                "support_threads": d.get("support_threads"),
                "support_threads_resolved": d.get("support_threads_resolved"),
                "tags": list((d.get("tags") or {}).keys()),
                "description": (d.get("sections") or {}).get("description", ""),
                "installation": (d.get("sections") or {}).get("installation", ""),
                "faq": (d.get("sections") or {}).get("faq", ""),
            }
        except Exception as e:
            print("FAILED", r["slug"], e)
        if i % 25 == 0:
            print(i, "/", len(rows))
        time.sleep(0.3)
    json.dump(details, open("details.json", "w"))
    print("saved", len(details))


if __name__ == "__main__":
    main()
