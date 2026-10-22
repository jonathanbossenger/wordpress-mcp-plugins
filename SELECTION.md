# WordCamp Joburg: MCP plugin selection

How the plugins in `shortlist.csv` were chosen. The list was built on 2026-10-15 from WordPress.org data and last changed on 2026-10-20.

## Scope

- MCP *server* plugins from the WordPress.org directory, free version only.
- Audience lens: site owners and non-developers.
- Test client: Claude Desktop.

## How the candidates were found

1. **Collect.** WordPress.org plugin API (`query_plugins`) for every plugin tagged `mcp`, `model-context-protocol`, `mcp-server`, `mcp-client` or `mcp-adapter`, plus a keyword match on "MCP" / "Model Context Protocol" in the name or short description. Result: 170 plugins.
2. **Enrich.** Full `plugin_information` for each: readme, tested-up-to, added date, support threads.
3. **Classify the role** from the name and short description (heuristic, with manual overrides after reading descriptions):

   | Role | Count | Meaning |
   |---|---|---|
   | server | 80 | Exposes WordPress to an AI client over MCP |
   | server? | 15 | Mentions "MCP server" only in the long description |
   | other? | 27 | No clear MCP role |
   | guardrail | 22 | Firewall, permissions, approvals or logs for MCP / abilities |
   | seo-visibility | 11 | llms.txt, AI visibility, "agent ready" SEO tools |
   | not-mcp-primary | 10 | MCP is a side feature of another product (e.g. Elementor) |
   | client | 4 | Lets WordPress call external MCP servers |
   | abilities-pack | 1 | Registers abilities, no server of its own |

   Only `server` plugins went forward.

## Shortlist filters

1. Name or short description mentions MCP / Model Context Protocol.
2. Role is "MCP server" (not client, guardrail or SEO-only tool).
3. Updated within the last 6 months.
4. Tested up to a current WordPress version (7.0 or later at the time).
5. Minimum signal: active installs or ratings. No fixed threshold was set; the lanes below were used instead.

## Lanes

| Lane | Count | Rule |
|---|---|---|
| Established | 17 | 100+ active installs |
| Challenger | 18 | Under 100 installs, hand-picked using a pre-screen signal count (below) |
| Baseline | 1 | `mcp-adapter` (the WordPress MCP Adapter), for reference only: not scored or installed |

Challenger pre-screen signals (one point each, 0-8, the `signals` column):
updated within 60 days; tested up to current WordPress; readme longer than 1,500 characters;
readme mentions security (permissions, authentication, OAuth, capabilities, read-only);
installation section has setup steps; mentions the Abilities API or MCP Adapter;
has at least one rating; has support threads.
The individual reasons for each hand-picked challenger were not recorded beyond this score.

## Changes since the list was built

- 2026-10-20: `ylabs-connector-for-wpwriter` (established) removed: closed on WordPress.org, cannot be installed.

## Known gaps in the list itself

Learned while testing, worth knowing before starting again:
- 3 plugins have no MCP server inside WordPress (the server runs elsewhere): `vibe-ai`, `diviops-agent`, `ylabs-ai-assistant-connector`. They fail filter 2 on closer reading.
- 7 accept OAuth only, which needs a browser consent flow: `miniorange-secure-mcp-server`, `albert-ai-butler`, `devcubic-ai-bridge-for-mcp`, `counterhand-mcp-for-woocommerce`, `admindra-mcp`, `siteskite`, `bcs-mcp-manager`.
