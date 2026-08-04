---
id: TASK-14
title: 'foreman-kit: codify concurrent-session coordination (coord branch protocol)'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
labels:
  - foreman-kit
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/219'
priority: medium
type: feature
ordinal: 400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #219. Field-proven 2026-07-27 (two /waves sessions, one checkout): coord/<date> branch of empty commits carrying WHO / ACTIVE SUBAGENTS / CLAIMS+MERGE QUEUE / SURFACES / REPLY. Codify as a session-coord skill and/or SessionStart hook that surfaces the latest coord message. Open design points (branch naming, pruning, waves Phase-0 check) in the GH record.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Protocol shipped as skill and/or hook in foreman-kit
- [ ] #2 Waves Phase 0 checks for a live coord branch
<!-- AC:END -->
