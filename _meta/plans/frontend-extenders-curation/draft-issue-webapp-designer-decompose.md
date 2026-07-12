# refactor: decompose webapp-designer on promotion; retire the dormant local plugin cache

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md. Owner approves before filing.

## Problem

`webapp-designer` (workbench, REGISTRY.md:33, `park`) is large: 8 skills, 6 agents, 3 MCP servers
(storybook, playwright, chrome-devtools via `.mcp.json`). The #48 core set deliberately does NOT
admit it whole — its registry note already says "decompose on promotion." Separately, a **dormant
local build** sits cached at `~/.claude/plugins/cache/webapp-designer-local/webapp-designer/0.1.0`
(8 skills, 6 agents, `commands/design-loop.md`) that is **not enabled**; its delta vs the incubator
source is that it already dropped the `frontend-design` internal skill (adding `web-design-guidelines`).

## Deliverables

- Decompose webapp-designer into promotable units rather than one plugin:
  - **Unique capabilities** (no inventory duplicate) → candidate skills: `data-visualization`
    (+ dataviz-designer agent), `design-intake-spec`, `visual-diff-critique`, and the design-role
    agents (design-director, design-engineer, design-systems-architect, interaction-designer,
    accessibility-auditor).
  - **browser-devtools-audit + browser-visual-capture** → survivors of overlap B row 6 (style-canon's
    browser-diagnostics retires into these).
  - **story-writing-conventions** → survivor of overlap B row 7 (design-system-toolkit's storybook skill retires).
  - **frontend-design internal** → drop (duplicate of the external, overlap B row 5; already dropped
    in the local build).
- Clear the stale `webapp-designer-local` cache once the decomposition path is chosen; do not
  maintain a parallel local plugin.
- Record in workbench `docs/promotions-log.md`.

## Acceptance

- [ ] webapp-designer's units carry explicit per-unit dispositions (promote-candidate / retire-duplicate / drop).
- [ ] No `frontend-design`-named internal skill remains under webapp-designer.
- [ ] `webapp-designer-local` dormant cache removed (or an explicit keep-reason recorded).
- [ ] promotions-log.md updated.

## Gates

- Workbench-side (`docs/promotions-log.md`); roster/targets drift guards on any decomposed unit promoted to core.

## Out of scope

- Promoting any decomposed unit to the roster core (separate, per-unit, after this decomposition).
- The 3 MCP servers' provenance (they are external tooling, not da mcp specs).
