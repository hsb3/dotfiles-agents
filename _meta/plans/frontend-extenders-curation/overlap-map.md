---
title: "Frontend extenders overlap map (Deliverable B of #48)"
type: reference
status: active
created: 2026-07-12
purpose: Pairwise duplicate/subsumes/complements verdicts across the frontend inventory, each with a file-level cite and a survivor candidate. Feeds curation-plan.md (C).
notes: Verdicts grounded in the actual SKILL.md/agent frontmatter compared, not registry one-liners. Cites verified fresh 2026-07-12.
---

# Frontend extenders overlap map — Deliverable B (#48)

_Status: active · 2026-07-12. Verdict vocabulary: **duplicate** (same job, keep one) ·
**subsumes** (one is a superset) · **complements** (adjacent jobs, both can survive)._

## The named pairs (all five from the plan) + two found during enumeration

| # | Pair | Verdict | Evidence (files compared) | Survivor candidate |
| - | ---- | ------- | ------------------------- | ------------------ |
| 1 | carbon-builder (roster) vs carbon-webapp-team (wb) | **complements** (team subsumes at the domain level) | carbon-builder/SKILL.md (single atomic-design builder, no MCP) vs carbon-webapp-team/skills/carbon-component-library + /agents/implementation-specialist.md (decomposed catalog + 6-agent orchestration). carbon-builder ≈ the team's implementation-specialist discipline; the team adds catalog, grid, principles, AI patterns, orchestration. | carbon-builder (as the lean core skill); carbon-webapp-team stays a workbench team, not core. |
| 2 | shadcn (roster) vs webapp-designer internals | **complements** | shadcn/SKILL.md (CLI component-registry manager: add/search/fix) vs webapp-designer/skills/component-build-loop + frontend-design (Storybook build-and-critique loop + visual design). Different layers: shadcn fetches/installs components; component-build-loop builds+critiques them. | Both survive different homes: shadcn = roster core; component-build-loop = webapp-designer bundle. |
| 3 | design-system-toolkit vs style-canon | **complements, partial token overlap** | design-system-toolkit/skills/styling-system-patterns (generic four-layer token system, Tailwind v4 + CVA) vs style-canon/skills/{color-tokens,spacing-scale,motion-timing} (Carbon-specific, token dimension split into 3 skills). Same "manage design tokens" concept at different grain and stack; not the same skill. | Merge target: a single genericized token/styling capability (see C); style-canon's Carbon-specific split folds in or stays Carbon-scoped. |
| 4 | react-doctor (roster) vs frontend-quality-guard | **complements** | react-doctor/SKILL.md (post-change diagnostic scan: security/perf/correctness scored 0–100) vs frontend-quality-guard/skills/frontend-architecture (prescriptive Next.js layer/taxonomy rules) + /skills/eslint-v9-migration. react-doctor judges after the fact; frontend-quality-guard prescribes structure + lints. Different jobs. | react-doctor = roster core; frontend-quality-guard's architecture guidance survives as candidate (client tokens stripped). |
| 5 | webapp-designer's `frontend-design` skill vs `frontend-design` external plugin | **duplicate (name + intent)** | webapp-designer/skills/frontend-design/SKILL.md ("distinctive visual design: aesthetic direction, typography, layout") vs cache `claude-plugins-official/frontend-design/.../SKILL.md` (Anthropic "distinctive, intentional visual design … not templated defaults"). Near-identical intent; **the live webapp-designer-local build already dropped its internal frontend-design** (replaced by web-design-guidelines), so the collision is de-facto resolved in favor of the external. | The Anthropic external `frontend-design` (fix its provenance, see draft-issue). Drop the webapp-designer internal on decomposition. |
| 6 (found) | webapp-designer vs design-system-toolkit vs style-canon (browser diagnostics) | **duplicate** (browser/console capture) | webapp-designer/skills/browser-devtools-audit + browser-visual-capture (Chrome DevTools + Playwright capture) vs style-canon/skills/browser-diagnostics (Playwright console/network/error capture). style-canon's browser-diagnostics is a subset of webapp-designer's browser skills. | webapp-designer's browser skills (richer); style-canon's browser-diagnostics is redundant. |
| 7 (found) | webapp-designer vs design-system-toolkit (Storybook stories) | **duplicate** | webapp-designer/skills/story-writing-conventions + design-engineer agent vs design-system-toolkit/skills/storybook-best-practices + story-creator agent. Both cover Storybook story authoring / state coverage / variants. | webapp-designer's story skills (part of a coherent build loop); design-system-toolkit's storybook skill is redundant. |

## Coverage — every inventory item lands in an overlap row or a no-overlap list

**In an overlap row above:** carbon-builder, carbon-webapp-team (all 4 skills + agents via row 1),
shadcn, webapp-designer (component-build-loop, frontend-design, browser-*, story-writing-conventions,
design-engineer via rows 2/5/6/7), design-system-toolkit (styling-system-patterns, storybook-best-practices
via rows 3/7), style-canon (color/spacing/motion-tokens + browser-diagnostics via rows 3/6),
react-doctor, frontend-quality-guard (frontend-architecture + eslint via row 4), frontend-design external.

**No overlap (unique capability — no duplicate elsewhere in the inventory):**

| Item | Home | Why unique |
| ---- | ---- | ---------- |
| obsidian-chat-ui | roster | Obsidian-domain chat sidebar; no general-frontend counterpart. |
| carbon-2x-grid-system / carbon-design-principles / carbon-for-ai-patterns | carbon-webapp-team | Carbon-specific grid/principles/AI patterns; carbon-builder references but does not duplicate these as standalone skills. |
| data-visualization + dataviz-designer | webapp-designer | Only data-viz capability in the whole inventory. |
| design-intake-spec, visual-diff-critique, interaction-designer, design-director, design-systems-architect, accessibility-auditor | webapp-designer | Distinct design-discipline roles; no counterpart elsewhere. |
| eslint-v9-migration | frontend-quality-guard | Only ESLint-v9 tooling in the inventory. |
| assistant-ui (external, 9 skills) | live config | Only assistant-ui React chat-library coverage; no counterpart. Not tracked in externals.yaml. |
| typescript-lsp | live config | Out-of-scope boundary (TS language server, not a UI/design extender). |
| webapp-designer-local | live config | The webapp-designer bundle as a deployed plugin; overlaps its own incubator source (2e), not a separate capability. |

No verdict above rests on a registry one-liner: each cites the compared SKILL.md / agent frontmatter.
