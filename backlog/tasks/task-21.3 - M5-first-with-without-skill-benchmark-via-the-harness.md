---
id: TASK-21.3
title: 'M5: first with/without skill benchmark via the harness'
status: To Do
assignee: []
updated_date: '2026-08-06'
created_date: '2026-08-04 00:43'
labels:
  - extender-db
dependencies:
  - TASK-21.2
  - TASK-22
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/165'
parent_task_id: TASK-21
priority: medium
type: feature
ordinal: 1250
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
M5 (Track II): the first comparative with/without benchmark for one skill. Author a task set with a machine-checkable reward, then measure the skill three ways — with-skill vs without vs a registry baseline — executing rollouts through the root `harness/` on a cheap model, storing results as `eval_runs` with full provenance. Validates the whole evaluation loop end-to-end before M6. The execution backend IS the root harness (charter decision 8; do not build a separate one); interface + extraction checklist in `harness/README.md`. Gated on M4 (task-21.2) for scoring criteria and on task-22 (harness isolation fixes) — GH #172's gaps let environment differences decide trial outcomes, so results predating that fix aren't trustworthy. Substance from closed GH #165.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A measured with/without/baseline delta stored in the database as `eval_runs` with provenance
- [ ] #2 The run reproduces from PROCEDURES.md
<!-- AC:END -->
