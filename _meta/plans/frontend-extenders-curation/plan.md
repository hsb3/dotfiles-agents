---
title: "feat: inventory the frontend extenders and curate to a core set"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #48 — inventory every frontend skill/agent/plugin across the roster, the workbench, and live config; map overlaps; curate to a named core set with dispositions and follow-on issues.
notes: Drafted 2026-07-03 from Henry's 2026-07-02 notes (_meta/NOTE.md). All source citations re-verified fresh 2026-07-03; the issue body's line numbers were stale and are re-cited below. Soft dep #31 CLOSED 2026-07-03 — outcomes harvested into this plan.
---

# feat: inventory the frontend extenders and curate to a core set

_The frontend surface spans nine-plus bundles across two repos and live machine config with
no single view and no owner for the set as a whole. #31 (closed 2026-07-03) already settled
the per-item bookkeeping — every roster frontend item now carries
`disposition: grandfathered-pending-use` and shadcn's sourced-origin flip landed — so what
RESIDUALLY remains is exactly this issue's three deliverables: one inventory that lists every
frontend item exactly once (roster four, workbench five, plus the live-config stragglers this
plan surfaces below), an overlap map for the known duplications (two Carbon bundles, shadcn
vs webapp-designer internals, design-system-toolkit vs style-canon, plus two found fresh:
react-doctor vs frontend-quality-guard, and webapp-designer's `frontend-design` skill vs the
`frontend-design` external), and a curation plan naming the core set with a disposition and
rationale per non-core item, executions spun off as follow-on issues. This issue itself is
report-only: no gates fire on it._

Status: active — deliverables A/B/C delivered 2026-07-12 (inventory.md, overlap-map.md, curation-plan.md + six draft-issue-*.md). Follow-on issue bodies staged, NOT filed (owner-approval gate).
Date: 2026-07-03 (plan) · 2026-07-12 (deliverables)

## Tracking

- Issue: #48 (`feat: inventory the frontend extenders and curate to a core set`, OPEN).
  Staged body: `_meta/plans/frontend-extenders-curation/issue-body.md`.
- Origin: Henry's 2026-07-02 notes (`_meta/NOTE.md`) — "inventory all the frontend
  skills/agents/plugins and make a plan to curate to a core set. there are way too many drafts."
