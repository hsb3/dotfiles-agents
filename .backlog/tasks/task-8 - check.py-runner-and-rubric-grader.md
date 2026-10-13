---
id: TASK-8
title: check.py runner and rubric grader
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - checks
  - grader
priority: high
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A trial is graded by the case's deterministic check.py and, for cases with assertions, by an LLM rubric grader that is always claude --bare with a JSON schema (SPEC.md check.py and Grader). Any failure of either must turn into failed entries rather than an error. Builds groma components checks and grader.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 check.py runs as python3 <case dir>/check.py with cwd = workspace and a 120 s timeout; spawn error, timeout, non-JSON or non-array stdout give one check.py entry with check-error: <reason>
- [ ] #2 The grader argv, environment (claude scrub, grader-home, grader-config, the betas variable) and verbatim prompt with digest, truncated result and compact assertions match the spec
- [ ] #3 The workspace digest lists files recursively sorted by path as <path> (<size>B), capped at 80 lines with "... and <k> more", or (empty)
- [ ] #4 Grades come from structured_output.grades of fixture A11; any other output gives every assertion passed:false with evidence grader-error
- [ ] #5 Tests running the shipped check.py files skip when no python3 is on PATH
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
