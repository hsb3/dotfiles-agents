---
id: TASK-11
title: 'Run command: argument parsing, validation order and the grid'
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-9
  - TASK-10
references:
  - commands
  - grid
  - cli
priority: high
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
agent-harness <candidate> --candidate-dir <path> is the main command: it validates everything before any agent CLI runs (harness names exit 3, then bad input exit 2), runs every preflight-passing cell with resume, and prints the preconditions, progress and summary lines and the report (SPEC.md Behaviour, Run flags, Grid). Also serves --report and --help. Builds groma components commands, grid and the entry point cli.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Validation order and exit codes match the spec (3 unknown harness, 2 bad input, usage to stdout on --help with exit 0, to stderr with exit 2 on no arguments); defaults resolve against the package dir
- [ ] #2 Cells run harness-major, failed preflight cells are skipped with their message, exit is 0 when any cell passed preflight and 1 when none did
- [ ] #3 Trials already in the ledger are skipped; preconditions, progress and summary lines match the spec
- [ ] #4 --report prints the candidate report without --candidate-dir and exits 0
- [ ] #5 An end-to-end test with stub CLIs runs the smoke-echo case under claude and appends rows a rerun does not repeat
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