- Relations: **soft dependency on #31 (Q-13 batch bootstrap-triage) — CLOSED 2026-07-03T14:45Z,
  COMPLETED**, so its outcomes are harvested here rather than waited on:
  - All 84 untriaged roster entries → `grandfathered-pending-use`; zero demotions, zero
    `qualified` (record: workbench `docs/promotions-log.md`, "2026-07-03 — Q-13 batch
    bootstrap-triage executed (da#31)"). `rg -c "disposition: untriaged" primitives-core.yaml`
    → 0, verified fresh.
  - The shadcn sourced-origin flip the issue flagged as pending has LANDED:
    `origin: sourced`, `vendor: shadcn-ui`, `upstream: https://github.com/shadcn-ui/ui`,
    `ref: d0fae528221011f75a8c64a917073904c2847493` (`primitives-core.yaml:596-600`).
  - Consequence for this plan: no frontend item was demoted by #31; the curation call is
    entirely this issue's to make. Every disposition below starts from
    `grandfathered-pending-use` (roster) or `incubating`/`park` (workbench).
- Contract impact: **report-only** — no gates fire on this issue itself (no `primitives-core/`,
  `targets/`, or manifest edits). Roster and targets drift guards fire on the follow-on
  execution issues (see Gate & contract hygiene).

## The problem (grounded in source)

**Line numbers in the issue body are stale.** Re-cited fresh 2026-07-03 below; the issue's
copies (obsidian-chat-ui 403, react-doctor 513, shadcn 563; workbench rows 11/15/17/25/27)
should not be trusted for grepping.

**EXISTS — roster (`primitives-core.yaml`), all four frontend items, all
`disposition: grandfathered-pending-use`:**

| Item | Cite (id line) | Type / shelf | Origin | Plugin membership |
| ---- | -------------- | ------------ | ------ | ----------------- |
| carbon-builder | primitives-core.yaml:62 | skill, core | authored | none |
| obsidian-chat-ui | primitives-core.yaml:433 | skill, toggle | authored | obsidian-plugin-dev |
| react-doctor | primitives-core.yaml:543 | skill, toggle | authored | frontend-extras |
| shadcn | primitives-core.yaml:593 | skill, toggle | sourced, shadcn-ui pinned | frontend-extras |

The `frontend-extras` plugin (`plugins.yaml:20`, v0.0.1, "shadcn/ui component patterns and
React diagnostics") bundles react-doctor + shadcn. carbon-builder sits on the core shelf in
no plugin. obsidian-chat-ui is frontend-shaped but domain-scoped to `obsidian-plugin-dev`
(`plugins.yaml:32`).

**EXISTS — workbench (`dotfiles-agents-workbench/REGISTRY.md`), all five candidates, with
contents verified on disk under `incubator/`:**

| Item | Cite (row) | Disposition | Hard checks | Contents (verified on disk) |
| ---- | ---------- | ----------- | ----------- | --------------------------- |
| carbon-webapp-team | REGISTRY.md:12 | incubating | pass | 4 skills (carbon-2x-grid-system, carbon-component-library, carbon-design-principles, carbon-for-ai-patterns) + 6 agents + commands/ to fold |
| design-system-toolkit | REGISTRY.md:16 | incubating | FAIL: client token raptorgpt + machine path | 3 skills (design-system-fundamentals, storybook-best-practices, styling-system-patterns) |
| frontend-quality-guard | REGISTRY.md:18 | incubating | FAIL: client token raptorgpt + machine path | 2 skills (eslint-v9-migration, frontend-architecture) + hooks/ + commands/ |
| style-canon | REGISTRY.md:26 | incubating | FAIL: client token functionform + machine path | 4 skills (browser-diagnostics, color-tokens, motion-timing, spacing-scale) |
| webapp-designer | REGISTRY.md:28 | park | pass | 8 skills (browser-devtools-audit, browser-visual-capture, component-build-loop, data-visualization, design-intake-spec, frontend-design, story-writing-conventions, visual-diff-critique) + 6 agents + 3 MCP per the registry row — "decompose on promotion" |

**EXISTS — live-config stragglers (checked fresh 2026-07-03):**

- `~/.claude/plugins/cache/claude-plugins-official/frontend-design/` — an installed external
  frontend plugin. It IS tracked in `externals.yaml:164` (`id: frontend-design`,
  `kind: plugin`) but with `upstream: null`, `ref: null`, `provides: ""` — a provenance gap
  against the externals convention (tracked externals record upstream + pinned ref,
  `externals.yaml:4`). Also collides by name with webapp-designer's internal
  `frontend-design` skill.
- `~/.claude/plugins/cache/claude-plugins-official/typescript-lsp/` — frontend-adjacent
  external; include in the inventory as boundary row (in or out is an inventory-time call).

**MISSING — checked and clean / absent:**

- `~/.claude/skills/` holds exactly 2 symlinks (`auth0-cli`, `find-skills`) — **neither is
  frontend**; no stragglers there.
- `~/.claude/plugins/cache/dotfiles-agents/` holds only `project-workflow` and
  `python-standards` — **`frontend-extras` is NOT installed on this machine**, so the two
  roster frontend skills it bundles (react-doctor, shadcn) currently reach no live plugin
  surface. Curation should decide the plugin's fate before anyone bothers installing it.
- No issue other than #48 owns the set-level view; the workbench rows carry only per-item
  blockers (REGISTRY.md rows above).

**The overlap surface (why per-item bookkeeping is not enough):** carbon-builder vs
carbon-webapp-team (same IBM Carbon domain — one no-MCP builder skill vs a 4-skill/6-agent
team plugin); shadcn vs webapp-designer internals (component-build-loop, frontend-design);
design-system-toolkit vs style-canon (styling-system-patterns vs the color/spacing/motion
token skills); react-doctor vs frontend-quality-guard (React diagnostics vs
frontend-architecture + eslint-v9-migration); webapp-designer's `frontend-design` skill vs
the `frontend-design` external plugin. None of these pairs is visible from any single
manifest.

## Deliverables

**A — Inventory.** One document section (in THIS plan folder — see open question 1) listing
EVERY frontend item exactly once across the three homes, with columns: item, type
(skill/agent/plugin/external), home (roster / workbench / live config), status
(disposition or registry state, harvested from #31 where applicable), and a one-line
"what it actually covers" grounded in its SKILL.md / README. Rows: the 4 roster items, the
5 workbench candidates (with their 21 internal skills + 12 agents enumerated as sub-rows so
overlap analysis has real material), the `frontend-design` external, the `frontend-extras`
plugin itself, and the boundary rows (obsidian-chat-ui, typescript-lsp) explicitly marked
in-scope or out-of-scope with a reason.
**Acceptance** (matches issue checkbox 1): grep of the inventory against
`primitives-core.yaml` and workbench `REGISTRY.md` finds no frontend item missing; every
item appears exactly once and carries a disposition; the two live-config homes
(`~/.claude/skills`, plugin caches) are each covered by an explicit row or an explicit
"none found" line.

**B — Overlap map.** For each of the five overlap pairs named above (plus any found during
A's sub-row enumeration): duplicate / subsumes / complements verdict, with the specific
files compared cited (e.g. carbon-builder SKILL.md vs carbon-webapp-team's
carbon-component-library). Output is a table: pair, verdict, evidence cite, survivor
candidate.
**Acceptance**: every A-inventory item appears in at least one overlap-map row OR an
explicit "no overlap" list; the five named pairs each have a verdict with a file-level cite;
no verdict rests on registry one-liners alone.

**C — Curation plan.** The named target core set (explicit list), plus a disposition for
every other item: keep / merge-into <target> / demote / retire, each with a one-line
rationale traceable to a B verdict or an A status. For every merge/demote/retire
disposition, a follow-on issue is drafted on the desk (staged `issue-body.md` per the
planning-desk flow) or explicitly declared unnecessary with a reason. Client-token bundles
get a split disposition consistent with the wb#25 precedent and the CLAUDE.md rule
(client-specific data → memory, not the extender): agnostic capability survives as
candidate, client tokens route to the client store.
**Acceptance** (matches issue checkboxes 2 and 3): the core set is named explicitly; every
non-core item has a stated disposition and rationale; follow-on issues are filed (or
explicitly declared unnecessary) for each merge/demote/retire disposition. Outward GitHub
filing gets owner approval first (`_config.md` convention); staging on the desk is free.

## Gate & contract hygiene

| Gate | Fires on #48? | Why |
| ---- | ------------- | --- |
| CI aggregate (make ci) | no PR, no fire | report-only: this issue lands a plan document under _meta/plans/, no code surface |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed by this issue |
| Targets drift guard (make build-check) | no | no primitives-core/, primitives-core.yaml, or plugins.yaml edit |
| Naming taxonomy | no | no new primitive or plugin named here; core-set NAMES proposed in C must pre-check docs/naming.md before follow-ons file |
| yamllint / actionlint | no | no YAML or workflow edits |

Follow-on execution issues are a different story and must each carry their own gate rows:
any merge/retire touching `primitives-core/` fires the **roster drift guard**; any edit to
`primitives-core/`, `primitives-core.yaml`, or `plugins.yaml` (e.g. dissolving or reshaping
`frontend-extras`) fires the **targets drift guard** (`targets/` is generated — never
hand-edit; `make build`). Workbench-side retirements need records in workbench
`docs/promotions-log.md` per the #31 precedent. Fixing the `frontend-design` external's
null upstream/ref edits `externals.yaml` → yamllint lane.

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A1 — roster sweep | primitives-core.yaml + primitives-core/skills/ 4 items + plugins.yaml | none | parallel |
| A2 — workbench sweep | REGISTRY.md + incubator/ 5 candidates, enumerate internal skills/agents/MCP | none | parallel with A1; read-only in the sibling repo |
| A3 — live-config sweep | ~/.claude/skills, plugin caches, externals.yaml cross-check | none | parallel; smallest; must run on this machine (live gh/disk state, per _config.md) |
| B — overlap map | pairwise file-level comparison | A1 + A2 + A3 merged | serialize: needs the full sub-row inventory |
| C — curation plan + follow-on drafts | core set, dispositions, staged issue bodies | B | serialize; owner approval gate before any issue files outward |

The three inventory sweeps are read-only, disjoint by home, and can run as parallel Explore
agents. B and C are judgment work and serialize after — one owner each, no fan-out. No
timelines; landing order only.

## Open questions / owner decisions

1. **Where does the inventory land?** The issue offers this plan folder or a workbench
   `docs/` note. **Recommend: this plan folder** (`_meta/plans/frontend-extenders-curation/`)
   — the desk is git-tracked and worktree-visible, the inventory spans BOTH repos plus live
   config so neither repo's docs/ is a natural sole home, and C's follow-on drafts stage
   here anyway. Leave a one-line pointer in the workbench if its gate process wants one.
2. **How aggressive is the core set?** Henry's directive says "way too many drafts."
   **Recommend: aggressive** — a single-digit core set of skills; the three client-token
   plugins do not survive as plugins (capabilities extracted, tokens to client store);
   webapp-designer stays parked-for-decomposition rather than entering the core whole.
   Alternative: conservative pass that only resolves the five named overlap pairs.
3. **Is obsidian-chat-ui in the frontend curation scope?** It is UI-flavored but
   domain-scoped to `obsidian-plugin-dev`. **Recommend: inventory yes, curation no** — list
   it for completeness (the acceptance grep will find it), disposition "keep, out of
   frontend core set, owned by the Obsidian domain."
4. **Client-token bundles (design-system-toolkit, frontend-quality-guard, style-canon):
   genericize or split?** **Recommend: split per the wb#25 precedent** — agnostic capability
   stays (or merges into a core-set survivor), `raptorgpt`/`functionform` tokens and machine
   paths route to the client memory store, mirroring the raptorxai-decks →
   presentation-designer split (REGISTRY.md, wb#10/wb#25). Alternative: in-place genericize
   PRs like #13/#14.
5. **Does the `frontend-design` external's provenance gap (`externals.yaml:164`,
   upstream/ref null) ride with this curation or file separately?** **Recommend: inventory
   row here + its own small follow-on issue** — it is a contract-hygiene fix (externals
   record upstream + pinned ref), not a curation judgment, and its name collision with
   webapp-designer's internal skill should be resolved by the curation naming pass.
6. **Is the missing `frontend-extras` install on this machine in scope?** **Recommend:
   note-only** — record in the inventory that the plugin is roster-defined but nowhere
   installed; whether it survives at all is a C decision, so installing it now would be
   churn.
