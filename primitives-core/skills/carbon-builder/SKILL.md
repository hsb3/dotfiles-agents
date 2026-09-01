---
name: carbon-builder
description: IBM Carbon Design System expert for React and Web Components — Carbon components, IBM Products UI, Carbon Charts, icons and pictograms, design tokens, IBM Plex, accessibility guidance, AI Chat / watsonx integration, and Carbon code generation or compliance audits. Use for any task that builds, reviews, or asks about Carbon UI code or Carbon design guidance.
---

# Carbon Builder

IBM's own Carbon Design System skill, composed over a vendored upstream body and the
hosted Carbon MCP server.

## How to use this skill

1. **Start at `base/SKILL.md`** — it is the full protocol: query planning, the capability
   matrix, mandatory context-gathering and code-audit rules, and the result-shape tables.
   Load `base/references/<topic>.md` only for the areas the task touches.
2. **The base assumes five MCP tools** (`code_search`, `docs_search`, `get_charts`,
   `labs_search`, `code_audit`) from the `carbon-design` server this plugin registers.
   The hosted server requires an **approved account**: if a tool call fails with an auth
   error, run `/mcp` and authenticate in the browser, and if no approved account exists,
   say so instead of guessing — approval is requested at
   <https://mcp.carbondesignsystem.com>.
3. **No MCP access** (no approved account, access lost, or server down)? The base's
   protocol still applies — substitute each tool with its public-docs equivalent and say
   plainly that answers came from public docs, not the MCP index:

   | Base calls | Substitute |
   |---|---|
   | `code_search` (components, variants, props) | WebFetch the component's usage page from `references/carbon-llms.txt`, and its Storybook (`react.carbondesignsystem.com` / `web-components.carbondesignsystem.com`) for live props and variants |
   | `code_search` (icons/pictograms) | WebFetch the icon library pages in the index; never guess export names — the base's icon-name warning still holds, so if the exact export cannot be verified, say so |
   | `docs_search` | `references/carbon-llms.txt` is the same docs corpus as an URL index — WebFetch the matching page |
   | `get_charts` | WebFetch the Carbon Charts docs (`charts.carbondesignsystem.com`) and the examples in `github.com/carbon-design-system/carbon-charts` |
   | `labs_search` | WebFetch `github.com/carbon-labs` package READMEs |
   | `code_audit` | Manual pass over `base/references/accessibility-rules.md` + `base/references/implementation-guardrails.md` as the checklist |

   Rules the substitution cannot honor (a mandatory `code_search` verification with no
   fetchable equivalent) are flagged as unverified in the output, never silently skipped.
4. **Writing a prompt or brief for Carbon codegen** (for a subagent or for the user)?
   Follow `references/prompting.md` — IBM's prompt-writing guidance for this exact
   MCP + skill pairing, distilled.

## Found an error?

`base/` is vendored verbatim and must never be hand-edited — an edit there registers as
upstream drift and fails the vendored-drift gate. Corrections go here in the authored
layer, with evidence; upstream-worthy ones belong on
<https://github.com/carbon-design-system/carbon-mcp/issues>.
