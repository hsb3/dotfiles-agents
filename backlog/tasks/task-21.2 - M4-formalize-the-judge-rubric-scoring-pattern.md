---
id: TASK-21.2
title: 'M4: formalize the judge + rubric scoring pattern'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:24'
labels:
  - evals
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/164'
parent_task_id: TASK-21
priority: medium
type: feature
ordinal: 1200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
M4 (Track II): formalize the judge + rubric + case-score scoring pattern onto the database's `assessments` table. Each quality dimension gets one judge prompt carrying a deterministic rubric (severity -> formula -> threshold -> worked examples), a first-class error state, and a reproducible scoring procedure — folding in the version-2 judging criteria. This makes scoring deterministic so M5 and M6 rest on a stable rubric. Inputs ready: W1 calibration flags, the four M1 boundary rules, the composition-tells duplication test, the `closedloop-judges` framework rows.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Version-2 criteria live in the frameworks' `criteria` fields, superseding version 1 per the charter
- [ ] #2 Re-running one already-judged pass under version-2 criteria reproduces its scores per PROCEDURES.md
<!-- AC:END -->
