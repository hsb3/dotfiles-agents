---
id: TASK-6
title: 'evals load-runs: harness ledger and logs'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - runs
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Harness telemetry (runs, artifacts, run events, tool calls) is what the Performance area compares; the ledger has three generations of rows, logs are linked by path or name prefix, and the measurement v1 envelope with record_sha256 says what each value rests on. A logless re-run must never erase stored evidence. Builds the runs component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Run bodies and measurement match Appendix C.2 for ledger lines 24 and 188, and record_sha256 matches C.1 for lines 24, 58 and 188 taken from the ledger lexemes
- [ ] #2 Log linkage follows explicit log_path then earliest unclaimed prefix match, with the exact warnings, and stores log_path as the spec states
- [ ] #3 Validation names the row key and field before any write; skip rows, execution validity rules and the era na rollup fill behave as specified; `--campaign` and `--candidate` scope reads and writes
- [ ] #4 Artifacts are deduplicated by sha256 across the load, owned by the first run, never updated, uploaded as protected blobs named by sha prefix
- [ ] #5 A re-run plans no writes; a logless re-run keeps stored session_id, era, rollup values and observed log hash; `--parse-only` prints exactly the documented shape
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
