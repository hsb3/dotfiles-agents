---
id: TASK-24
title: 'foreman-kit: lift arbitrary maxTurns cap on builder (silent mid-work stalls)'
status: To Do
assignee: []
created_date: '2026-08-04 00:44'
labels:
  - foreman-kit
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/222'
priority: high
type: bug
ordinal: 100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Work item for GH bug #222 (stays open as the report; close on fix). Lift maxTurns:50 on builder.md, port the scope-not-clock doctrine (oversized slice = loud early escalation), decide deliberately on reviewer(30)/scout(15) caps. Edit source, not dist (moot after task-3).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 builder cap lifted + scoping doctrine in agent prompt
- [ ] #2 reviewer/scout caps get a recorded keep-or-lift ruling
- [ ] #3 GH #222 closed on merge
<!-- AC:END -->
