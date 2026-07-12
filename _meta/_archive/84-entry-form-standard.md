---
title: "Build plan — use-case entry forms + shared milestone-set standard (#84)"
type: plan
status: active
created: 2026-07-12
purpose: Land the two standards #84 asks for as planning-desk reference content — the backlog/bench entry forms (one shared core, two applications) and the shared P-N milestone set + gate labels — grounded in shipped practice, not invented policy.
---

# feat: use-case entry forms + shared milestone-set standard (2026-07-12)

_Both standards implied by the ratified `use-case-driven-backlog` decision have no home and would
vanish when the vault registries freeze (#84). This lands them as `planning-desk` reference content so
future backlog seeding (#49) and board setup (#9) cite them. Deliverable A is amended (owner,
2026-07-11) to also define the workbench bench-entry form; the two entry forms share one field core._

Status: active · Date: 2026-07-12

## Tracking

- #84 (this issue). Pairs with #49 (backlog seed) and the Agent Extenders board (hsb3/projects/9).
- Owner amendment 2026-07-11: Deliverable A also defines the bench-entry form (scope doc gating
  `dotfiles-agents-workbench/incubator/` entry). Acceptance addition: `docs/extender-lifecycle.md`
  references the form at intake; first application wb#37.

## What already exists (verified)

- `use-case-driven-backlog` decision — an extender enters a queue because a named project/workflow
  needs it, ranked by nearness of the need; vendor list is a sourcing catalog, not a backlog.
- The `#49` backlog-seed plan already uses a three-field entry shape (use case, existing assets, source
  pointers) — `_meta/plans/extender-ideas-backlog-seed/plan.md` Deliverable A. This standard names and
  generalizes that shape; it does not invent it.
- `dotfiles-agents` milestones P1–P4 exist with promise-level descriptions (verified via
  `gh api repos/hsb3/dotfiles-agents/milestones`). The gate-label concept (`gate:<promise>`) is from
  Henry's project protocol; `gate:cross-tool` is live on the P4 milestone.
- The Agent Extenders board (hsb3/projects/9) is joint da+wb, one item set, "milestones mirror across
  both repos" (verified via the board's `shortDescription`).
- The promotion gate H/J checks (`dotfiles-agents-workbench/docs/promotion-gate.md`,
  `docs/extender-lifecycle.md`): J1 = proven ≥2 real uses, J4 = distinct — the bench-form maps its
  driving-use-case field to J1 and its overlaps field to J4.

## Deliverables

**A — The standard as a new planning-desk reference file.**
`primitives-core/skills/planning-desk/references/entry-forms-and-milestones.md` — Part 1 (entry forms:
shared core + backlog application + bench application) and Part 2 (shared milestone set: P-N promise
milestones + gate labels + the Agent Extenders board mapping). `SKILL.md` gains a pointer to it.

Acceptance:
- The file states the backlog-entry form (fields + representation: project-task issue, story-as-framing,
  spec-link-when-large) and the bench-entry form (scope doc, fields mapped to H/J).
- It defines the shared milestone set + how a project adopts it, and maps the Agent Extenders board.
- Independently verifiable: open the file, confirm the shared-core field table, the two application
  tables, the milestone table, and the board mapping table are all present and cite their sources.

**B — Wiring (minimal, pointer-only into #49-owned files).**
- `_meta/plans/extender-ideas-backlog-seed/plan.md` gets a one-line blockquote pointer to the entry
  form (no rewrite — #49 owns that file).
- `dotfiles-agents-workbench/docs/extender-lifecycle.md` Stage 1 (Intake) references the bench-entry
  form (separate wb PR; the `#84` acceptance addition; first application wb#37).

**C — Version bump + regenerate.**
- `plugins.yaml` `project-workflow` 0.2.4 -> 0.2.5 (patch; skill-content addition, matching the 0.2.x
  content-patch precedent — 0.2.0 was for a membership change).
- Root `.claude-plugin/marketplace.json` bumped to match.
- `make build` regenerates `targets/` + `targets/claude-code/.claude-plugin/marketplace.json` +
  `primitives-core-translation-results.json`; never hand-edited.

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| `make ci` (aggregate) | yes | skill content changes; run in the da worktree |
| Targets drift guard (`make build-check`) | yes | `primitives-core/` + `plugins.yaml` + marketplace changed; run `make build`, commit the regenerated bundles |
| Roster drift (`make check`) | no | no primitive added/removed/renamed; only content inside an existing skill |
| Naming taxonomy (`make names`) | no | no new primitive/plugin named |
| Canonical-doc amendment | no | no spine doc (CHARTER/CLAUDE/AGENTS) behavior changes |
| Sibling-wb test import | may skip | `tests/test_check_naming.py` imports `../../dotfiles-agents-workbench/scripts/promote_check.py`; from a worktree that path resolves off the worktree root and the test skips (guarded) |

## Landing order & coordination

1. da PR (this repo): reference file + SKILL.md pointer + #49 pointer + version bump + `make build`.
2. wb PR: one edit to `docs/extender-lifecycle.md` Stage 1; cross-references the da PR.
3. **The #81 re-triage PR also rebuilds `targets/` + the lock.** This PR merges SECOND; on merge it is
   rebased and `make build` re-run so the generated bundles reconcile against #81's rebuild.

## Open items (Proposed — for owner ratification)

1. **Unranked-wishlist rule** — an idea with no driving use case yet enters as a one-line unranked
   wishlist entry (not a ready issue), promoted only when a use case claims it. Grounded in the #49
   owner-decision default; marked **Proposed** in the standard until ratified as a standing rule.
