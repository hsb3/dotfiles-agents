---
id: TASK-12
title: Smoke loadability check
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-11
references:
  - smoke
priority: high
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Before spending a campaign on a candidate the owner needs to know it loads under each harness: --smoke injects it into an empty workspace, sends "Reply with exactly: OK" and prints a smoke block, writing a log but no ledger row (SPEC.md Smoke block). Builds groma component smoke.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Smoke uses the same injection, argv, environment and isolation as a with trial, in a fresh run dir deleted afterwards, and writes <runs-dir>/<harness>-smoke-<candidate>-<YYYYMMDD-HHMMSS>-<32 hex>.log with raw stdout and no header
- [ ] #2 The smoke block prints harness, kind, plugins loaded (names, (none) or (not reported)), plugin_error lines, the exit line and the verdict; an unhostable kind prints the skip line and fails
- [ ] #3 Exit is 0 when at least one cell ran and every cell that ran passed, else 1
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
