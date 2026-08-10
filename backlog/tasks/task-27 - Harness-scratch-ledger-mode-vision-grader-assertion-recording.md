---
id: TASK-27
title: 'Harness: scratch-ledger/--dry-run mode + vision-grader assertion recording'
status: To Do
assignee: []
created_date: '2026-08-06'
updated_date: '2026-08-10 02:25'
labels:
  - harness
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/172'
priority: low
type: feature
ordinal: 2100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two residuals from the task-22 build (PR #241).

1. Evidence runs and smoke tests append rows to the tracked `harness/results.jsonl`; auth-failure rows poison the resume key, so a later real run skips those cells as done. Had to be restored by hand twice during task-22. Needs a scratch-ledger or `--dry-run` mode so evidence runs can't mutate tracked results.

2. Per W3 findings §3.7, vision-dependent grader assertions are unverifiable after the fact. Record enough (grader input digest or artifact copy alongside the run log) for an adversarial reviewer to re-check them post-hoc. Was in the linked issue's report but missed task-22's Done-when.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented mode (flag or env) under which no run appends to the tracked results.jsonl — `git diff --stat harness/results.jsonl` is empty after an evidence run under it
- [ ] #2 Vision-dependent grader assertions leave a post-hoc-verifiable artifact next to the run log; one test asserts its presence and content shape
<!-- AC:END -->
