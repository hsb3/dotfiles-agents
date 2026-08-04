---
id: TASK-3
title: >-
  Retire dist lanes, generators, and drift guards; slim roster to provenance
  manifest
status: To Do
assignee: []
created_date: '2026-08-04 00:41'
labels:
  - refactor
milestone: m-0
dependencies:
  - TASK-2
priority: high
type: chore
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Delete dist/, gen_marketplace.py, gen_standalone.py, plugins.yaml, skill-catalog.yaml, check_roster.py, check_skill_catalog.py. Slim primitives-core.yaml to provenance (origin/upstream/targets/disposition). Repoint check_identity/check_provenance/check_hook_layout at the new layout. Update Makefile + tests.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 make ci green with no build/build-check targets
- [ ] #2 ADR 0015 provenance enforcement still passes against the slimmed manifest
<!-- AC:END -->
