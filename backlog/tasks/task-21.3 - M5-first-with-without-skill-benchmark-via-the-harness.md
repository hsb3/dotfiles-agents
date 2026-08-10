---
id: TASK-21.3
title: 'M5: first with/without skill benchmark via the harness'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:24'
labels:
  - evals
milestone: m-3
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
M5 (Track II): the first comparative with/without benchmark for one skill, validating the evaluation loop end-to-end before M6. Author a task set with a machine-checkable reward, then measure the skill three ways — with-skill vs without vs a registry baseline — executing rollouts through the root `harness/` on a cheap model, storing results as `eval_runs` with full provenance. The execution backend is the root harness (charter decision 8; do not build a separate one) — interface and extraction checklist in `harness/README.md`. Depends on TASK-21.2 for scoring criteria and TASK-22 for harness isolation fixes: TASK-22's gaps let environment differences decide trial outcomes, so results predating that fix aren't trustworthy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A measured with/without/baseline delta stored in the database as `eval_runs` with provenance
- [ ] #2 The run reproduces from PROCEDURES.md
<!-- AC:END -->
