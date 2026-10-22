# Code review checklist

Every plugin in `shortlist.csv` is reviewed against the checks below by reading its source
(the free version from WordPress.org). `review.py` hands this file to Claude and stores one
`reviews/<slug>.json` per plugin.

## Rules for the reviewer

- Judge from the code, not the readme. When the readme and the code disagree, the code wins: note the disagreement in the summary.
- Every status except Unknown and N/A needs evidence: `path/to/file.php:123`, relative to the plugin folder. Built JavaScript (e.g. `app/index.js`) can be cited by file and a short quoted string instead of a line.
- Vendor libraries the plugin ships (e.g. `vendor/wordpress/mcp-adapter`) count: they are part of what the site runs.
- Pro-only features do not count towards a Pass. Mention them in the summary.
- Unknown means the code does not settle it. Say what is missing.

Statuses, always from the point of view of a site owner:

| Status | Meaning |
|---|---|
| Pass | Does this well |
| Partial | Does some of it, or only in some setups |
| Fail | Does not do it, or does it unsafely |
| Info | Descriptive check, no judgement (the value carries the facts) |
| Unknown | The code does not settle it |
| N/A | Does not apply, e.g. the plugin has no MCP server in WordPress |

## Security and auth

| ID | Question | Pass / Partial / Fail |
|---|---|---|
| SEC-AUTH | Which credentials does the MCP endpoint accept? Value: list from `application-password`, `api-key`, `bearer-token`, `oauth`, `cookie`, `none`. | Pass: every tool needs a credential tied to a WordPress user. Partial: a shared key not tied to a user, or some routes open. Fail: no authentication. |
| SEC-UNAUTH | With MCP enabled, can a request with no credentials list or call tools? Value: `{public_by_design: bool}`. | Pass: refused. Partial: lists tools but cannot call them, or only read-only public data, deliberately (comment or setting says so). Fail: tools callable without credentials. |
| SEC-CAPS | Does each tool call check the capability for that action (`current_user_can('delete_post', $id)` and so on), not only at the endpoint? | Pass: per tool / per object. Partial: one check at the endpoint (e.g. `manage_options`) for everything. Fail: no capability checks. |
| SEC-SECRETS | How are API keys and tokens stored? | Pass: hashed, or none stored. Partial: encrypted, or plain text but never shown again. Fail: plain text and shown or logged. N/A: no plugin-issued secrets. |
| SEC-DEFAULT | Out of the box, is MCP off until an admin turns it on, and are open or broad options off? | Pass: off by default. Partial: on by default but authenticated. Fail: on and reachable without credentials. |

## Safety controls

| ID | Question | Pass / Partial / Fail |
|---|---|---|
| SAFE-READONLY | Is there a read-only mode that applies to every connection type? | Pass: yes. Partial: only for some credentials, or only Pro. Fail: no. |
| SAFE-SCOPE | Can the site owner limit which tools a connection may use, per tool or per role? | Pass: per tool or per role, for every connection type. Partial: coarse groups, or only some credentials. Fail: all or nothing. |
| SAFE-CONFIRM | Is there a confirmation for destructive actions? `destructiveHint` annotations (the client asks), a required `confirm` argument, or an approval queue. Value: `{mechanism: ...}` | Pass: plugin-side confirmation or approval. Partial: annotations only. Fail: none. |
| SAFE-DELETE | Do delete tools move posts to the trash by default? | Pass: trash by default, permanent delete only when asked. Partial: permanent by default but limited. Fail: permanent by default. N/A: no delete tools. |
| SAFE-LOG | Are tool calls recorded somewhere an admin can read (who, what, when)? | Pass: in the free plugin, viewable in wp-admin. Partial: only to debug.log, or only Pro. Fail: not logged. |

## Capabilities

| ID | Question | Status |
|---|---|---|
| CAP-TOOLS | Which tools does the server expose once every option is switched on? Value: `{count, names}`. For meta-tool servers (e.g. MCP Adapter `discover-abilities` / `execute-ability`), list the abilities behind them. | Info |
| CAP-AREAS | Which areas do the tools cover? Value: list from `posts`, `pages`, `media`, `taxonomies`, `users`, `comments`, `plugins`, `themes`, `settings`, `blocks`, `woocommerce`. | Info |
| CAP-TASKS | Can each standard task (below) be done with the tools? Value: `{"T1": {"status": "Pass", "tool": "wp_get_posts"}, ...}` | Info at the top level; Pass / Partial / Fail per task |

Standard tasks:

| Task | What it needs |
|---|---|
| T1 | List the 5 most recent posts with title and status |
| T2 | Create a draft post with a heading, a paragraph and an image. Note whether content is stored as block markup or converted from Markdown/HTML |
| T3 | Edit an existing post's title and add to its content without losing the rest |
| T4 | Upload an image to the media library from a URL |
| T5 | List installed plugins with version and active state |
| T6 | Change the site tagline (`blogdescription`) |
| T7 | Delete a post: trash or permanent, confirmed, logged |
| T8 | A subscriber's credential cannot publish or delete posts |

## Standards

| ID | Question | Pass / Partial / Fail |
|---|---|---|
| STD-ABILITIES | Does it use the WordPress Abilities API or the MCP Adapter (registers abilities, or exposes abilities registered by other plugins)? | Pass: registers or exposes abilities. Partial: optional or Pro. Fail: neither. |
| STD-TRANSPORT | How is MCP served? Value: `{transports: [...], protocol_version, runs_in_wordpress: bool}` | Pass: Streamable HTTP inside WordPress, current protocol version. Partial: SSE only, or an older protocol. Fail: no MCP server in WordPress (an external relay or hosted service does the work). |
| STD-FREE | Is the MCP functionality complete in the free plugin? Value: list of Pro-only MCP features. | Pass: nothing important gated. Partial: some tools or controls are Pro. Fail: MCP itself needs Pro or an account. |

## Hosting, setup and docs

| ID | Question | Pass / Partial / Fail |
|---|---|---|
| HOST-LOCAL | Can Claude Desktop connect to a local site (`http://localhost`, no public URL, no HTTPS)? | Pass: yes, with a credential and a bridge such as `@automattic/mcp-wordpress-remote` or `mcp-remote`. Partial: only with workarounds. Fail: needs HTTPS, a public URL or the vendor's cloud. |
| HOST-PUBLIC | Does it work on a typical public host? Look for handling of a stripped `Authorization` header, CORS for web clients, caching or WAF notes, HTTPS requirements. | Pass: works, with fallbacks for common host problems. Partial: works, known host problems not handled. Fail: will not work without server changes. |
| SETUP-STEPS | How many steps from activating the plugin to the first tool call in Claude Desktop, following the plugin's own instructions? Value: `{count, steps: [...]}` | Pass: 3 or fewer. Partial: 4-6. Fail: more than 6, or a step needs a developer. |
| SETUP-NOTERM | Can a site owner connect without a terminal or editing a JSON config (OAuth with dynamic client registration, a connector URL for Claude's "Add custom connector")? | Pass: yes. Partial: only for some clients. Fail: needs a terminal or config file. |
| SETUP-GUIDE | Does the plugin's admin screen show how to connect (copyable URL, config snippet, step list)? | Pass: copyable and specific to this site. Partial: generic text or a link only. Fail: nothing in wp-admin. |
| DOCS | Is documentation easy to reach: setup steps in the readme, links from the plugin's admin screens, a docs site? Value: list of links found. | Pass: setup documented and linked from wp-admin. Partial: readme only, or docs incomplete or out of date. Fail: no setup documentation. |
