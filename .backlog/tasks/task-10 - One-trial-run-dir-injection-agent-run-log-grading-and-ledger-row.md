---
id: TASK-10
title: 'One trial: run dir, injection, agent run, log, grading and ledger row'
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-2
  - TASK-4
  - TASK-6
  - TASK-7
  - TASK-8
references:
  - trial
  - run-dirs
  - trial-logs
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The trial is the unit of evidence: it must isolate the agent in a run dir with per-run homes, inject the candidate only for with, write the per-trial log, fold, grade, apply the pass rule and append exactly the 29-field row (SPEC.md One trial, Pass rule, error field, Ledger row variants, Per-trial log). Builds groma component trial and the run-dirs and trial-logs stores.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The run dir is <tmp>/harness-<harness>-<candidate>-<case>-<config>-<trial>-<random>/ honouring TMPDIR, with ws/ a copy of the fixture or empty
- [ ] #2 Normal, skip and injection-failure rows carry exactly the 29 fields with the spec values, including preconditions, self_installs, workspace and log_path relative to the ledger dir
- [ ] #3 The pass rule and the error field rules (timeout, missing executable, stderr tail, fold error, exit code) hold
- [ ] #4 The log is <runs-dir>/<harness>-<candidate>-<case>-<config>-<trial>-<YYYYMMDD-HHMMSS>-<32 hex>.log with the # preconditions header then raw stdout
- [ ] #5 The run dir is deleted after a pass (unless --keep-workspaces) and after a skip row, and kept after a failure
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
