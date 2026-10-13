---
id: TASK-1
title: Subprocess runner and stub test kit
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - subprocess
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every child process the harness starts (agent CLIs, grader, check.py, --version, codex plugin installs) must run with a list-form argv, stdin from /dev/null, its own process group and a timeout that SIGKILLs the whole group while keeping the stdout captured so far (SPEC.md Non-functional). The test suite never runs a real CLI, so it also needs a reusable stub kit: stub `claude`/`opencode`/`codex`/`python3` executables first on PATH that record argv, cwd and env and replay an Appendix A stream with a given exit code. Builds groma component subprocess. Also brings package.json in line with the Stack section (exact devDependencies) and ships the empty results.jsonl with runs/ and campaign-logs/ git-ignored.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A child runs without a shell, with stdin from /dev/null, in its own process group, and its stdout, stderr and exit code are returned
- [ ] #2 On timeout the whole process group is SIGKILLed, the stdout captured so far is kept and the result says it timed out; a test proves a sleeping descendant of a hanging stub is gone afterwards
- [ ] #3 A missing executable is reported distinctly from a non-zero exit
- [ ] #4 Test helpers provide stub executables that record argv, cwd and environment and print a given fixture stream with a given exit code and stderr
- [ ] #5 package.json lists typescript 7.0.2 and @types/bun 1.4.2 as exact devDependencies; results.jsonl ships empty; runs/ and campaign-logs/ are git-ignored
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
