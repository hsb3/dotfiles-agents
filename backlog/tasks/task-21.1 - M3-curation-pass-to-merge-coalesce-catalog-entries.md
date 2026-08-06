---
id: TASK-21.1
title: 'M3: curation pass to merge/coalesce catalog entries'
status: To Do
assignee: []
updated_date: '2026-08-06'
created_date: '2026-08-04 00:43'
labels:
  - extender-db
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/163'
parent_task_id: TASK-21
priority: medium
type: feature
ordinal: 1150
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
M3 (Track I): the combine/coalesce curation pass — consume the coverage matrix, relationship data (duplicative + directional), dispositions, and promotion outcomes to produce concrete catalog actions (merges, drops, boundary redraws), each recorded as finding -> action. This is where Milestone 1's descriptive analysis becomes real catalog changes. Inputs all landed: the four promotion sub-issues + the coleam00 drop. Refs: charter roadmap M3, charter decisions 9-10. Substance from closed GH #163.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At least one real catalog change landed from relationship data
- [ ] #2 Curation decisions recorded and the coverage matrix regenerated
- [ ] #3 Superseded DB rows marked superseded, never overwritten
<!-- AC:END -->
