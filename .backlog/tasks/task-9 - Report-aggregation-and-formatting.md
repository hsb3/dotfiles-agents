---
id: TASK-9
title: Report aggregation and formatting
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:20'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - report
  - ledger
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/report.md
  - src/report.ts
  - test/report.test.ts
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
- [x] #1 Cells group rows with a boolean passed by (campaign, harness, model, case, config), sorted as strings with null as ""; n, pass, p@n, p^n, cost and ms follow the spec, with sample stdev 0 for one value and - when no numbers
- [x] #2 The table is left-aligned, two-space joined, trailing spaces trimmed, with a dash line as long as the header; the spec example renders exactly
- [x] #3 Delta lines, the skip section, "no result rows for <candidate>" and the no-pass-signal form match the spec
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/report.ts: formatReport(candidate, rows) building cells over rows with boolean passed, keyed and sorted by (campaign, harness, model, case, config); n, pass, p@n, p^n, cost and ms mean±sample stdev; aligned table with dash line; delta lines for with cells with a baseline match; skip section for rows whose passed is not boolean; the two edge forms. report(candidate, resultsPath) reads the candidate's ledger rows.
2. test/report.test.ts: reproduce the spec example exactly from constructed rows, edge cases, empty campaign forms, negative delta.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 70 pass, 0 fail. test/report.test.ts reproduces the SPEC.md report example byte for byte from constructed rows (cells out of order in input, one skip row), the empty-campaign forms (-, delta scope without campaign, skip line without [campaign]), a negative delta, both edge forms, and reading only the candidate rows from a ledger with junk lines. groma: matched 1; accepted report and report -> ledger; lint clean.
Product calls: skip rows are the candidate rows whose passed is not a boolean; the edge-case reports have no leading empty line; strings sort by UTF-16 code unit; a negative delta prints its own minus sign (a value rounding to -0.00 prints as -0.00); ms uses Math.round (half up).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/report.ts: formatReport (cells, aligned table, deltas, skip section, edge forms) and report (reads the candidate rows from the ledger). Verified by 4 tests including the exact spec example.
<!-- SECTION:FINAL_SUMMARY:END -->
