---
id: TASK-15
title: 'opencode trials write outside the workspace: set PWD for every agent CLI'
status: To Do
assignee: []
created_date: '2026-10-13 03:42'
labels: []
milestone: m-1
dependencies: []
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
- [ ] #1 Every child the harness spawns has PWD equal to its cwd (asserted with the stub kit for claude, opencode, codex, grader and check.py)
- [ ] #2 A stub opencode that writes into $PWD lands its file in the trial workspace, and the trial passes
- [ ] #3 SPEC.md Agent CLIs common rules state the PWD rule
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
