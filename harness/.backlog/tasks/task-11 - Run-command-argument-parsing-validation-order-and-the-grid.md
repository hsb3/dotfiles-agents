---
id: TASK-11
title: 'Run command: argument parsing, validation order and the grid'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:27'
labels: []
milestone: m-0
dependencies:
  - TASK-9
  - TASK-10
references:
  - commands
  - grid
  - cli
  - evaluate-a-candidate
  - trial
  - candidate
modified_files:
  - .groma/flows/evaluate-a-candidate.md
  - .groma/index.md
  - .groma/systems/harness/containers/agent-harness-cli/components/cli.md
  - .groma/systems/harness/containers/agent-harness-cli/components/commands.md
  - .groma/systems/harness/containers/agent-harness-cli/components/grid.md
  - .groma/systems/harness/containers/agent-harness-cli/components/trial.md
  - src/candidate.ts
  - src/cli.ts
  - src/commands.ts
  - src/grid.ts
  - src/harnesses.ts
  - src/trial.ts
  - test/commands.test.ts
  - test/grid.test.ts
  - test/helpers/cli.ts
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
- [x] #1 Validation order and exit codes match the spec (3 unknown harness, 2 bad input, usage to stdout on --help with exit 0, to stderr with exit 2 on no arguments); defaults resolve against the package dir
- [x] #2 Cells run harness-major, failed preflight cells are skipped with their message, exit is 0 when any cell passed preflight and 1 when none did
- [x] #3 Trials already in the ledger are skipped; preconditions, progress and summary lines match the spec
- [x] #4 --report prints the candidate report without --candidate-dir and exits 0
- [x] #5 An end-to-end test with stub CLIs runs the smoke-echo case under claude and appends rows a rerun does not repeat
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/commands.ts: main(argv, io) -> exit code. Two-pass parsing: harness names validated first (exit 3), then usage errors, configs, --trials/--timeout integers >= 1, missing --candidate-dir (exit 2); --help to stdout (0), no args to stderr (2). Defaults resolve against the package dir; relative paths against cwd; the results path is kept as given for the summary line. Dispatch: run -> grid, --report -> report.
2. src/grid.ts: runCandidate(opts, io): load candidate and cases (loader errors -> exit 2), cells harness-major x models (default per harness), preflight (stderr, skip), --version, preconditions line, resume walk over cases x configs x trials with progress lines, summary line and report per cell; exit 0 if any cell passed preflight else 1.
3. src/cli.ts: bun shebang, calls main with console io, sets the exit code, maps unexpected errors to exit 1.
4. candidate.ts: resolve the candidate dir to an absolute path (messages keep the path as given).
5. Tests: test/commands.test.ts (validation order and messages, help/usage, defaults) and test/grid.test.ts end-to-end through src/cli.ts with stub CLIs (smoke-echo under claude, resume on rerun, failed preflight cells, exit codes, --report).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 92 pass, 0 fail. test/commands.test.ts: --help/no-args, exit 3 before usage errors (also for --report and campaign), every exit-2 usage/config/candidate-dir message, candidate and dataset errors before any stub CLI call, defaults against the package dir and relative paths against the cwd. test/grid.test.ts runs src/cli.ts end to end with stub CLIs: smoke-echo under claude (exact preconditions/progress/summary lines, report, two rows, two logs, no run dirs left, no grader call), rerun skips both keys, relative --results shown as given with a relative log_path, harness-major cells across two models with failed-preflight messages, exit 1 when no cell passes (missing CLI, missing OPENAI_API_KEY), a failing trial, --report without --candidate-dir, and the shipped check.py under the real python3. Manual: `bun src/cli.ts --help`, no args (exit 2), unknown harness (exit 3). groma: matched 2; accepted commands, grid and 10 planned relations; added grid -> commands (Io callbacks); flow evaluate-a-candidate added over 20 existing steps; lint clean.
Correction to TASK-10: check.py now gets the harness own environment minus the XDG variables (no per-run HOME), following the common env rule for a child that belongs to no harness, so a version-manager python3 shim keeps working.
Product calls: usage errors print `agent-harness: <detail> (see agent-harness --help)`; --flag=value is accepted; the last repeated flag wins; --candidates-root/--dry-run outside campaign and --candidate-dir/--smoke/--report in campaign are usage errors; --smoke with --report is a usage error; empty list entries are dropped and duplicate models removed; the summary and report print after every cell; candidate/dataset messages print verbatim; an unexpected exception prints `agent-harness: <message>` and exits 1.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/commands.ts (parsing, validation order with exit 3 then 2, defaults against the package dir, usage, dispatch of run and --report), src/grid.ts (cells, preflight, version, preconditions/progress/summary lines, resume, report per cell, exit 0/1) and the src/cli.ts entry; candidate dirs now resolve to absolute paths; check.py gets the harness env minus XDG. Verified by 12 new tests including end-to-end CLI runs with stub CLIs; flow evaluate-a-candidate added.
<!-- SECTION:FINAL_SUMMARY:END -->
