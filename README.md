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
| `compare.py` | Combines `reviews/` into `comparison.md` (tables) and `comparison.csv` (for a spreadsheet) |

## Running it

Needs Python 3.9+ (standard library only) and Claude Code. `review.py` uses `~/.local/bin/claude`;
set `CLAUDE_BIN` if it is installed elsewhere.

```sh
python3 fetch_sources.py            # once per machine: sources/ is not in git
python3 review.py royal-mcp         # one plugin at a time
python3 review.py                   # every plugin without a review yet
python3 compare.py                  # rebuild comparison.md and comparison.csv
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
  Then, in three more batches of three: iato-mcp, abilities-bridge, diviops-agent, aicom, vibe-ai,
  cowboy-mcp, track-debug, acadium-agent-publisher, publishio.
  Then royal-mcp, saddle, stifli-flex-mcp ($7.14 for the batch, about 3 minutes), and
  rectus-content-access-for-mcp, miniorange-secure-mcp-server, webo-mcp ($6.91, about 3½ minutes).
  On 2026-10-24: nibwp, siteskite, agent-abilities-for-mcp ($8.37, about 3¾ minutes), and
  acrossai-mcp-manager, albert-ai-butler, ai-workflow-automation-ai-agent-hub ($7.83, about 4½ minutes),
  and finally easy-mcp-ai on its own ($3.57, about 2½ minutes).
  All 35 done (`mcp-adapter` is the baseline and is not fetched or reviewed), $65.12 at API prices
  in total.
- Cost by size: the first 13 (0.6k–23k PHP lines) cost $0.90–$2.62 each; the next nine (25k–48k)
  $0.49–$0.97 each; the six after (51k–85k) $1.54–$3.10 each; the next six (86k–164k) $2.23–$2.95
  each; easy-mcp-ai (244k) $3.57.
- strifebridge-mcp: its 7 unverified citations say `includes/api.php` but the file is `api/api.php`.
  The cited lines exist there and match the review, so it's a wrong path, not made-up evidence.
- Decided (2026-10-23): HOST-LOCAL passes when a local connection is possible, whether or not the plugin documents it.

## Next steps

1. **Spot-check the surprises by hand.** The reviews are from Claude reading the code, so check the
   ones the conclusions will rest on: the top five in `comparison.md` (easy-mcp-ai, agent-abilities-for-mcp,
   saddle, albert-ai-butler, miniorange-secure-mcp-server) and the two biggest by installs, which score
   low (ai-engine 8 Pass / 11 Partial, vibe-ai 8 Pass / 4 Fail). Read each review's Fail and Partial
   evidence against the source.
2. **Decide what counts most.** The P / ½ / F tally has no weighting. Choose which checks must pass
   (for example, no Fail on any SEC-* check) and which only break ties, then re-sort with that rule.
3. **Test the shortlist on a real site.** CAP-TASKS, HOST-* and SETUP-* are judged from code. Install
   the top candidates on a local site, connect Claude Desktop, run T1–T8 and count the actual setup steps.
4. **Write up the findings.** Use `comparison.md` plus the weighted ranking, and call out common gaps:
   SAFE-READONLY fails in 11 of 35, STD-ABILITIES in 10 of 35, and only 9 of 35 have a plugin-side
   confirmation for destructive actions.
5. **Keep it current.** Each review records the plugin version. After `fetch_sources.py`, re-run
   `review.py --force <slug>` for any plugin whose version changed, then `compare.py`.
