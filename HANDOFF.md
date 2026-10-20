# Handoff: test automation and manual test sheet

Written 2026-10-19 so work can resume on another machine. Read `criteria.md` first for the rubric.

## Where things stand

| Area | Status |
|------|--------|
| Shortlist (35 plugins) + WordPress.org metadata scoring | Done: `shortlist.csv`, `build_scoring_sheet.py` -> `mcp-plugin-scoring.xlsx` |
| Site setup (Studio site per plugin, install, activate, seed content) | Done: `setup_test_sites.sh` (logs to `setup_results.tsv`, git-ignored) |
| Manual copy/paste test sheet | Done, untested against live sites: `build_manual_test_sheet.py` -> `mcp-manual-test-sheet.xlsx` |
| Automated tests (`run_tests.py` + `test_config.json`) | Built 2026-10-19, prototyped on mcp-for-woocommerce, royal-mcp, ai-engine. Writes `results.json` |
| Single place for all results | `results.json` exists (auto checks only). `import_manual.py` and scoring-sheet integration not built |

## run_tests.py (built)

Checks per slug: S1 active/version, A2 MCP routes before enabling, A3pre unauth probe before enabling, ABIL source markers (registers/reads abilities, MCP Adapter), EN enable MCP via `enable_php` in `test_config.json`, A3 unauth probe after enabling (tools returned = hard-fail candidate), AUTH authenticated tools/list (auth method, tool count, names), BR breadth by tool-name keywords. Entries are `source: auto`; `source: manual` entries are never overwritten.

- `test_config.json` has an entry for all 35 shortlisted plugins (done 2026-10-19, from reading each plugin's source and testing on its Studio site). Fields: `enable_php` (run as admin; may echo `token:<value>` to hand back a key made with the plugin's own API), `endpoint`, `auth` (basic / bearer / header / none / oauth), `install_plugins` (companion plugins, e.g. the MCP Adapter), `transport: external`, `public_by_design` + `public_evidence`, `notes`.
- Rule used: the config switches MCP on AND enables every available tool/scope, so tool counts measure capability; out-of-the-box state is captured by A2/A3pre before that.
- Results (all 35 plugins run): 25 authenticate automatically; 7 are OAuth only (AUTH = Manual: miniorange, albert, devcubic, counterhand, admindra, siteskite, bcs); 3 have no MCP server in WordPress (vibe-ai, diviops-agent, ylabs-ai-assistant-connector).
- ylabs-connector-for-wpwriter was removed from the shortlist on 2026-10-20 (closed on WordPress.org). It is excluded in `make_shortlist.py`; the shortlist, both workbooks, `test_config.json`, `results.json` and its Studio site were updated or removed.
- Findings worth a look: invizo-mcp 2.0.8 ships without vendor/ (endpoint never registers without the MCP Adapter plugin); cowboy-mcp API keys always act as the first admin; strifebridge stores its legacy token in plain text; several readmes say OAuth only but accept application passwords (acadium, publishio, rectus).
- MCP Adapter meta-tool servers (nibwp, rectus, invizo): run_tests calls discover-abilities and records ability_count. cowboy-mcp (2 meta-tools) and acrossai (14 grouped toolsets) still undercount: judge breadth manually.
- Default auth when a plugin has no entry is an admin application password (Basic), which works on Studio sites.
- EN sets the site option `run_tests_mcp_enabled_at`; after that A2/A3pre are skipped. Recreate the site (`setup_test_sites.sh delete` + `setup`) to re-check defaults.
- Sites are left running with MCP enabled.
- First results: all 3 off by default. mcp-for-woocommerce is open without auth once enabled; marked `public_by_design` in `test_config.json` (source says read-only storefront tools), so not a hard fail (rule in `criteria.md`). royal-mcp 401 without key, 259 tools. ai-engine 401 without auth, 46 tools.
- Breadth is name-based, so it undercounts generic tools (ai-engine handles pages through `wp_get_posts` with a post type).
- Not automated yet: T1-T8 (LLM-driven client), T8 low-privilege user, audit-log diff, time to first tool call (an automated time says nothing about the human setup time).

Setup script fixes this session: installs "Requires Plugins" dependencies before activating; no `mapfile` (macOS bash 3.2). Manual sheet: A3 has a "Disabled" option and says to re-probe after enabling; `xdg-open` replaced with `open || xdg-open`. Settings page guess in A4 is wrong for mcp-for-woocommerce (`mcpfowo-settings`) and ai-engine (`mwai_settings`).

