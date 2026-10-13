---
id: TASK-15
title: 'opencode trials write outside the workspace: set PWD for every agent CLI'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:42'
updated_date: '2026-10-13 03:45'
labels: []
milestone: m-1
dependencies: []
references:
  - subprocess
  - opencode
  - trial
  - evaluate-a-candidate
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/subprocess.md
  - SPEC.md
  - src/subprocess.ts
  - test/helpers/stubs.ts
  - test/subprocess.test.ts
  - test/trial.test.ts
priority: high
type: bug
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the coordinator's live check (2026-10-12, opencode 2.0.25): in a smoke-echo trial, opencode wrote HELLO.txt into the directory the harness was invoked from, not the trial workspace, so both configs failed their checks. The child process had cwd = <run>/ws, but its PWD environment variable was still the parent's. opencode resolves its project directory from PWD. Reproduced: the same opencode run with PWD=<ws> writes into the workspace.

Requirement (amends SPEC.md, "Agent CLIs" common rules): every agent CLI child, the grader, check.py and the codex plugin-install commands get PWD set to their cwd.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every child the harness spawns has PWD equal to its cwd (asserted with the stub kit for claude, opencode, codex, grader and check.py)
- [x] #2 A stub opencode that writes into $PWD lands its file in the trial workspace, and the trial passes
- [x] #3 SPEC.md Agent CLIs common rules state the PWD rule
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/subprocess.ts: runProcess sets PWD to the cwd in every child env (agent CLIs, grader, check.py, codex plugin installs and --version all go through it).
2. Stub kit: $VAR expansion in writeFiles keys and an ifExists match condition, so a stub opencode can write into $PWD and a stub python3 can answer by what the workspace holds.
3. Tests: PWD equals cwd for claude, opencode, codex, grader and check.py children; an opencode trial whose parent PWD is elsewhere lands HELLO.txt in ws/ and passes.
4. SPEC.md Agent CLIs common rules: the PWD rule.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 113 pass, 0 fail. New tests: subprocess PWD equals the cwd even when the parent PWD points elsewhere; a trial set with the parent PWD elsewhere records PWD == cwd for the claude agent, the three grader runs, the three check.py runs, opencode run, codex exec and both codex plugin-install commands; a stub opencode writing into $PWD lands HELLO.txt in the kept ws/ (not the invocation dir) and the trial passes via a stub python3 that answers by file presence. Mutation check: without the PWD line those 3 tests fail (110 pass, 3 fail). SPEC.md Agent CLIs common rules now state the PWD rule. groma: no planned component (draft v1-1 tags subprocess); scan created 0, lint clean; subprocess overview updated.
Product calls: the rule is applied once in runProcess, so it also covers `<exe> --version`; PWD is the absolute (resolved) cwd string, the run dir already being a real path. Stub kit gained $VAR expansion in writeFiles keys, an ifExists match condition, a lacks condition and dumpEnvTo (used by TASK-16).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
runProcess now sets PWD to the child cwd for every spawned process (agent CLIs, grader, check.py, codex plugin installs, --version), fixing opencode writing outside the workspace. SPEC.md amended; verified by 3 new tests (mutation-checked) using an extended stub kit.
<!-- SECTION:FINAL_SUMMARY:END -->
