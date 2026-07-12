---
title: "chore: rename the frontend core skills to the docs/naming.md taxonomy"
type: proposed-issue
status: draft
created: 2026-07-12
purpose: Staged chore issue from the #48 curation plan.
notes: Held with the #48 draft set pending owner entries in scope.md section 1; owner approves before filing.
---

# chore: rename the frontend core skills to the docs/naming.md taxonomy

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md. Owner approves before filing.

## Problem

`docs/naming.md` requires skills to be `<domain>-<capability>` kebab with `domain ∈ {…, frontend, …}`;
it even cites `frontend-carbon-builder` as the model. The surviving frontend core skills predate
that and are un-prefixed: `carbon-builder`, `shadcn`, `react-doctor`. Renaming aligns them with the
lint-enforced taxonomy so the core set is findable by domain.

## Deliverables

- Rename in `primitives-core.yaml` `id` + `source` path (and the on-disk `primitives-core/skills/<id>/` dir):
  - `carbon-builder` → `frontend-carbon-builder`
  - `shadcn` → `frontend-shadcn`
  - `react-doctor` → `frontend-react-doctor`
- Leave the external `frontend-design` as-is (already conformant).
- Regenerate `targets/` via `make build`; update any plugin membership references.

## Acceptance

- [ ] The three skills carry `frontend-` prefixed ids conforming to docs/naming.md.
- [ ] Naming lint (Phase 3 drift guard) passes.
- [ ] `make build-check` passes (targets regenerated, no drift).
- [ ] No dangling references to the old ids (`rg "carbon-builder|react-doctor|\bshadcn\b" primitives-core.yaml plugins.yaml targets/` resolves only to renamed forms).

## Gates

- Naming taxonomy lint + roster drift guard + targets drift guard (id renames regenerate targets/).

## Out of scope

- The sourced `shadcn` upstream pin (unchanged; only the local id changes).
- Sequencing vs the frontend-extras retire — coordinate so the two edits to the same skill blocks don't collide.
