#!/usr/bin/env python3
"""Build the public ranking page from reviews/ into site/index.html.

Usage:
  python3 build_site.py      writes site/index.html (one self-contained file, no external requests)

Scores and order come from compare.py, so the page always matches ranking.md. Deploy the site/
folder to any static host, e.g. `sf publish ./site` on Spacefast.
"""
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import compare

HERE = Path(__file__).resolve().parent
SITE = HERE / "site"
REPO = "https://github.com/jonathanbossenger/wordpress-mcp-plugins"

GROUPS = [("SEC", "Security"), ("SAFE", "Safety controls"), ("STD", "Standards"), ("HOST", "Hosting"), ("SETUP", "Setup and docs")]
LABELS = {
    "SEC-AUTH": "Every tool needs a user credential", "SEC-UNAUTH": "No anonymous access",
    "SEC-CAPS": "Permission checks per tool", "SEC-SECRETS": "Keys stored safely", "SEC-DEFAULT": "Off until switched on",
    "SAFE-READONLY": "Read-only mode", "SAFE-SCOPE": "Limit which tools a connection gets",
    "SAFE-CONFIRM": "Confirms destructive actions", "SAFE-DELETE": "Deletes go to the trash", "SAFE-LOG": "Activity log in wp-admin",
    "STD-ABILITIES": "Uses the Abilities API", "STD-TRANSPORT": "Current MCP protocol, inside WordPress",
    "STD-FREE": "Complete in the free version", "HOST-LOCAL": "Works on a local site", "HOST-PUBLIC": "Works on typical hosts",
    "SETUP-STEPS": "Three steps or fewer", "SETUP-NOTERM": "No terminal or config file", "SETUP-GUIDE": "Connection guide in wp-admin",
    "DOCS": "Documentation",
}


def tasks():
    """T1-T8 descriptions from the checklist's task table."""
    return dict(re.findall(r"^\| (T\d) \| ([^|]+?)\.? \|", compare.CHECKLIST.read_text(), re.M))


def data():
    ids = compare.judged(compare.check_ids())
    shortlist = {r["slug"]: r for r in csv.DictReader(compare.SHORTLIST.open())}
    plugins, dates = [], []
    for n, r in enumerate(compare.ranked(compare.load()), 1):
        review = json.loads((compare.REVIEWS / f"{r['slug']}.json").read_text())
        checks = review["checks"]
        dates.append(review["reviewed_at"][:10])
        task_values = checks.get("CAP-TASKS", {}).get("value") or {}
        plugins.append({
            "rank": n, "slug": r["slug"], "name": shortlist.get(r["slug"], {}).get("name", r["slug"]),
            "version": r["version"], "lane": r["lane"], "installs": r["installs"], "score": r["score"],
            "pass": r["pass"], "partial": r["partial"], "fail": r["fail"], "gated": r["gated"],
            "tools": r["tools"] if isinstance(r["tools"], int) else "",  # some reviews give a sentence, not a count
            "checks": {i: {"s": checks[i]["status"], "t": checks[i]["summary"]} for i in ids if i in checks},
            "tasks": {t: {"s": (task_values.get(t) or {}).get("status", ""), "t": (task_values.get(t) or {}).get("tool", "")}
                      for t in compare.TASKS},
            "notes": review.get("notes", ""),
        })
    return {
        "plugins": plugins, "groups": GROUPS, "labels": LABELS, "tasks": tasks(),
        "weights": compare.WEIGHTS, "gate": compare.GATE, "repo": REPO,
        "reviewed": [min(dates), max(dates)], "built": datetime.now().date().isoformat(),
    }


