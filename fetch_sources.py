#!/usr/bin/env python3
"""Download the current free version of every shortlisted plugin from WordPress.org into sources/<slug>/.

Usage:
  python3 fetch_sources.py [slug ...]    default: every plugin in shortlist.csv except the baseline lane

The plugin code is only unpacked, never run. Versions go to sources/manifest.json.
"""
import csv
import io
import json
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "sources"
MANIFEST = SOURCES / "manifest.json"
API = "https://api.wordpress.org/plugins/info/1.2/"


def info(slug):
    params = {"action": "plugin_information", "request[slug]": slug}
    with urllib.request.urlopen(API + "?" + urllib.parse.urlencode(params), timeout=60) as r:
        return json.load(r)


def unpack(data, dest):
    """Unzip into dest, refusing any entry that would land outside it."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    root = dest.resolve()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.infolist():
            target = (dest / member.filename).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"unsafe path in zip: {member.filename}")
        z.extractall(dest)
    # WordPress.org zips hold one top-level folder named after the slug: flatten it
    inner = [p for p in dest.iterdir()]
    if len(inner) == 1 and inner[0].is_dir():
        for p in inner[0].iterdir():
            p.rename(dest / p.name)
        inner[0].rmdir()


def main():
    slugs = sys.argv[1:] or [r["slug"] for r in csv.DictReader(open(HERE / "shortlist.csv")) if r["lane"] != "baseline"]
    SOURCES.mkdir(exist_ok=True)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for slug in slugs:
        try:
            d = info(slug)
            if "error" in d:
                raise ValueError(d["error"])
            with urllib.request.urlopen(d["download_link"], timeout=120) as r:
                unpack(r.read(), SOURCES / slug)
            manifest[slug] = {"version": d["version"], "download_link": d["download_link"],
                              "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}
            print(f"{slug}: {d['version']}")
        except Exception as e:  # keep going: one closed or broken plugin should not stop the rest
            manifest[slug] = {"error": str(e), "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds")}
            print(f"{slug}: FAILED ({e})")
        MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
