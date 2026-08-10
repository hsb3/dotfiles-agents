---
id: TASK-11
title: >-
  Vendored/distributed skill quality: provenance coverage, checks, feedback
  channel
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:23'
labels:
  - distribution
milestone: m-1
dependencies:
  - TASK-10
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/218'
priority: medium
type: feature
ordinal: 800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Motivating case: PocketBase skill shipped a false single-use-token claim (learn-pocketbase#56) with no upstream pin and no feedback route.

Three fixes: registry coverage for every vendored skill in use, a documented quality gate for distributed content, and a standard found-an-error pointer in every distributed skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every vendored skill currently in use, including PocketBase, has an externals.yaml entry with origin/upstream/ref populated; any skill without one has a reason recorded in externals.yaml naming specifically why it can't be tracked — not a bare "skipped" note
- [ ] #2 Quality-check step documented and wired into `make ci` or a named make target
- [ ] #3 Feedback pointer ships in all distributed skills
<!-- AC:END -->
