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
| `spotchecks/` | Manual checks of selected reviews against the source, one per plugin |
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

Where things stand (2026-10-24): all 35 reviewed, the comparison is built, and the spot-checks are done.
`reviews/` and `comparison.*` have not been changed by the spot-checks yet. Pick up at step 1.

1. **Settle three open decisions, then apply the corrections.**
   - **STD-TRANSPORT cutoff.** The checklist says "current protocol version" without naming one, so
     reviews disagree: on 2025-06-18, cowboy-mcp, miniorange-secure-mcp-server, alphabridge-mcp,
     wsp-mcp-ai-agents-connector and siteskite got Pass, while ai-engine, devcubic-ai-bridge-for-mcp,
     iato-mcp and aicom got Partial. Suggested rule: 2025-11-25 or later is Pass, older is Partial.
     Write the rule into `CHECKLIST.md`, then re-score STD-TRANSPORT for all 35 from each review's
     `protocol_version` value (no need to re-run `review.py`).
   - **Apply the spot-check corrections** below by editing `reviews/<slug>.json` by hand. Add a note to
     each changed check's summary saying it was corrected by the spot-check, then run `compare.py`.
   - **Consistency pass.** Most corrections came from checks applied unevenly, not from misread code.
     Compare SETUP-STEPS (how steps are counted) and STD-FREE (account-required = Fail) across all 35.
2. **Decide what counts most.** The P / ½ / F tally has no weighting. Choose which checks must pass
   (for example, no Fail on any SEC-* check) and which only break ties, then re-sort with that rule.
3. **Test the shortlist on a real site.** CAP-TASKS, HOST-* and SETUP-* are judged from code. Install
   the top candidates on a local site, connect Claude Desktop, run T1–T8 and count the actual setup steps.
4. **Write up the findings.** Use `comparison.md` plus the weighted ranking, and call out common gaps:
   SAFE-READONLY fails in 11 of 35, STD-ABILITIES in 10 of 35, and only 9 of 35 have a plugin-side
   confirmation for destructive actions (re-count after step 1).
5. **Keep it current.** Each review records the plugin version. After `fetch_sources.py`, re-run
   `review.py --force <slug>` for any plugin whose version changed, then `compare.py`.

### Spot-check results

Checked the top five and the two most-installed plugins. Top five: tried to break their Passes.
ai-engine and vibe-ai: tried to lift their Partials and Fails. Details and evidence in `spotchecks/<slug>.md`.

| Plugin | Result | Corrections to apply |
|---|---|---|
| easy-mcp-ai | Holds up | None. Fix the SAFE-SCOPE summary and notes: a bare `*` key *does* grant privileged tools once their group is on (`includes/auth/class-permission-guard.php:90`). SAFE-LOG evidence should be `class-server.php:2516-2540`. |
| agent-abilities-for-mcp | Holds up | None. Note: product, media and comment deletes are always permanent. |
| saddle | Holds up | None |
| albert-ai-butler | Holds up | None. Note: two read tools skip per-object checks; the approval queue only works on WordPress 7.1+. |
| miniorange-secure-mcp-server | 3 wrong | SAFE-CONFIRM Pass → Partial (`delete-user` and some force deletes have no confirm). HOST-LOCAL Partial → Pass (localhost redirect URIs accepted). STD-TRANSPORT Pass → Partial (only 2025-06-18), pending the cutoff decision. |
| ai-engine | 1 borderline | SETUP-STEPS Partial → Pass (3 steps, as siteskite was counted). |
| vibe-ai | Too harsh | SEC-AUTH, SEC-UNAUTH, SAFE-DELETE, STD-ABILITIES Partial → Pass. STD-FREE Partial → Fail (needs a WPVibe account). CAP-TASKS T7 Pass → Partial. Goes from 8 / 7 / 4 to 12 / 2 / 5. |

Verified by hand: the easy-mcp-ai wildcard claim, and the miniorange protocol version and localhost claims.
Not yet verified by hand: the vibe-ai and ai-engine corrections, which come from the spot-check alone.
