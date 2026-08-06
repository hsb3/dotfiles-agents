---
id: TASK-11
title: >-
  Vendored/distributed skill quality: provenance coverage, checks, feedback
  channel
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-06'
labels:
  - quality
  - externals
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
Migrated from GH #218. Motivating case: PocketBase skill shipped a false single-use-token claim (learn-pocketbase#56); no upstream pin, no feedback route. (1) externals.yaml covers every vendored skill in use, (2) documented quality gate for distributed content, (3) standard found-an-error pointer in every distributed skill.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Registry coverage incl. PocketBase skill (or explicit disposition)
- [ ] #2 Quality-check step documented and wired into make ci or a named make target
- [ ] #3 Feedback pointer ships in all distributed skills
<!-- AC:END -->
