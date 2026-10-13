---
id: TASK-4
title: Case dataset loading and validation
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - cases
  - shipped-cases
  - cases-directory
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
- [ ] #1 Cases load from <cases-dir>/<candidate>/<case-id>/case.json with optional fixture/ and check.py, ignoring subdirectories without case.json, sorted by id
- [ ] #2 --case selects one id; none found gives "no case.json found under <dir>" with " for --case <id>" appended
- [ ] #3 Missing dataset dir, invalid JSON, missing or empty prompt and assertions lacking id or text give the spec error messages
- [ ] #4 The shipped cases cases/_template/rename-this-case and cases/smoke-echo/create-file load without error
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
