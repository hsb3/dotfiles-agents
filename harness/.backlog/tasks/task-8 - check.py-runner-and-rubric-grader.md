---
id: TASK-8
title: check.py runner and rubric grader
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:19'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - checks
  - grader
  - python3
  - claude-code-cli
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/checks.md
  - .groma/systems/harness/containers/agent-harness-cli/components/grader.md
  - src/checks.ts
  - src/grader.ts
  - test/checks.test.ts
  - test/grader.test.ts
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
- [x] #1 check.py runs as python3 <case dir>/check.py with cwd = workspace and a 120 s timeout; spawn error, timeout, non-JSON or non-array stdout give one check.py entry with check-error: <reason>
- [x] #2 The grader argv, environment (claude scrub, grader-home, grader-config, the betas variable) and verbatim prompt with digest, truncated result and compact assertions match the spec
- [x] #3 The workspace digest lists files recursively sorted by path as <path> (<size>B), capped at 80 lines with "... and <k> more", or (empty)
- [x] #4 Grades come from structured_output.grades of fixture A11; any other output gives every assertion passed:false with evidence grader-error
- [x] #5 Tests running the shipped check.py files skip when no python3 is on PATH
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/checks.ts: runChecks(checkPath, ws, env) -> Entry[]: python3 <check> in ws, 120 s, subprocess rules; parse stdout as a JSON array of {id, passed, evidence}; any failure -> one check.py entry with check-error: <reason>.
2. src/grader.ts: workspaceDigest(ws), graderPrompt(digest, result, assertions) verbatim, grade(): claude -p --bare argv with compact schema, claude scrub + grader-home/grader-config + betas var, reads structured_output.grades, otherwise every assertion grader-error.
3. Tests: test/checks.test.ts (real python3 with the shipped check.py files, skipped without python3; stub python3 for failure modes) and test/grader.test.ts (argv, env, prompt, digest cap, A11, error cases).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 66 pass, 0 fail. test/checks.test.ts runs both shipped check.py files with the real python3 (test.skipIf when python3 is absent; here they ran, 4 pass), plus stubbed argv/cwd and every check-error reason. test/grader.test.ts: exact argv with the compact schema, digest (sorted, sizes, (empty), 80-line cap with "... and 13 more"), verbatim prompt with 3000-char truncation, A11 grades with env checks (grader-home, grader-config, betas var, CLAUDE*/XDG scrubbed, API key passed), grader-error for missing CLI, non-JSON and missing structured_output. groma: matched 2; accepted checks, grader and their subprocess/python3/claude-code-cli relations; added grader -> claude and grader -> harnesses; lint clean.
Product calls: check.py runs with the trial child environment (per-run HOME); a check entry that is not {id: string, passed: boolean, evidence: string} fails the whole check.py as "entries must be {id, passed, evidence}"; the digest lists symlinks as files without following them; grades are taken as the grader returns them (no per-id reconciliation).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/checks.ts (runChecks: python3 check.py in the workspace, 120 s, check-error mapping) and src/grader.ts (workspace digest, verbatim prompt, claude --bare argv with schema, isolated grader env, structured_output.grades or grader-error). Verified by 9 tests, incl. the shipped check.py files under the real python3 and fixture A11.
<!-- SECTION:FINAL_SUMMARY:END -->
