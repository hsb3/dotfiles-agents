---
id: TASK-5
title: Decide + implement the publish model (main as merge gate vs install-from-dev)
status: To Do
assignee: []
created_date: '2026-08-04 00:42'
updated_date: '2026-08-04 02:55'
labels:
  - refactor
  - decision
milestone: m-0
dependencies:
  - TASK-3
priority: high
type: task
ordinal: 500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
With no tracked dist, publishing no longer needs the filtered parented assembly. Options: keep main as a plain fast-forward release gate (publish = merge dev→main, guards retired) or retire main and install from dev. Owner ruling, then implement: publish.yml, branch protection, the three no-main-checkout guards, publish-to-main skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ruling recorded (backlog decision + ADR cross-ref)
- [ ] #2 Publish workflow and guards match the ruling
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Owner ruling 2026-08-04 (decision-4): main = plain fast-forward release gate; retire the filtered-assembly build + guards. Constraint: evals/ and harness/ do NOT publish to main. Now unblocked + High.
<!-- SECTION:NOTES:END -->
