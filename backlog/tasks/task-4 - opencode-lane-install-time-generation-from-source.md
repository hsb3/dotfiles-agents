---
id: TASK-4
title: 'opencode lane: install-time generation from source'
status: In Progress
assignee: []
created_date: '2026-08-04 00:41'
updated_date: '2026-08-04 02:18'
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
- [x] #1 Installer clones/pulls repo and lays down generated opencode config locally
- [x] #2 dist/opencode removed from tracking; drift guard retired
- [x] #3 Round-trip verified on this machine against a real opencode setup
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Executed on feat/task-4-opencode-install-time. gen_opencode.py reworked: --out DIR only (no DIST mode, refuses non-empty target); scripts/install_opencode.sh = consumer entry (gen to tempdir -> generated install.sh --global/--project). AC2 had landed with task-3 (dist/opencode untracked, guard retired). Round-trip on this machine vs opencode 1.18.11: --project laydown discovered fully (23/23 skills via 'opencode debug skill', 4/4 agents via 'opencode agent list'). Live bug found+fixed: opencode rejects CC named agent colors (color: cyan) at config load — transform now drops color. Observation for later: pptx-themes/base/SKILL.md (vendored Anthropic base) is discovered as its own skill in opencode.
<!-- SECTION:NOTES:END -->
