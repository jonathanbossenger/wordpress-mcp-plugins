# WordPress MCP plugins: code review

Compares the MCP server plugins in `shortlist.csv` (chosen as described in `SELECTION.md`) by
reviewing their source against `CHECKLIST.md`.

## Files

| File | What it is |
|---|---|
| `shortlist.csv` | The 35 plugins to review, plus `mcp-adapter` as a reference |
| `SELECTION.md` | How the shortlist was chosen |
| `CHECKLIST.md` | The 22 checks and how each is scored |
| `fetch_sources.py` | Downloads each plugin's free version from WordPress.org into `sources/` (git-ignored) |
| `review.py` | Runs Claude Code headless on each plugin and writes `reviews/<slug>.json` |
| `reviews/` | One review per plugin |

## Running it

Needs Python 3.9+ (standard library only) and Claude Code. `review.py` uses `~/.local/bin/claude`;
set `CLAUDE_BIN` if it is installed elsewhere.

```sh
python3 fetch_sources.py            # once per machine: sources/ is not in git
python3 review.py royal-mcp         # one plugin at a time
python3 review.py                   # every plugin without a review yet
```

- Plugins that already have a review are skipped; `--force` redoes them.
- `--config-dir ~/.claude-work` picks another Claude account (default: your environment's `CLAUDE_CONFIG_DIR`).
- `-j 4` reviews four at a time: same total usage, but it reaches the plan's session limit sooner.
- Claude only gets Read, Grep and Glob inside the plugin folder. Cited `file:line` references that do not exist are listed in `unverified_evidence`.

Usage: the ai-engine pilot (one of the largest plugins) took about 3 minutes and reported $2.72 at API prices.
Check `/usage` in Claude Code before and after a few plugins to see what one costs against your plan.

## Status

- Reviewed: ai-engine (2026-10-22, matches a manual read of its code).
- Reviewed 2026-10-23, smallest first, three at a time (`-j 3`) with a usage check between batches:
  ylabs-ai-assistant-connector, devcubic-ai-bridge-for-mcp, strifebridge-mcp, admindra-mcp, invizo-mcp,
  mcp-for-woocommerce, bcs-mcp-manager, sokket-site-connector-for-mcp, counterhand-mcp-for-woocommerce,
  mountdev-ai-mcp-connector, wsp-mcp-ai-agents-connector, alphabridge-mcp.
  13 of 36 done, $24.51 at API prices in total. Each batch of three took 2½–5 minutes.
- Next batch: iato-mcp, abilities-bridge, diviops-agent (the next smallest without a review).
- strifebridge-mcp: its 7 unverified citations say `includes/api.php` but the file is `api/api.php`.
  The cited lines exist there and match the review, so it's a wrong path, not made-up evidence.
- Decided (2026-10-23): HOST-LOCAL passes when a local connection is possible, whether or not the plugin documents it.
