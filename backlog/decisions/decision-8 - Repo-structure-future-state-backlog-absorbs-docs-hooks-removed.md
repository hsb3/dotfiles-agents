---
id: decision-8
title: Repo structure future-state — backlog absorbs docs/, planning desk winds down
date: '2026-08-06'
status: proposed
---
## Context

The 2026-08-06 cleanup branch removed the empty top-level `hooks/` placeholder and
dissolved `docs/` into the backlog: the ADR mirrors moved to `backlog/decisions/`
(alongside the backlog-native `decision-N` series), and the extender-dev SOP
(`CONTRIBUTING.md`), `FLOW.md`, and `vendoring-rule.md` moved to `backlog/docs/`.
Backlog.md was already THE task system (decision-1); this makes `backlog/` the decision
and working-docs home too. `backlog/config.yml` now carries `harness` / `evals` area
labels so those workbenches' tasks, decisions, and docs are tracked in the same backlog.

## Proposed future-state (the owner rules)

Top level converges to five groups, every path homed in `flow.yaml`:

- **sources** — `primitives-core/` + `primitives-core.yaml` + `externals.yaml` +
  `translation.yaml`
- **distribution** — `plugins/` + `.claude-plugin/`
- **toolchain + gates** — `scripts/`, `tests/`, `Makefile`, `flow.yaml`, `.github/`
- **workbenches** — `backlog/` (tasks · decisions · docs · milestones · drafts),
  `harness/`, `evals/`, `_meta/` (winding down), `.claude/`
- **entry docs** — `README.md`, `AGENTS.md`, `CLAUDE.md`

`_meta/` winds down to `operations/` (untracked secrets) plus `briefings/` (comms
output). New planning work starts as backlog tasks/docs instead of `_meta/plans/`
folders; the existing `plans/`, `signoff/`, `research/`, and `_archive/` content stays
put as historical record until individually promoted or archived.

## Open questions (each needs an owner ruling, not a default)

1. **`_meta/` endgame** — wind down as above, or keep the full planning-desk convention?
2. **Published-standard divergence** — the shipped `repo-meta-structure` checklist
   mandates `docs/decisions/` (DOCS-03..05) and `_meta/HANDOFF.md` (META-06); this repo
   now fails both in its own published standard. Amend the published checklist (an IA
   change to a shipped skill, sign-off required) or record the divergence as deliberate?
   Same territory as task-15.
3. **Harness/evals extraction** (decision-5, task-6) is unchanged — still deferred; the
   new labels only make their work trackable meanwhile.

## Consequences

- Live docs, code, and gate scripts were retargeted to the new paths; historical records
  (ADR bodies, completed task cards, `_meta` trails, archives) keep their original path
  citations by design.
- `backlog/docs/FLOW.md`'s hand-authored homes table was already stale from before this
  move (it still lists retired pre-0017 surfaces); its refresh belongs to task-7.
