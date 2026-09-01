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
3. **No MCP access?** Fall back to `references/carbon-llms.txt` — the official index of
   carbondesignsystem.com documentation URLs — and WebFetch the pages the task needs. Say
   plainly that the answer came from public docs, not the MCP index, and do not generate
   component code the base's Context Gathering Rule would have required `code_search` for
   without flagging that the verification step was unavailable.
4. **Writing a prompt or brief for Carbon codegen** (for a subagent or for the user)?
   Follow `references/prompting.md` — IBM's prompt-writing guidance for this exact
   MCP + skill pairing, distilled.

## Found an error?

`base/` is vendored verbatim and must never be hand-edited — an edit there registers as
upstream drift and fails the vendored-drift gate. Corrections go here in the authored
layer, with evidence; upstream-worthy ones belong on
<https://github.com/carbon-design-system/carbon-mcp/issues>.
