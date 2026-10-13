---
id: TASK-4
title: >-
  Evaluation loaders: load-eval-run, load-verdicts, load-curation,
  compare-verdicts
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - evaluations
priority: high
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every verdict links back to the run, prompt and response that produced it, so evaluation passes are loaded as eval runs with responses first, then verdict files into assessments and curation files into job_coverage and relationships; compare-verdicts measures agreement between two verdict sets offline. Builds the evaluations component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 load-eval-run writes eval_runs and eval_responses with the measurement envelope (manifest sha256, canonical resolved_response_sha256, availability and provenance) and with link_assessor stamps eval_run on that assessor assessments; refused extenders, NaN response_json and bad metrics are validation errors
- [ ] #2 load-verdicts expands fill rows, refuses mechanical-v1, unknown or retired extenders, foreign elements, duplicates within and across files, and enforces --extenders and --complete
- [ ] #3 load-curation writes only the rows the file lists, keyed as the spec states, and refuses duplicate keys and unknown eval runs
- [ ] #4 compare-verdicts prints sorted disagreements and `verdict agreement: a/t (p%)`, honours fill, and exits 1 with `no overlapping extenders`
- [ ] #5 Each loader supports --parse-only and --dry-run and a re-run plans no writes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
