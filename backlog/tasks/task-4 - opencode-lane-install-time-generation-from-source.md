---
id: TASK-4
title: 'opencode lane: install-time generation from source'
status: To Do
assignee: []
created_date: '2026-08-04 00:41'
labels:
  - refactor
  - opencode
milestone: m-0
dependencies:
  - TASK-2
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stop tracking dist/opencode; the opencode installer runs gen_opencode.py (stdlib-only) against primitives-core/ + translation.yaml at install time. Keeps one source tree serving both runtimes per the one-repo ruling.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Installer clones/pulls repo and lays down generated opencode config locally
- [ ] #2 dist/opencode removed from tracking; drift guard retired
- [ ] #3 Round-trip verified on this machine against a real opencode setup
<!-- AC:END -->
