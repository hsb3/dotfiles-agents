---
title: "Frontend extenders curation plan (Deliverable C of #48)"
type: spec
status: draft
created: 2026-07-12
purpose: The named single-digit core set plus a keep/merge/demote/retire disposition + one-line rationale for every non-core frontend item, each traceable to an overlap-map verdict or an inventory status. Drafts the follow-on execution issues (staged only — owner approves before any GitHub filing).
notes: Aggressive curation per binding owner ruling 48.2 (single-digit core; client-token plugins split per wb#25, not kept). Naming proposals pre-checked against docs/naming.md (skill = <domain>-<capability> kebab; domain "frontend" is a listed example). Report-only — no roster/target edits land from #48.
---

# Frontend extenders curation plan — Deliverable C (#48)

_Status: draft · 2026-07-12. This issue delivers the plan only; executions are the drafted
follow-on issues below (staged on the desk, not filed — `_config.md` owner-approval gate)._

## The core set (aggressive, single-digit — ruling 48.2)

**Five skills** survive as the deliberate frontend core. Everything else keeps / merges into
one of these, demotes to the workbench, or retires. Names are proposed to conform to
`docs/naming.md` (`<domain>-<capability>`, domain `frontend`); the rename itself is a follow-on,
not part of #48.

| # | Core skill (proposed name) | Today | Home | Why core |
| - | -------------------------- | ----- | ---- | -------- |
| 1 | `frontend-carbon-builder` | carbon-builder | roster (core shelf) | Self-contained, no-MCP Carbon builder; the one lean skill that covers IBM-Carbon UI work end to end. docs/naming.md even cites this exact rename. |
| 2 | `frontend-shadcn` | shadcn | roster (toggle) | Sourced, pinned (shadcn-ui @ d0fae52); the only component-registry manager. Distinct layer from everything else (overlap row 2). |
| 3 | `frontend-react-doctor` | react-doctor | roster (toggle) | The only post-change React diagnostic scanner; complements, duplicates nothing (overlap row 4). |
| 4 | `frontend-design` (external) | frontend-design external | live config → roster external | Anthropic-official distinctive-visual-design skill; wins the name collision (overlap row 5). Needs its provenance gap fixed first (draft-issue-frontend-design-provenance). |
| 5 | `frontend-design-tokens` (merge target) | NEW — merge of styling-system-patterns + style-canon token skills | workbench → core on promotion | One genericized design-token/styling capability (four-layer tokens + Tailwind/CVA + color/spacing/motion), client-agnostic. Consolidates overlap row 3. |

Rationale for the cut line: the directive is "way too many drafts." A single-digit core keeps
exactly the capabilities with no live duplicate and clear ownership — a Carbon builder, a
component-registry manager, a React linter, a visual-design skill, and one token system. The
large design *teams* (webapp-designer, carbon-webapp-team) stay in the workbench as bundles to
decompose on promotion, not in the core whole.

## Disposition for every non-core item

| Item | Home | Disposition | Rationale (→ B verdict / A status) | Follow-on |
| ---- | ---- | ----------- | ---------------------------------- | --------- |
| obsidian-chat-ui | roster | **keep, out of frontend core** | Domain-scoped to obsidian-plugin-dev; no frontend duplicate (B no-overlap). Ruling 48.3: inventory yes, curation no. Also **demoting via da#81** to workbench. | none (rides #81) |
| frontend-extras plugin | roster | **retire the plugin shell; skills survive standalone** | v0.0.1, never installed on any machine (A Home 3). Its two skills (react-doctor, shadcn) are core in their own right; no need for the bundling plugin. | draft-issue-frontend-extras-retire |
| carbon-webapp-team | workbench | **stay incubating (workbench team); fold commands/ → skills** | Complements carbon-builder at the team level (B row 1); its registry blocker is the `commands/` fold, not a curation call. Not core. | none (workbench-internal, its existing blocker) |
| design-system-toolkit | workbench | **split (ruling 48.4 / wb#25): capability → `frontend-design-tokens` merge; tokens → client store** | styling-system-patterns folds into core #5 (B row 3); storybook-best-practices is a duplicate of webapp-designer's (B row 7). Client `raptorgpt` token is **doc-only** (SETTINGS_TEMPLATE.md:40-41), so extraction is clean. | draft-issue-client-token-bundles-split |
| frontend-quality-guard | workbench | **split: frontend-architecture survives as candidate; eslint-v9-migration survives; tokens → client store** | Complements react-doctor (B row 4); no duplicate of a core skill. Client `raptorgpt` token is **doc-only** (TESTING.md). Genericized capability can incubate toward core later. | draft-issue-client-token-bundles-split |
| style-canon | workbench | **split: color/spacing/motion tokens → `frontend-design-tokens` merge (Carbon-scoped variants); browser-diagnostics retire; token → client store** | Token skills fold into core #5 (B row 3); browser-diagnostics duplicates webapp-designer's browser skills (B row 6). Client `functionform` token is **doc-only** (TESTING.md:11). | draft-issue-client-token-bundles-split |
| webapp-designer | workbench | **stay parked; decompose on promotion (do NOT enter core whole)** | 8 skills + 6 agents + 3 MCP; hard-check passes but too large for core. Its unique skills (data-viz, design-intake, visual-diff, the 6 design-role agents) are candidates on decomposition; its browser + story skills are the survivor of B rows 6/7; its `frontend-design` internal is dropped (B row 5, already dropped in the live build). | draft-issue-webapp-designer-decompose |
| frontend-design (external) provenance | externals.yaml:164 | **fix in place (contract hygiene, not curation)** | `upstream: null, ref: null, provides: ""` violates the externals convention (externals.yaml:11). Ruling 48.5: own small follow-on. | draft-issue-frontend-design-provenance |
| typescript-lsp (external) | externals.yaml:248 | **out of frontend scope; same provenance gap noted** | TS language server, not a UI/design extender (A boundary row). Same null upstream/ref — fold its fix into the provenance issue as a second row, or leave to a general externals-hygiene pass. | note in draft-issue-frontend-design-provenance |
| assistant-ui (external, 9 skills) | live config cache | **decide: track-or-purge** | Cached + installed but **not enabled**, and **not tracked in da externals.yaml** (A Home 3, new find). Either add it to externals.yaml with proper provenance (it is a real Anthropic-adjacent frontend plugin) or purge the dormant cache. Owner call. | draft-issue-assistant-ui-decision |
| webapp-designer-local | live config cache | **retire the dormant local cache once webapp-designer decomposition lands** | Not enabled; it is the workbench bundle deployed locally as a plugin (A Home 3). Superseded by the decomposition path; the stale cache should be cleared, not maintained in parallel. | note in draft-issue-webapp-designer-decompose |
| frontend-extras **install** on this machine | live config | **note-only (ruling 48.6)** | Roster-defined, nowhere installed; whether it survives is decided by the retire disposition above, so installing now is churn. | none |

## Follow-on issues drafted (staged, NOT filed)

Six draft bodies staged in this folder. **None filed on GitHub** — owner reviews first (`_config.md`).
Each carries its own gate rows (roster/targets drift guards fire on execution, per the plan's gate table).

| Draft file | Fires which gate on execution |
| ---------- | ----------------------------- |
| draft-issue-frontend-extras-retire.md | targets drift guard (plugins.yaml + primitives-core.yaml edit) + roster drift guard |
| draft-issue-client-token-bundles-split.md | workbench-side (promotions-log record) + roster drift guard on any promotion to core |
| draft-issue-webapp-designer-decompose.md | workbench-side (promotions-log); roster/targets on any decomposed promotion |
| draft-issue-frontend-design-provenance.md | yamllint lane (externals.yaml edit) |
| draft-issue-assistant-ui-decision.md | yamllint lane (externals.yaml add) OR none (cache purge) |
| draft-issue-core-rename.md | targets drift guard (primitives-core.yaml id renames regenerate targets/) + naming lint |

## Acceptance (matches issue checkboxes 2 & 3)

- Core set named explicitly: five skills above. ✔
- Every non-core item has a stated disposition + rationale traceable to a B verdict or A status. ✔
- Follow-on issues drafted for each merge/demote/retire (or declared unnecessary with a reason). ✔
  Outward filing pends owner approval per `_config.md`.
