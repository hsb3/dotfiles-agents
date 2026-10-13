---
id: TASK-7
title: 'evals report: coverage matrix and analysis'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - reports
priority: medium
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The owner reads coverage and cross-cutting answers as Markdown snapshots for diff review; they render deterministically from the database or JSON dumps. Builds the reports component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 coverage-matrix.md and analysis.md render exactly the documented sections, ordering, escaping and scope paragraph from --fixtures dumps
- [ ] #2 Retired extenders and assessments and relationships referencing them are excluded and counted once each
- [ ] #3 The same data renders byte-identical files; a missing hsb3-jobs-to-be-done framework exits 1; the wrote lines report the stated counts
- [ ] #4 Reading from a live database gives the same output as from dumps of it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
