---
id: TASK-3
title: >-
  Retire dist lanes, generators, and drift guards; slim roster to provenance
  manifest
status: Done
assignee: []
created_date: '2026-08-04 00:41'
updated_date: '2026-08-06 21:31'
labels:
  - gates
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
- [x] #1 make ci green with no build/build-check targets
- [x] #2 ADR 0015 provenance enforcement still passes against the slimmed manifest
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Executed on feat/task-3-retire-dist (PR #229). dist/ (530 files) + gen_marketplace/gen_standalone/check_skill_catalog + plugins.yaml/skill-catalog.yaml deleted; roster slimmed to provenance manifest; check_roster.py rewritten (not deleted — parse_roster is the shared parser for identity/provenance/gen_opencode/evals); ci.yml drift-guards steps swapped with job name kept verbatim (branch-protection pin); gen_opencode+translation.yaml dormant for task-4; publish.yml fails-loudly pending task-5; evals/ingest.py repointed to marketplace.json+assemblies. make ci green (92 tests), provenance green vs slimmed manifest, fresh install verified.
<!-- SECTION:NOTES:END -->
