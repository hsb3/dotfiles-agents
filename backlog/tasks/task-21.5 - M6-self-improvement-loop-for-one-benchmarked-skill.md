---
id: TASK-21.5
title: 'M6: self-improvement loop for one benchmarked skill'
status: To Do
assignee: []
created_date: '2026-08-04 00:44'
updated_date: '2026-08-06 21:33'
labels:
  - evals
milestone: m-3
dependencies:
  - TASK-21.2
  - TASK-21.3
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/166'
parent_task_id: TASK-21
priority: medium
type: feature
ordinal: 1300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
M6 (Track II): the self-improvement loop for one benchmarked skill — propose an edit, re-evaluate on a held-out split, keep the edit only on strict measured improvement, adopt with a human in the loop. Closes the loop from measuring a skill (M5) to improving one; the strict-improvement gate and human adopt step prevent quality regression. Gated behind M4 (task-21.2) + M5 (task-21.3). Substance from closed GH #166.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One skill improved with a measured before/after eval delta on a held-out split
- [ ] #2 Improved artifact plus both eval runs stored; the human adopt step recorded
- [ ] #3 Negative runs retained as evidence
<!-- AC:END -->