def main():
    payload = json.dumps(data(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(TEMPLATE.replace("__DATA__", payload))
    print(f"site/index.html ({(SITE / 'index.html').stat().st_size // 1024} KB)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordPress MCP Plugin Rankings</title>
<meta name="description" content="35 MCP server plugins from WordPress.org, reviewed from their source code for security, safety controls, standards and ease of setup.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%232f5bd3'/><path d='M8 22V10h3l5 7 5-7h3v12h-3v-7l-5 6.5L11 15v7z' fill='white'/></svg>">
<style>
:root {
  --bg: #f7f7f5; --surface: #ffffff; --surface-2: #f1f1ee; --border: #e3e2dd;
  --text: #1c1c1a; --muted: #6b6a64; --accent: #2f5bd3; --accent-soft: #e6ecfb;
  --pass: #1f7a4d; --pass-bg: #e3f3ea; --partial: #9a6200; --partial-bg: #fbf0d9;
  --fail: #b42318; --fail-bg: #fbe5e2; --none: #6b6a64; --none-bg: #ecebe7;
  --bar: #2f5bd3; --bar-track: #e8e7e2; --shadow: 0 1px 2px rgba(0,0,0,.04), 0 1px 1px rgba(0,0,0,.03);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #131312; --surface: #1c1c1b; --surface-2: #242422; --border: #33332f;
    --text: #ecebe6; --muted: #9c9b94; --accent: #8aa8ff; --accent-soft: #1f2a47;
    --pass: #5fcf94; --pass-bg: #17321f; --partial: #e9b45a; --partial-bg: #3a2c12;
    --fail: #ff8a7d; --fail-bg: #3d1915; --none: #9c9b94; --none-bg: #2a2a27;
    --bar: #8aa8ff; --bar-track: #2c2c29; --shadow: none;
  }
}
:root[data-theme="dark"] {
  --bg: #131312; --surface: #1c1c1b; --surface-2: #242422; --border: #33332f;
  --text: #ecebe6; --muted: #9c9b94; --accent: #8aa8ff; --accent-soft: #1f2a47;
  --pass: #5fcf94; --pass-bg: #17321f; --partial: #e9b45a; --partial-bg: #3a2c12;
  --fail: #ff8a7d; --fail-bg: #3d1915; --none: #9c9b94; --none-bg: #2a2a27;
  --bar: #8aa8ff; --bar-track: #2c2c29; --shadow: none;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-feature-settings: "tnum" 1;
}
a { color: var(--accent); }
.wrap { max-width: 960px; margin: 0 auto; padding: 0 16px; }
header { padding: 56px 0 28px; }
.eyebrow { font-size: 13px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--accent); margin: 0 0 10px; }
h1 { font-size: clamp(28px, 5vw, 40px); line-height: 1.15; letter-spacing: -.02em; margin: 0 0 14px; text-wrap: balance; }
.lede { font-size: 18px; color: var(--muted); margin: 0; max-width: 680px; }
.caveat {
  margin: 24px 0 0; padding: 14px 16px; border-radius: 10px; background: var(--surface);
  border: 1px solid var(--border); font-size: 14px; color: var(--muted); display: flex; gap: 10px;
}
.caveat strong { color: var(--text); }
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 8px 0 16px; }
.search {
  flex: 1 1 220px; min-width: 0; font: inherit; font-size: 15px; padding: 9px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface); color: var(--text);
}
.search:focus-visible, button:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.seg { display: inline-flex; background: var(--surface-2); border-radius: 8px; padding: 3px; }
.seg button {
  font: inherit; font-size: 14px; border: 0; background: none; color: var(--muted); padding: 6px 12px;
  border-radius: 6px; cursor: pointer;
}
.seg button[aria-pressed="true"] { background: var(--surface); color: var(--text); box-shadow: var(--shadow); font-weight: 600; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; color: var(--muted); margin: 0 0 12px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }

.list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); }
.card summary { list-style: none; cursor: pointer; padding: 14px 16px; display: grid; gap: 4px 16px;
  grid-template-columns: 40px minmax(0, 1fr) 180px 20px; align-items: center; }
.card summary::-webkit-details-marker { display: none; }
.rank { font-size: 20px; font-weight: 700; color: var(--muted); text-align: right; }
.card.top .rank { color: var(--accent); }
.name { font-weight: 600; font-size: 16px; overflow-wrap: anywhere; }
.meta { font-size: 13px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: center; }
.chip { font-size: 12px; padding: 1px 8px; border-radius: 999px; background: var(--surface-2); color: var(--muted); }
.chip.gate { background: var(--fail-bg); color: var(--fail); font-weight: 600; }
.scorecol { display: grid; gap: 6px; }
.scoreline { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.score { font-size: 20px; font-weight: 700; }
.score small { font-size: 12px; font-weight: 500; color: var(--muted); }
.tally { font-size: 12px; color: var(--muted); white-space: nowrap; }
.tally b { font-weight: 600; }
.bar { height: 6px; border-radius: 3px; background: var(--bar-track); overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--bar); border-radius: 3px; }
.card.excluded .bar i { background: var(--muted); }
.chev { width: 20px; height: 20px; color: var(--muted); transition: transform .15s; }
details[open] .chev { transform: rotate(180deg); }

