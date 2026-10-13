---
id: TASK-7
title: 'evals report: coverage matrix and analysis'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:53'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - reports
  - render-the-reports
modified_files:
  - .groma/flows/render-the-reports.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/reports.md
  - .groma/systems/evals/containers/evals-cli/components/runs.md
  - src/commands.ts
  - src/reports.ts
  - src/runs.ts
  - src/store.ts
  - test/reports.test.ts
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
- [x] #1 coverage-matrix.md and analysis.md render exactly the documented sections, ordering, escaping and scope paragraph from --fixtures dumps
- [x] #2 Retired extenders and assessments and relationships referencing them are excluded and counted once each
- [x] #3 The same data renders byte-identical files; a missing hsb3-jobs-to-be-done framework exits 1; the wrote lines report the stated counts
- [x] #4 Reading from a live database gives the same output as from dumps of it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/reports.ts: load the eight collections from the database or --fixtures dumps; model live extenders, suppressed assessments and relationships, coverage rows.
2. Render coverage-matrix.md (header, provenance, scope paragraph, matrix, gaps, relationship counts, duplicative/conflicting/directed sections) and analysis.md (profiles, relationship listing with status, assessor comparison, provenance index) with cell escaping and code-point sorting.
3. Wire the report command; print the wrote lines.
4. Tests: exact output from a dump, determinism, missing jobs framework, database vs dumps equivalence. Gate, groma accept reports and relations, flow, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate passes (84 tests). test/reports.test.ts: from a dump with a retired extender, a missing-element row, every relationship kind and pipes/newlines in text, `evals report --fixtures` writes coverage-matrix.md and analysis.md equal line for line to the expected text (scope paragraph with 1 retired, 1 suppressed assessment, 1 suppressed relationship; matrix with bold status and `?`, gaps, kind counts, duplicative/conflicting/directed sections; profiles, relationship listing with resolved/open, assessor comparison with `—` and 0/0/0 for a not-applicable-only assessor, provenance index) and prints both wrote lines with the stated counts into a nested --out it creates; two renders are byte-identical; a dump without hsb3-jobs-to-be-done exits 1 with `evals report: framework hsb3-jobs-to-be-done is missing`; records inserted into PocketBase render identically from the database and from API dumps of them. groma: accepted reports, commands -> reports, reports -> store, reports -> report-directory, authored src/reports.ts -> src/canonical.ts; shared textOf from store after lint flagged a duplicate helper; flow render-the-reports; scan created 0, lint clean.
Product calls: a job without a job_coverage row shows `**?**` as status and `?` as disposition (also `?` in a gap line whose row has no disposition); an empty gaps or directed section shows `_None._`; list items (gaps, pairs) keep `|` and turn newlines into spaces, while table cells also escape `|`; jobs order by sort_order then slug; a missing fixture file is an error naming it; the assessor comparison counts every live assessment of any framework; the relationship degree counts each live relationship touching the extender once.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built `evals report` (src/reports.ts): reads the eight collections from PocketBase or --fixtures dumps and renders coverage-matrix.md and analysis.md deterministically with the documented sections, exclusions, escaping and counts. Verified by exact-output tests from a dump, determinism and missing-framework tests, and a database-vs-dump equivalence test against PocketBase.
<!-- SECTION:FINAL_SUMMARY:END -->
