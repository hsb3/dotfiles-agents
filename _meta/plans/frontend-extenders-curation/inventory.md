---
title: "Frontend extenders inventory (Deliverable A of #48)"
type: reference
status: active
created: 2026-07-12
purpose: Every frontend skill/agent/plugin/external listed exactly once across the three homes (da roster, workbench incubator, live machine config), with type, home, status, and a grounded one-line "what it covers". Companion to overlap-map.md (B) and curation-plan.md (C).
notes: All cites re-verified fresh 2026-07-12 against current main (post #85/#87). Roster line numbers shifted from the 2026-07-03 plan (carbon-builder 62→64, obsidian-chat-ui 433→449, react-doctor 543→561, shadcn 593→613); use the numbers here. Coordinating with da#81 (demoting six obsidian-* skills to workbench) — obsidian-chat-ui row marked "demoting via #81".
---

# Frontend extenders inventory — Deliverable A (#48)

_Status: active · 2026-07-12 · report-only, no roster/target edits._

Three homes, every frontend item exactly once. Sub-rows enumerate the internal
skills/agents of each workbench bundle so the overlap map (B) has real material.
Verdicts and dispositions live in overlap-map.md and curation-plan.md.

## Home 1 — da roster (`primitives-core.yaml`), 4 items

| Item | Cite | Type / shelf | Origin | Disposition | Plugin | Covers |
| ---- | ---- | ------------ | ------ | ----------- | ------ | ------ |
| carbon-builder | primitives-core.yaml:64 | skill / core | authored | grandfathered-pending-use | none | Self-contained IBM Carbon builder for @carbon/react + web components; sequences UI via atomic-design (tokens→atoms→…→pages), no MCP. |
| obsidian-chat-ui | primitives-core.yaml:449 | skill / toggle | authored | grandfathered-pending-use (**demoting via #81**) | obsidian-plugin-dev | Chat/copilot sidebar UIs in Obsidian plugins via ItemView with streaming. Domain-scoped, not general frontend. |
| react-doctor | primitives-core.yaml:561 | skill / toggle | authored | grandfathered-pending-use | frontend-extras | Post-change React scan: security/perf/correctness/architecture, 0–100 score + diagnostics. |
| shadcn | primitives-core.yaml:613 | skill / toggle | sourced (shadcn-ui @ d0fae52) | grandfathered-pending-use | frontend-extras | Manages shadcn/ui projects via CLI: add/search/fix/debug/style/compose components. |

**Roster plugins carrying frontend items:**

| Plugin | Cite | Version | Bundles | Note |
| ------ | ---- | ------- | ------- | ---- |
| frontend-extras | plugins.yaml:20 | 0.0.1 | react-doctor + shadcn | The only pure-frontend roster plugin. **Not installed on this machine** (see Home 3). |
| obsidian-plugin-dev | plugins.yaml:32 | 0.1.1 | obsidian-chat-ui (+ 6 obsidian skills, 3 agents) | Domain plugin; obsidian-chat-ui is its only frontend-shaped member. |

## Home 2 — workbench incubator (`REGISTRY.md`), 5 candidates + internals

Counts below are **verified on disk** (agents/commands the 2026-07-03 plan's REGISTRY-derived
counts under-listed are included). Bundle rows are the inventory units; sub-rows are enumerated
for overlap analysis.

### 2a. carbon-webapp-team — REGISTRY.md:14 · incubating · hard-check pass

Plugin v0.1.0. 4 skills, 6 agents, 4 commands (`commands/` → fold-to-skills is its registry blocker).

| Internal | Type | Covers |
| -------- | ---- | ------ |
| carbon-2x-grid-system | skill | Carbon 2x grid: fluid/fixed grids, breakpoints, spacing, mini units, gutters. |
| carbon-component-library | skill | Reference for 60+ Carbon React components; static catalog + live fetch + patterns. |
| carbon-design-principles | skill | Carbon's four principles (openness, inclusivity, modularity, restraint). |
| carbon-for-ai-patterns | skill | Carbon-for-AI: AI labels, explainability, chatbot components, transparency styling. |
| carbon-orchestrator | agent | Team coordinator; deploys design-architect/component-selector/implementation-specialist. |
| design-architect | agent | App architecture: pages, components, navigation, data flow, Carbon compliance. |
| component-selector | agent | Map features → Carbon components; enforce reuse over custom. |
| implementation-specialist | agent | Only agent with Edit/Write; writes TS/React using Carbon components. |
| accessibility-validator | agent | WCAG 2.1 AA: axe-core, keyboard nav, screen-reader checks. |
| carbon-ai-integrator | agent | AI interface impl: chatbots, AI-content labels, explainability, Carbon-for-AI. |
| carbon-ai-interface / carbon-component / carbon-init / carbon-validate | commands (4) | Scaffold AI interface / component wizard / init project / validate imports+grid+a11y. |

### 2b. design-system-toolkit — REGISTRY.md:21 · incubating · hard-check FAIL (client token `raptorgpt`)

3 skills, 4 agents, 5 commands. **Client token is doc-only:** `raptorgpt` + machine path appear
in `SETTINGS_TEMPLATE.md:40-41` only; skills/agents/commands carry no hardcoded tokens.

| Internal | Type | Covers |
| -------- | ---- | ------ |
| design-system-fundamentals | skill | Strict five-layer frontend architecture, one-way deps, prevent component explosion. |
| storybook-best-practices | skill | Comprehensive Storybook stories: state coverage, variants, visual regression. |
| styling-system-patterns | skill | Tailwind v4 + four-layer token architecture + CVA type-safe variants. |
| architecture-validator | agent | Validate component-architecture compliance. |
| component-designer | agent | Design/create new UI components. |
| design-system-auditor | agent | Audit design-system completeness/consistency. |
| story-creator | agent | Create Storybook stories. |
| audit / create-component / create-story / refactor-to-library / validate | commands (5) | Design-system audit / new component / new story / refactor to library / validate compliance. |

### 2c. frontend-quality-guard — REGISTRY.md:23 · incubating · hard-check FAIL (client token `raptorgpt`)

2 skills, 3 agents, 3 commands, `hooks/hooks.json`. **Client token is doc-only:** `raptorgpt` +
machine paths appear in `TESTING.md` only (lines 11/17/240/276/314/379/390).

| Internal | Type | Covers |
| -------- | ---- | ------ |
| eslint-v9-migration | skill | ESLint v9 flat-config setup/migration with Next.js architecture-layer rules. |
| frontend-architecture | skill | Next.js layer separation, component taxonomy, adapter/view pattern. |
| component-classifier | agent | Classify components, recommend placement. |
| layer-validator | agent | Validate layer-boundary compliance. |
| type-safety-guardian | agent | Check TypeScript type errors. |
| hooks.json | hook | Hook configuration. |
| classify-component / migrate-eslint / validate-architecture | commands (3) | Classify + verify placement / ESLint v9 migrate / validate architecture. |

### 2d. style-canon — REGISTRY.md:31 · incubating · hard-check FAIL (client token `functionform`)

4 skills, 1 agent, 1 command. **Client token is doc-only:** `functionform` + machine path appear
in `TESTING.md:11` only.

| Internal | Type | Covers |
| -------- | ---- | ------ |
| browser-diagnostics | skill | Playwright capture: console, network failures, HTTP errors, uncaught exceptions. |
| color-tokens | skill | Semantic color token selection, WCAG compliance, token-misuse diagnosis. |
| motion-timing | skill | Carbon motion timing: easing + duration utilities for consistent animation. |
| spacing-scale | skill | Carbon 8px spacing scale, decision frameworks, consistency validation. |
| style-canon-validator | agent | Validate style compliance against canon standards. |
| validate | command | Run style-canon validation. |

### 2e. webapp-designer — REGISTRY.md:33 · park · hard-check pass

Plugin v0.1.0. 8 skills, 6 agents, 3 MCP servers (via `.mcp.json`: storybook, playwright,
chrome-devtools), no `commands/`. Registry note: "decompose on promotion." Attributes Vercel
Web Interface Guidelines + Anthropic data-viz.

| Internal | Type | Covers |
| -------- | ---- | ------ |
| browser-devtools-audit | skill | Chrome DevTools: perf traces, Lighthouse, console/network audits. |
| browser-visual-capture | skill | Playwright screenshots of Storybook stories at themes/viewports. |
| component-build-loop | skill | Closed loop: reuse → stories → interaction/a11y tests → screenshot → self-correct. |
| data-visualization | skill | Chart selection, dashboard design, number formatting, viz accessibility. |
| design-intake-spec | skill | Turn rough UI asks into tight component specs before code. |
| frontend-design | skill | **Name collides** with the `frontend-design` external (Home 3). Distinctive visual design: aesthetic direction, typography, layout. |
| story-writing-conventions | skill | Storybook authoring: states, args vs render, play-function tests. |
| visual-diff-critique | skill | Cross-theme render judgment, pixel-delta vs intent, feedback closure. |
| accessibility-auditor | agent | A11y audit: contrast/keyboard/focus/labeling/target-size + token-tied fixes. |
| dataviz-designer | agent | Chart/dashboard design for analytic SaaS. |
| design-director | agent | Taste pass: hierarchy/restraint/polish critique → punch-list, no code. |
| design-engineer | agent | End-to-end UI build over Storybook: spec→implement→test→screenshot→check. |
| design-systems-architect | agent | Tokens, type scale, spacing rhythm, theming, component-API governance. |
| interaction-designer | agent | State/flow/motion: empty/error/loading, microcopy, transitions. |

## Home 3 — live machine config (checked fresh 2026-07-12)

| Item | Location | Type | State | In scope? | Note |
| ---- | -------- | ---- | ----- | --------- | ---- |
| frontend-design (external) | externals.yaml:164 + cache `claude-plugins-official/frontend-design/` | external plugin (1 skill) | cached, **NOT enabled**, NOT in installed_plugins | in | Anthropic official "distinctive visual design" skill. Provenance gap: `upstream: null`, `ref: null`, `provides: ""`. **Name collides** with webapp-designer's internal `frontend-design`. |
| typescript-lsp (external) | externals.yaml:248 + cache `claude-plugins-official/typescript-lsp/` | external plugin | cached | boundary → **OUT** | Frontend-adjacent tooling (TS language server), not a UI/design extender. Same null upstream/ref provenance gap as frontend-design. Note-only. |
| assistant-ui (external) | cache `assistant-ui-skills/assistant-ui/{0.0.1,0.0.2}` + installed_plugins.json | external plugin (9 skills) | cached, **NOT enabled** | in (**new — not in the 2026-07-03 plan**) | Third-party marketplace plugin: "building AI chat interfaces with assistant-ui React library" (skills: assistant-ui, cloud, primitives, runtime, setup, streaming, thread-list, tools, update). Not tracked in da `externals.yaml`. |
| webapp-designer-local | cache `webapp-designer-local/webapp-designer/0.1.0` | local plugin (8 skills, 6 agents) | cached, **NOT enabled** | in (**new — not in the plan**) | The workbench webapp-designer built + cached locally as a plugin. Delta vs incubator 2e: drops `frontend-design` skill, adds `web-design-guidelines`, adds `commands/design-loop.md`. So the live build already resolved the `frontend-design` name collision by dropping that skill. |

**MISSING / clean (checked, no frontend straggler):**

- `~/.claude/skills/` — 16 symlinks (api-server-design, cmux, comms, devcontainer-setup, docx, dotfiles-expert, efficient-fable, fable-foreman, github-project-board, handoff, opencode-expertise, pptx, pptx-henry, setup-project-dashboard, update-project-dashboard, xlsx). **None frontend.** (The 2026-07-03 plan's "exactly 2 symlinks" is stale — the set grew, but the "no frontend straggler" conclusion holds.)
- `~/.claude/plugins/cache/dotfiles-agents/` — only `media-gen` + `project-workflow`. **`frontend-extras` is NOT installed.** The two roster frontend skills it bundles (react-doctor, shadcn) reach no live surface.
- `enabledPlugins` (settings.json:48-56) — **NO frontend plugin is enabled.** frontend-extras, frontend-design, assistant-ui, webapp-designer-local all sit dormant in cache. The entire frontend surface is currently non-live.
- `~/dotfiles/claude-code/.claude/rules/react.md` — a React authoring rule (not an extender; noted for completeness, out of inventory scope).

## Exactly-once check (acceptance)

Every roster item (4) and every REGISTRY frontend row (5) appears exactly once above; live-config
homes each carry an explicit row or a "none found" line. **No item appears in more than one home**
— the closest is the `frontend-design` NAME appearing as both a webapp-designer internal skill (Home 2e)
and the external plugin (Home 3); these are two distinct artifacts, flagged for the naming pass, not a
double-listing. Total distinct frontend inventory units: 4 roster + 5 workbench bundles + 3 live-config
externals/local (frontend-design, assistant-ui, webapp-designer-local) = **12 top-level units**;
typescript-lsp listed as an out-of-scope boundary row.
