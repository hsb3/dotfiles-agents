---
id: TASK-27
title: 'Harness: scratch-ledger/--dry-run mode + vision-grader assertion recording'
status: To Do
assignee: []
created_date: '2026-08-06'
labels:
  - harness
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/172'
priority: low
type: feature
ordinal: 2100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two residuals from the task-22 build (PR #241). (1) Proving candidate resolution or smoke-testing the harness appends rows to the tracked `harness/results.jsonl`, and auth-failure rows poison the resume key — a later real run skips those cells as "done". The task-22 build had to restore the ledger by hand twice. Add a scratch-ledger or `--dry-run` mode so evidence runs cannot mutate tracked results. (2) W3 findings §3.7: vision-dependent grader assertions are unverifiable after the fact — record enough (grader input digest or artifact copy alongside the run log) for an adversarial reviewer to re-check them post-hoc. Was in GH #172's report but never in task-22's Done-when; carried here so it isn't lost.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A documented mode (flag or env) under which no run can append to the tracked results.jsonl; `git diff --stat harness/results.jsonl` empty after an evidence run under it
- [ ] #2 Vision-dependent grader assertions leave a post-hoc-verifiable artifact next to the run log; one test asserts its presence and content shape
<!-- AC:END -->
