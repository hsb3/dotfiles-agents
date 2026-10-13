---
id: TASK-9
title: Report aggregation and formatting
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - report
priority: high
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The report is how the owner reads the with − baseline delta; it ends every grid and campaign run and serves --report (SPEC.md Report). Builds groma component report.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Cells group rows with a boolean passed by (campaign, harness, model, case, config), sorted as strings with null as ""; n, pass, p@n, p^n, cost and ms follow the spec, with sample stdev 0 for one value and - when no numbers
- [ ] #2 The table is left-aligned, two-space joined, trailing spaces trimmed, with a dash line as long as the header; the spec example renders exactly
- [ ] #3 Delta lines, the skip section, "no result rows for <candidate>" and the no-pass-signal form match the spec
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