.detail { border-top: 1px solid var(--border); padding: 16px; display: grid; gap: 20px; }
.detail h3 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: 0 0 8px; }
.rows { display: grid; gap: 2px; }
.row { display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--surface-2); }
.row:last-child { border-bottom: 0; }
.row .label { font-weight: 600; font-size: 14px; }
.row .label code { font-size: 11px; color: var(--muted); font-weight: 500; margin-left: 6px; }
.row p { margin: 2px 0 0; font-size: 14px; color: var(--muted); }
.pill { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; padding: 2px 8px;
  border-radius: 999px; height: 22px; white-space: nowrap; justify-self: start; }
.pill svg { width: 12px; height: 12px; }
.s-Pass { background: var(--pass-bg); color: var(--pass); }
.s-Partial { background: var(--partial-bg); color: var(--partial); }
.s-Fail { background: var(--fail-bg); color: var(--fail); }
.s-Unknown, .s-NA, .s-None { background: var(--none-bg); color: var(--none); }
.notes { font-size: 14px; color: var(--muted); margin: 0; white-space: pre-line; }
.links { font-size: 14px; display: flex; gap: 16px; flex-wrap: wrap; }

.divider { margin: 36px 0 12px; }
.divider h2 { font-size: 20px; margin: 0 0 4px; }
.divider p { margin: 0; color: var(--muted); font-size: 14px; }
.empty { padding: 24px; text-align: center; color: var(--muted); }

section.method { margin: 56px 0 0; padding: 28px 0 0; border-top: 1px solid var(--border); }
section.method h2 { font-size: 22px; margin: 0 0 12px; }
section.method p, section.method li { color: var(--muted); font-size: 15px; }
section.method li { margin: 4px 0; }
.weights { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; padding: 0; list-style: none; }
.weights li { margin: 0; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 6px 12px; font-size: 14px; color: var(--text); }
.weights b { color: var(--accent); }
footer { padding: 40px 0 56px; font-size: 13px; color: var(--muted); }
.theme { font: inherit; font-size: 13px; background: none; border: 1px solid var(--border); color: var(--muted); border-radius: 6px; padding: 4px 10px; cursor: pointer; }

@media (max-width: 640px) {
  header { padding-top: 36px; }
  .card summary { grid-template-columns: 32px minmax(0, 1fr) 20px; }
  .scorecol { grid-column: 2 / 3; grid-row: 2; }
  .chev { grid-column: 3; grid-row: 1; }
  .rank { font-size: 17px; }
  .row { grid-template-columns: 1fr; gap: 4px; }
}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow">WordPress × Model Context Protocol</p>
    <h1>Which WordPress MCP plugin should you trust with your site?</h1>
    <p class="lede" id="lede"></p>
    <div class="caveat" role="note">
      <span aria-hidden="true">ⓘ</span>
      <span><strong>Judged from the code, not tested on a live site.</strong> Scores a point or two apart are effectively level. Open a plugin to see the reasoning behind every check.</span>
    </div>
  </header>

  <div class="controls">
    <input class="search" id="q" type="search" placeholder="Search plugins" aria-label="Search plugins">
    <div class="seg" role="group" aria-label="Filter by lane" id="lane">
      <button aria-pressed="true" data-lane="">All</button>
      <button aria-pressed="false" data-lane="established">100+ installs</button>
      <button aria-pressed="false" data-lane="challenger">Newer</button>
    </div>
  </div>
  <div class="legend" id="legend"></div>

  <ol class="list" id="ranked"></ol>
  <div class="divider" id="exdiv">
    <h2>Excluded</h2>
    <p id="exnote"></p>
  </div>
  <ol class="list" id="excluded"></ol>

  <section class="method" id="method">
    <h2>How the ranking works</h2>
    <p id="m-intro"></p>
    <ul>
      <li>Every check and standard task scores <b>Pass 1</b>, <b>Partial ½</b>, <b>Fail 0</b>, multiplied by the weight of its group. Unknown and not-applicable checks are left out.</li>
      <li>The score is the share of possible points, out of 100. Ties go to the plugin with more active installs.</li>
      <li id="m-gate"></li>
      <li>"100+ installs" plugins were chosen by size. "Newer" plugins have fewer than 100 installs and were hand-picked from a pre-screen of their readme, ratings and update history.</li>
    </ul>
    <ul class="weights" id="weights"></ul>
    <p>The standard tasks Claude should be able to do through each plugin:</p>
    <ul id="tasklist"></ul>
  </section>

  <footer>
    <p id="foot"></p>
    <button class="theme" id="theme" type="button">Toggle dark mode</button>
  </footer>