## What can be automated (original proposal)

- Endpoint discovery: list REST routes matching `mcp` via `studio wp eval`.
- Unauthenticated probe: POST JSON-RPC `tools/list` with no credentials. A returned tool list means "exposed by default" and should set "Security hard fail?" = Y.
- Time to first tool call: time activation to a successful authenticated `tools/list`.
- Tool inventory and breadth: keyword-match tool names against posts, media, users, plugins, settings, blocks, WooCommerce.
- T1-T8 via a headless MCP client driven by an LLM (e.g. Claude Agent SDK), verified with WP-CLI (`post list`, `option get blogdescription`, `post exists`). Tool names differ per plugin, so a fixed script will not work.
- T8: low-privilege (subscriber) user + application password, try to publish and delete, verify with WP-CLI that nothing changed.
- Audit log: diff plugin tables and options before and after T7.
- Abilities API / MCP Adapter: grep plugin source for `wp_register_ability` / `mcp-adapter`.

## What stays manual (covered by the manual sheet)

- Credentials: each plugin issues auth differently (app password, API key, OAuth). Needs per-plugin config or Playwright; OAuth is the worst case.
- Claude Desktop connection and UX: works without a terminal, in-plugin connection guide, error message quality.
- Output quality (valid block markup is checkable, overall quality is a human call), docs and support.
- Caveat: the headless client tests the plugin's MCP server, not Claude Desktop. Say so in the talk. LLM agent results are non-deterministic, so use pass/partial/fail with a retry count.

## Manual test sheet (`mcp-manual-test-sheet.xlsx`)

Sheets: README, Runbook, Results, Slugs. On Runbook pick a plugin slug in B4; the grey command cells are formulas that update per plugin. 23 steps in sections A-E: pre-connect probes, credentials and Claude Desktop config (via `mcp-remote`), T1-T8 (prompt + WP-CLI verify), quality checks, cleanup. Results sheet has one row per plugin with Pass/Partial/Fail dropdowns.

Regenerate: `python3 build_manual_test_sheet.py` from the repo root. Needs `openpyxl` (not installed system-wide on the first machine; use a venv: `python3 -m venv venv && venv/bin/pip install openpyxl`).

Assumptions and known caveats:
- Sites live in `$HOME/Studio/mcp-tests/<slug>` (`MCP_TEST_ROOT` in the setup script). `$HOME` is used because `~` does not expand inside double quotes.
- Commands use `studio wp --path ...` and assume you run them from the repo folder.
- The Claude Desktop config uses `mcp-remote` (needs Node.js), with the header passed via `env` to avoid the space-escaping bug on Windows. It only suits plugins that accept Basic auth.
- The admin settings URL in step A4 is a guess based on the slug.
- Formulas recalculated cleanly in LibreOffice, but the commands have not been run against a real Studio site.

## Gaps identified

1. Results live in three places: `mcp-plugin-scoring.xlsx`, `mcp-manual-test-sheet.xlsx`, `setup_results.tsv`. T1-T8 must be copied from the manual sheet into the Tasks sheet by hand.
2. Several manual Results columns (auth method, minutes to first call, tool count, T7 confirmed / audit log) have no matching column or formula on the Scores sheet.
3. The unauthenticated probe does not set the hard-fail flag automatically.
4. No rule for which result wins when an automated and a manual run cover the same check.

## Proposed next steps (agreed direction, not started)

1. Single source of truth: `results.json` (or SQLite) keyed by slug and check ID (A3, T1-T8, D1...), each entry with `source: auto|manual`.
2. `run_tests.py` for the automatable checks, writing `source: auto` results. Prototype on 2-3 plugins first (e.g. `mcp-for-woocommerce`, `royal-mcp`) to see how much credential handling varies.
3. `import_manual.py` to load the manual sheet's Results into the store, with manual overriding auto where both exist.
4. Change `build_scoring_sheet.py` to read the store so Tasks, the hard-fail flag and the new columns fill in automatically; the scoring workbook stays the one presentation file.
5. Fold `setup_results.tsv` into the store.

## Open decisions (from `criteria.md`)

Final weights (30/30/25/15 is a starting point), shortlist thresholds, and whether a hard fail caps the total score (the Weights sheet currently caps at 40).
