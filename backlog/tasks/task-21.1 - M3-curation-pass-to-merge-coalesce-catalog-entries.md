---
id: TASK-21.1
title: 'M3: curation pass to merge/coalesce catalog entries'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:24'
labels:
  - evals
milestone: m-3
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
M3 (Track I): the curation pass that turns M1's descriptive analysis into real catalog changes. Consume the coverage matrix, relationship data (duplicative + directional), dispositions, and promotion outcomes to produce concrete catalog actions — merges, drops, boundary redraws — each recorded as finding -> action. Inputs are ready: the four promotion sub-issues and the coleam00 drop. Follows charter roadmap M3, decisions 9-10.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 At least one real catalog change lands from relationship data
- [ ] #2 Curation decisions recorded and the coverage matrix regenerated
- [ ] #3 Every DB row this pass supersedes is marked superseded, not overwritten or deleted
<!-- AC:END -->
