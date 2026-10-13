---
id: TASK-10
title: 'Toolbox UI: evaluations and performance'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-9
references:
  - evaluations-view
  - performance-view
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Readers review current assessments and coverage, and compare one baseline with one with-configuration run on recorded evidence without overclaiming. This slice builds the Evaluations and Performance areas: runs list, selection, comparison and charts, run detail with token-gated evidence, and campaigns. Builds the evaluations-view and performance-view components.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Evaluations lists assessments (optionally per extender) and job coverage with the documented texts and links
- [ ] #2 The runs list supports search, configuration filter, client-side duration/cost sort with unavailable last, 25 or 50 per page, and a selection tray of at most two
- [ ] #3 Comparison eligibility returns the documented first failing reason; an eligible pair shows the n=1 caveat, the differences table, the sources table and a grouped bar chart per available metric
- [ ] #4 Measurements show only when the v1 envelope marks them available and valid, formatted as specified; run detail, evidence via file token, events, tool calls and campaign detail follow the spec
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
