---
id: TASK-24
title: 'foreman-kit: lift arbitrary maxTurns cap on builder (silent mid-work stalls)'
status: Done
assignee: []
created_date: '2026-08-04 00:44'
updated_date: '2026-08-06 21:31'
labels:
  - primitives
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
- [x] #1 builder cap lifted + scoping doctrine in agent prompt
- [x] #2 reviewer/scout caps get a recorded keep-or-lift ruling
- [x] #3 GH #222 closed on merge
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped in PR #233 (commit 0e71b57, 2026-08-04): builder and reviewer maxTurns caps lifted with the scope-not-clock doctrine in the agent prompts; scout keeps its deliberate maxTurns: 15 bounded-recon backstop (the recorded keep ruling — see primitives-core/agents/scout.md). GH #222 closed 2026-08-04. Board status was stale until the 2026-08-06 review (decision-7 cleanup).
<!-- SECTION:NOTES:END -->