</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById("data").textContent);
  var GROUP_NAMES = { SEC: "Security", SAFE: "Safety", STD: "Standards", HOST: "Hosting", SETUP: "Setup", DOCS: "Docs", T: "Tasks" };
  var ICON = {
    Pass: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.2l2.3 2.3 4.7-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    Partial: '<svg viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M6 2a4 4 0 0 1 0 8z" fill="currentColor"/></svg>',
    Fail: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
    Other: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 6h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
  };
  var chev = '<svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 8l5 5 5-5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function md(s) { return esc(s).replace(/`([^`]+)`/g, "<code>$1</code>"); }
  function fmt(n) { return Number(n).toLocaleString("en-US"); }
  function pill(s) {
    var label = s === "N/A" ? "N/A" : (s || "—");
    var cls = s === "N/A" ? "NA" : (s || "None");
    return '<span class="pill s-' + cls + '">' + (ICON[s] || ICON.Other) + label + "</span>";
  }
  function date(iso) { return new Date(iso + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }); }

  var plugins = D.plugins, nChecks = Object.keys(D.labels).length;
  document.getElementById("lede").textContent = plugins.length + " MCP server plugins from WordPress.org, each read line by line and scored on " +
    nChecks + " checks: security, safety controls, standards, hosting and setup, plus 8 everyday tasks.";
  document.getElementById("legend").innerHTML = ["Pass", "Partial", "Fail"].map(function (s) { return "<span>" + pill(s) + "</span>"; }).join("") +
    "<span>Score out of 100, weighted towards security</span>";

  function card(p) {
    var top = !p.gated.length && p.rank <= 3;
    var summary = '<summary>' +
      '<span class="rank">' + p.rank + '</span>' +
      '<span><span class="name">' + esc(p.name) + '</span>' +
      '<span class="meta"><span>' + fmt(p.installs) + ' installs</span><span>v' + esc(p.version) + '</span>' +
      (p.tools !== "" ? '<span>' + esc(p.tools) + ' tools</span>' : "") +
      '<span class="chip">' + (p.lane === "established" ? "100+ installs" : "Newer") + '</span>' +
      p.gated.map(function (g) { return '<span class="chip gate">Fails ' + esc(D.labels[g] || g) + '</span>'; }).join("") +
      '</span></span>' +
      '<span class="scorecol"><span class="scoreline"><span class="score">' + p.score.toFixed(1) + ' <small>/ 100</small></span>' +
      '<span class="tally" aria-label="' + p.pass + ' pass, ' + p.partial + ' partial, ' + p.fail + ' fail">' +
      '<b style="color:var(--pass)">' + p.pass + '</b> · <b style="color:var(--partial)">' + p.partial + '</b> · <b style="color:var(--fail)">' + p.fail + '</b></span></span>' +
      '<span class="bar"><i style="width:' + p.score + '%"></i></span></span>' + chev + '</summary>';

    var sections = D.groups.map(function (g) {
      var ids = Object.keys(D.labels).filter(function (i) { return i.split("-")[0] === g[0] || (g[0] === "SETUP" && i === "DOCS"); });
      return '<div><h3>' + esc(g[1]) + ' <span style="font-weight:500">×' + D.weights[g[0]] + '</span></h3><div class="rows">' + ids.map(function (i) {
        var c = p.checks[i] || {};
        return '<div class="row">' + pill(c.s) + '<div><div class="label">' + esc(D.labels[i]) + '<code>' + i + '</code></div><p>' + md(c.t) + '</p></div></div>';
      }).join("") + '</div></div>';
    }).join("");
    var tasks = '<div><h3>Standard tasks <span style="font-weight:500">×' + D.weights.T + '</span></h3><div class="rows">' + Object.keys(D.tasks).map(function (t) {
      var c = p.tasks[t] || {};
      return '<div class="row">' + pill(c.s) + '<div><div class="label">' + esc(D.tasks[t]) + '<code>' + t + '</code></div>' + (c.t ? '<p>' + md(c.t) + '</p>' : "") + '</div></div>';
    }).join("") + '</div></div>';
    var notes = p.notes ? '<div><h3>Reviewer notes</h3><p class="notes">' + md(p.notes) + '</p></div>' : "";
    var links = '<div class="links"><a href="https://wordpress.org/plugins/' + esc(p.slug) + '/" rel="noopener">WordPress.org page</a>' +
      '<a href="' + D.repo + '/blob/trunk/reviews/' + esc(p.slug) + '.json" rel="noopener">Full review with code references</a></div>';

    return '<li><details class="card' + (top ? " top" : "") + (p.gated.length ? " excluded" : "") + '" data-slug="' + esc(p.slug) + '">' + summary +
      '<div class="detail">' + sections + tasks + notes + links + '</div></details></li>';
  }

  var state = { q: "", lane: "" };
  function render() {
    var q = state.q.toLowerCase();
    var shown = plugins.filter(function (p) {
      return (!state.lane || p.lane === state.lane) && (!q || (p.name + " " + p.slug).toLowerCase().indexOf(q) >= 0);
    });
    var ok = shown.filter(function (p) { return !p.gated.length; }), ex = shown.filter(function (p) { return p.gated.length; });
    var empty = '<li class="empty">No plugins match.</li>';
    document.getElementById("ranked").innerHTML = ok.map(card).join("") || empty;
    document.getElementById("excluded").innerHTML = ex.map(card).join("");
    document.getElementById("exdiv").style.display = ex.length ? "" : "none";
  }

  document.getElementById("q").addEventListener("input", function (e) { state.q = e.target.value; render(); });
  document.getElementById("lane").addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    state.lane = b.dataset.lane;
    this.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
    render();
  });

  var gateNames = D.gate.map(function (g) { return D.labels[g]; });
  document.getElementById("exnote").textContent = "These plugins fail at least one basic check, so they rank below every other plugin whatever their score.";
  document.getElementById("m-gate").textContent = "A Fail on any of these puts a plugin below all the others: " + gateNames.join(", ") + ".";
  document.getElementById("m-intro").textContent = "Each plugin's free version was downloaded from WordPress.org and its source reviewed against a fixed checklist " +
    "(reviews dated " + date(D.reviewed[0]) + (D.reviewed[0] !== D.reviewed[1] ? " to " + date(D.reviewed[1]) : "") + "). Claude Code did the reading and cited a file and line for every finding, and the top results were spot-checked by hand.";
  document.getElementById("weights").innerHTML = Object.keys(D.weights).map(function (g) {
    return "<li>" + GROUP_NAMES[g] + " <b>×" + D.weights[g] + "</b></li>";
  }).join("");
  document.getElementById("tasklist").innerHTML = Object.keys(D.tasks).map(function (t) { return "<li><b>" + t + "</b> " + esc(D.tasks[t]) + "</li>"; }).join("");
  document.getElementById("foot").innerHTML = 'Built ' + date(D.built) + ' from the <a href="' + D.repo + '">wordpress-mcp-plugins</a> repository, where the checklist, every review and the scripts to rerun it all live.';

  var root = document.documentElement;
  document.getElementById("theme").addEventListener("click", function () {
    var dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  });
  try { var t = localStorage.getItem("theme"); if (t) root.dataset.theme = t; } catch (e) {}

  if (location.hash) {
    render();
    var el = document.querySelector('[data-slug="' + CSS.escape(location.hash.slice(1)) + '"]');
    if (el) { el.open = true; el.scrollIntoView(); }
  } else render();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
