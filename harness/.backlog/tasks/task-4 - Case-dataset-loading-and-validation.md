---
id: TASK-4
title: Case dataset loading and validation
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:12'
labels: []
milestone: m-0
dependencies: []
references:
  - cases
  - shipped-cases
  - cases-directory
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/cases.md
  - src/cases.ts
  - test/cases.test.ts
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Trials walk a candidate's cases sorted by id; a broken dataset must be rejected with exit 2 before any agent CLI runs (SPEC.md Case dataset). The shipped cases (Appendix B) are the default --cases-dir. Builds groma component cases.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Cases load from <cases-dir>/<candidate>/<case-id>/case.json with optional fixture/ and check.py, ignoring subdirectories without case.json, sorted by id
- [x] #2 --case selects one id; none found gives "no case.json found under <dir>" with " for --case <id>" appended
- [x] #3 Missing dataset dir, invalid JSON, missing or empty prompt and assertions lacking id or text give the spec error messages
- [x] #4 The shipped cases cases/_template/rename-this-case and cases/smoke-echo/create-file load without error
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/cases.ts: loadCases(casesDir, candidate, caseId?) -> Case[] {id, dir, prompt, assertions, fixture|null, check|null} sorted by id; throws Error with the spec messages (caller maps to exit 2).
2. Errors: missing dataset dir -> no eval cases at <dir> — copy cases/_template to author some; invalid JSON; missing/empty prompt; assertion lacking string id or text; no case.json found under <dir>[ for --case <id>].
3. test/cases.test.ts: layout, sorting, ignoring dirs without case.json, --case, each error, and the shipped cases loading.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 19 pass, 0 fail; test/cases.test.ts covers layout and sorting, ignored dirs, --case, every error message, and loading both shipped cases. groma: matched 1, accepted cases plus cases -> cases-directory and cases -> shipped-cases; lint clean.
Product calls: "no eval cases at <dir>" is for a missing <cases-dir>/<candidate> directory, "no case.json found under <dir>" for an existing one with no (matching) case; <dir> is <cases-dir>/<candidate> and <file> the full case.json path; a case.json that is not an object, or whose prompt is not a non-empty string, is "missing required field prompt"; a non-array assertions value (null counts as absent) is the assertion error.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/cases.ts: loadCases reads and validates a candidate case dataset (prompt, assertions, fixture/, check.py), sorted by id with --case selection, failing with the spec messages. Verified by 3 case tests (incl. the shipped cases) in the gate.
<!-- SECTION:FINAL_SUMMARY:END -->
