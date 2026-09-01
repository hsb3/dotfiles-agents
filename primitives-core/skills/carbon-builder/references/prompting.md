# Prompting for Carbon codegen

IBM's prompt guidance for the Carbon MCP + carbon-builder pairing, distilled from
<https://carbondesignsystem.com/developing/carbon-mcp/prompts/> (full sample prompts live
there). Use it when writing a codegen brief — for a subagent, or shaping the user's ask.

## A complete brief names

- Framework and version: "Carbon React v11 (Core only)" / "Carbon Web Components v11
  with Carbon for IBM Products" — never just "React".
- UI goal + purpose, the **full component list** (Grid, Header, Tile, Form, …), layout
  (columns, spacing, breakpoints), sample data, and the **exact file list** to output.

## Non-negotiables to enforce in the brief

- MCP first: `code_search` for APIs + `docs_search` for usage/tokens/accessibility before
  any code; `get_charts` first for charts. Never let the model guess props or tokens.
- Only Carbon tokens — no ad-hoc colors or spacing, no Tailwind or utility frameworks.
- No inline token styles (`style={{ margin: '$spacing-05' }}`): small utility classes in
  the stylesheet using spacing tokens, applied by class.
- Required SCSS imports stated explicitly (`@use '@carbon/styles/scss/themes' as *;` etc.
  — the base's framework-rules reference has the full set).
- Semantic HTML + Carbon typography; IBM Plex via tokens.
- WCAG 2.2 + Carbon accessibility guidance: keyboard nav, focus order, ARIA.
- UI Shell Header always wraps page content in `Content` (fixed header overlaps otherwise).
- Props/variants must exist per `code_search` results; imports must resolve; compile on
  first attempt.

## Token conservation

- "After tool calls, do not restate results — say 'Received the necessary context.'"
- Emit only the requested files; no tests, README, or extras unless asked.
- Plan step-by-step ("high reasoning") before emitting final code, once.
