---
id: TASK-6
title: Decide + execute evals/ and harness/ extraction to their own repos
status: To Do
assignee: []
created_date: '2026-08-04 00:42'
labels:
  - refactor
  - decision
milestone: m-0
dependencies: []
priority: medium
type: task
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
evals/ tracked data.db is 16MB of the repo's 29MB; consumers clone the marketplace repo under the new model. Owner already intends harness extraction. Decide scope (one or both, when), then execute the move with pointers back. Removes 3 workbench nodes from this repo's DAG.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ruling recorded
- [ ] #2 Extracted repos own their history; this repo keeps consume-pointers only
<!-- AC:END -->
