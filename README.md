# WordPress MCP plugins: code review

Compares the MCP server plugins in `shortlist.csv` (chosen as described in `SELECTION.md`) by
reviewing their source against `CHECKLIST.md`.

## Files

| File | What it is |
|---|---|
| `discover.py` | Finds every MCP-tagged plugin on WordPress.org, classifies it and applies the filters from `SELECTION.md`, into `discovery/` (git-ignored) |
| `shortlist.csv` | The 35 plugins to review, plus `mcp-adapter` as a reference |
| `SELECTION.md` | How the shortlist was chosen |
| `CHECKLIST.md` | The 22 checks and how each is scored |
| `fetch_sources.py` | Downloads each plugin's free version from WordPress.org into `sources/` (git-ignored) |
| `review.py` | Runs Claude Code headless on each plugin and writes `reviews/<slug>.json` |
| `reviews/` | One review per plugin |
| `review_combined.py` | Reviews a plugin together with the companion plugin(s) it needs, into `setups/` |
| `spotchecks/` | Manual checks of selected reviews against the source, one per plugin |
| `compare.py` | Combines `reviews/` into `comparison.md` (tables), `comparison.csv` (for a spreadsheet) and `ranking.md` (weighted ranking) |
| `build_site.py` | Builds `site/index.html`, the public ranking page, from `reviews/` with the same scores as `ranking.md` |
| `site/` | The ranking page: one self-contained HTML file, ready for any static host |

## Running it

Needs Python 3.9+ (standard library only) and, for the reviews, [Claude Code](https://claude.com/claude-code)
signed in to an account with enough usage. `review.py` uses `claude` from your `PATH`; set `CLAUDE_BIN` to use another.

To replicate the whole process from a fresh clone:

```sh
python3 discover.py                 # 1. find MCP plugins on WordPress.org -> discovery/candidates.csv
                                    #    (--write-shortlist refreshes the numbers in shortlist.csv)
python3 fetch_sources.py            # 2. download every shortlisted plugin into sources/ (git-ignored)
python3 review.py --force -j 3      # 3. review each one with Claude Code -> reviews/<slug>.json
python3 compare.py                  # 4. rebuild comparison.md, comparison.csv and ranking.md
python3 build_site.py               # 5. rebuild the ranking page in site/
```

- Step 1 only shows what is on WordPress.org today. Choosing the challengers was a judgement call, so the
  candidates are not the shortlist: edit `shortlist.csv` by hand to change which plugins are reviewed.
  `--as-of 2026-10-15 --wp-version 7.0` applies the original cutoffs. See `SELECTION.md`.
- Step 3 without `--force` reviews only plugins without a review, so `python3 review.py royal-mcp` does one.
  `--force` overwrites the spot-check corrections in `reviews/` (see below), and model output varies from
  run to run, so expect some checks to come out differently.
- `--config-dir ~/.claude-work` picks another Claude account (default: your environment's `CLAUDE_CONFIG_DIR`).
- `-j 4` reviews four at a time: same total usage, but it reaches the plan's session limit sooner.
- Claude only gets Read, Grep and Glob inside the plugin folder. Cited `file:line` references that do not exist are listed in `unverified_evidence`.

## Publishing the ranking page

`site/index.html` holds all its data and makes no external requests, so any static host can serve the
`site/` folder. On Spacefast: `sf publish ./site`, and run it again after `build_site.py` to update the
same space. Each plugin has a link (`index.html#<slug>`) that opens its details, and the page links to the
full reviews in this repository on GitHub.

Usage: the ai-engine pilot (one of the largest plugins) took about 3 minutes and reported $2.72 at API prices.
Check `/usage` in Claude Code before and after a few plugins to see what one costs against your plan.

## Plugins split across two plugins

Every plugin is reviewed on its own downloaded zip. That is the fair basis for a comparison, but it
under-measures a plugin whose tools live in a second plugin the vendor expects you to install.
`acrossai-mcp-manager` is the one plugin in the shortlist built that way: it ships the MCP server,
transport, OAuth, access control and wp-admin, while the abilities come from the separate free
`acrossai-abilities-manager`. Reviewed alone it serves 6 tools and does 1 of the 8 standard tasks,
which its own review notes point out.

`review_combined.py` runs the same checklist, schema, tool restrictions and citation check as
`review.py` over both plugins side by side, as they sit in `wp-content/plugins`:

```sh
python3 fetch_sources.py acrossai-mcp-manager acrossai-abilities-manager
python3 review_combined.py acrossai-mcp-manager acrossai-abilities-manager
```

It writes to `setups/`, not `reviews/`, so `compare.py` keeps ranking one zip per plugin and the
ranking is unchanged.

Two things to weigh before letting `setups/` feed the ranking. A combined run is not a like-for-like
comparison with `reviews/acrossai-mcp-manager.json`, because `fetch_sources.py` downloads the current
release while that review is of 0.4.3: the activity log that SAFE-LOG asks about arrived in 0.4.4, so
some of any difference is the version, not the companion plugin. And royal-mcp, cowboy-mcp and
miniorange-secure-mcp-server all ship integration packs that only register when another plugin is
active, so measuring deployed setups rather than plugins would affect several rows, not one.

### Spot-check results

Checked the top five and the two most-installed plugins. Top five: tried to break their Passes.
ai-engine and vibe-ai: tried to lift their Partials and Fails. Details and evidence in `spotchecks/<slug>.md`.

| Plugin | Result | Corrections (applied 2026-10-24) |
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
