# WordCamp Joburg: MCP plugin comparison criteria (DRAFT)

**Scope:** MCP *server* plugins from WordPress.org, free version only.
**Audience lens:** site owners / non-developers.
**Test client:** Claude Desktop.
**Method:** feature checklist + the same scripted tasks for every plugin.
**Scoring:** weighted, each criterion scored 0-5, total out of 100.

## Shortlist filters (applied before hands-on testing)
1. Name or short description mentions MCP / Model Context Protocol
2. Role is "MCP server" (not client, guardrail or SEO-only tool)
3. Updated within the last 6 months
4. Tested up to a current WordPress version
5. Minimum signal: >= N active installs OR >= N ratings (N to be decided)

## Weighted criteria

| # | Area | Weight | Sub-criteria (each scored 0-5) |
|---|------|--------|--------------------------------|
| 1 | Setup & connection | 30 | Install-to-first-tool-call time; steps needed; works with Claude Desktop without a terminal; connection instructions in the plugin UI; quality of error messages |
| 2 | Security & auth | 30 | Auth method (OAuth / app password / API key); per-tool or per-role permissions; read-only mode; confirmation for destructive actions; audit log; safe defaults (off until enabled) |
| 3 | Capabilities | 25 | Pass rate on the standard task set (below); breadth (posts, pages, media, taxonomies, users, plugins, settings, blocks, WooCommerce); output quality (e.g. valid block markup) |
| 4 | Quality & maintenance | 15 | Update recency; active installs; rating; WP/PHP compatibility; uses Abilities API / MCP Adapter; docs and support responsiveness |

## Standard task set (run via Claude Desktop, pass / partial / fail)
1. List the 5 most recent posts
2. Create a draft post with a heading, paragraph and image
3. Edit an existing post's title and content
4. Upload an image to the media library
5. List installed plugins and their versions
6. Change a site setting (e.g. tagline)
7. Attempt a destructive action (delete a post): is it confirmed / logged?
8. Attempt something the connected user shouldn't be allowed to do: is it blocked?

## Open decisions
- Final weights (30 / 30 / 25 / 15 is a starting point)
- Shortlist thresholds (installs / ratings)
- Whether a "hard fail" (e.g. no auth, or exposes everything by default) caps the total score

## Decisions
- An endpoint that answers without credentials is NOT a hard fail when the plugin's source code shows it is deliberately public (e.g. `permission_callback` `__return_true` with a comment explaining why). Record the evidence (file:line).
