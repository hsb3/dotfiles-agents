---
id: TASK-10
title: 'One trial: run dir, injection, agent run, log, grading and ledger row'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:23'
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
  - claude-code-cli
  - opencode-cli
  - codex-cli
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/trial.md
  - src/trial.ts
  - test/trial.test.ts
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
- [x] #1 The run dir is <tmp>/harness-<harness>-<candidate>-<case>-<config>-<trial>-<random>/ honouring TMPDIR, with ws/ a copy of the fixture or empty
- [x] #2 Normal, skip and injection-failure rows carry exactly the 29 fields with the spec values, including preconditions, self_installs, workspace and log_path relative to the ledger dir
- [x] #3 The pass rule and the error field rules (timeout, missing executable, stderr tail, fold error, exit code) hold
- [x] #4 The log is <runs-dir>/<harness>-<candidate>-<case>-<config>-<trial>-<YYYYMMDD-HHMMSS>-<32 hex>.log with the # preconditions header then raw stdout
- [x] #5 The run dir is deleted after a pass (unless --keep-workspaces) and after a skip row, and kept after a failure
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/trial.ts: local-time helpers (ts, log stamp, random hex); makeRunDir (mkdtemp under os.tmpdir() honouring TMPDIR, ws/ = fixture copy or empty); runAgent shared with smoke (childEnv, injection for with, CLI run through runProcess, fold, wall-clock duration where the adapter says so); errorField rules; selfInstalls; preconditions object; log writing with the # preconditions header; relative log_path.
2. runTrial(spec): skip row when the harness cannot host the kind (both configs, run dir deleted), injection-failure row (run dir kept), normal row with checks, grades, pass rule, run dir kept on failure or --keep-workspaces; appends the row and returns it.
3. test/trial.test.ts with stub CLIs: normal claude skill trial (A2) with a stub python3 check, A3 plugin error with vs baseline, A1 error field, timeout, missing executable, skip row, codex injection failure row, grader run, exact 29 keys, log name/header, log_path, run-dir lifecycle.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 80 pass, 0 fail. test/trial.test.ts (stub claude/opencode/codex/python3, TMPDIR pointed into the sandbox): passing skill trial with exact 29 keys, values from A2, preconditions, log name/header/raw stdout, relative log_path, ledger content, run dir deleted, cwd/HOME/scrub/argv checks; baseline without injection and fixture copy with --keep-workspaces; A3 plugin error fails with but not baseline and keeps the run dir; error field (fold error with empty stderr, 2000-char stderr tail, exit <code>); timeout (-1, partial log); missing executable (-1, empty log); skip rows for both configs with no CLI run and no run dir left; codex injection-failure row; claude grader under codex with wall-clock duration; self_installs rules. groma: matched 1; accepted trial and its 13 planned relations; lint clean.
Product calls: a harness that cannot host the kind writes a skip row for baseline too (the cell cannot evaluate the candidate, so no API spend on an unpaired baseline); a missing executable still counts as an agent run (log written, check.py and grader run, grader_model set); the stderr tail is taken after trimming trailing whitespace; the run dir path is the real path (macOS /tmp -> /private/tmp) so workspace equals the agent cwd; the log timestamp is the trial start; check.py gets the trial child env.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/trial.ts: run dir creation, shared runAgent (env, injection, CLI run, fold), error field, self_installs, preconditions, per-trial log, relative log_path, and runTrial producing normal, skip and injection-failure rows with the pass rule and run-dir lifecycle. Verified by 10 trial tests with stub CLIs.
<!-- SECTION:FINAL_SUMMARY:END -->
