---
id: TASK-6
title: 'evals load-runs: harness ledger and logs'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:50'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - runs
  - load-a-harness-campaign
modified_files:
  - .groma/flows/load-a-harness-campaign.md
  - .groma/systems/evals/containers/evals-cli/components/commands.md
  - .groma/systems/evals/containers/evals-cli/components/evaluations.md
  - .groma/systems/evals/containers/evals-cli/components/runs.md
  - .groma/systems/evals/containers/evals-cli/components/store.md
  - src/commands.ts
  - src/evaluations.ts
  - src/runs.ts
  - src/store.ts
  - test/runs.test.ts
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
- [x] #1 Run bodies and measurement match Appendix C.2 for ledger lines 24 and 188, and record_sha256 matches C.1 for lines 24, 58 and 188 taken from the ledger lexemes
- [x] #2 Log linkage follows explicit log_path then earliest unclaimed prefix match, with the exact warnings, and stores log_path as the spec states
- [x] #3 Validation names the row key and field before any write; skip rows, execution validity rules and the era na rollup fill behave as specified; `--campaign` and `--candidate` scope reads and writes
- [x] #4 Artifacts are deduplicated by sha256 across the load, owned by the first run, never updated, uploaded as protected blobs named by sha prefix
- [x] #5 A re-run plans no writes; a logless re-run keeps stored session_id, era, rollup values and observed log hash; `--parse-only` prints exactly the documented shape
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/runs.ts: ledger reading with lexeme-preserving parse and record_sha256, key replacement, bad-line warnings, validation naming row key and field, scope by campaign/candidate.
2. Log linkage (explicit log_path claims, then earliest unclaimed prefix match with the exact warnings) and log_path storage.
3. Run row builder with measurement v1 (availability, provenance, execution rules, source identity), era/session/rollup fill, null dropping, and the logless re-run rule; exported for the fixture.
4. Artifacts deduplicated by sha across the load with protected blobs, run_events and tool_calls from parsed logs; diff skipping unavailable measurement fields; parse-only shape; linkage warnings before the plan.
5. Tests: C.1/C.2 vectors through the builder, linkage, validation, parse-only output, end-to-end load with claude/opencode/codex logs against PocketBase, idempotence, logless re-run. Gate, groma accept runs and relations, flow, lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: gate `bunx tsc --noEmit && bun run build:ui && bun test` passes (81 tests). test/runs.test.ts: buildRun reproduces the C.2 measurement of ledger lines 24 and 188 exactly and the exact 28-field body of line 188; record_sha256 of line 58 from lexemes (all C.1 lines are also covered in test/canonical.test.ts); the nine execution rules in order and the preconditions validity rule; the logless rule keeps stored session_id, era, rollup values with log-rollup availability and the observed log sha. readLedger: later key replaces earlier, bad lines warn by line number. linkLogs: explicit relative and legacy log_path claims first, earliest unclaimed prefix match stored as harness/runs/<file>, exact no-match and ambiguous warnings. CLI: --parse-only prints the documented block exactly (counts, log reference, observed bytes, era split, warnings), `--campaign nope` prints `no ledger rows in scope; nothing to do` exit 0, `--campaign ""` selects the legacy row; validation names `<row key>: <field> must be ...` for each bad field; an unreadable ledger exits 1. Against PocketBase 0.40.5 with claude (C.3 log), opencode (C.3 log, rollup fill), codex (spec log via legacy log_path fallback), a skip row and line 24: dry run prints linkage warnings then the plan and writes nothing; the write stores era/session/provenance/model_usage, observed log sha, the opencode rollup fill with log-rollup provenance, codex usage sums, skipped/absent for the skip row, line 24 measurement exactly, two artifacts owned by the claude run with protected blobs named <sha12>.png/.txt and readable with a file token, events with artifact links and ts, tool calls (no_result, coerced opencode output); a re-run plans 0 create/0 update everywhere; with the runs directory moved away nothing is updated or erased; a --campaign/--candidate scoped load updates only in-scope runs and leaves the other run `updated` unchanged. Manual timing: 216 runs with 40-event logs (8856 events, 8640 tool calls) load in 2.3 s, re-run 0.75 s. groma: accepted runs with commands -> runs, runs -> logs, runs -> store, runs -> agent-harness-output; authored src/runs.ts -> src/canonical.ts, src/evaluations.ts -> src/canonical.ts and the store -> runs callback; added flow load-a-harness-campaign; moved the shared chunked filter read into store.ts (fetchWhereIn) and one childBody builder after lint flagged duplicates; scan created 0, lint clean.
Product calls: bad ledger lines warn as `ledger line <n> skipped: not a JSON object` and print as `warnings (<n>):` ahead of the linkage warnings (inside the parse-only warnings list); a replaced row keeps the first row position for artifact ownership order; linkage is computed over the whole ledger and only in-scope warnings print; a skip row without log_path still gets the no-match warning (the spec exempts none); harness, config, candidate, case and trial are validated too (they are required or select columns); measurement.execution.preconditions is the ledger value only when it is an object, plugin_errors the ledger value or null when absent.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Built `evals load-runs` (src/runs.ts): ledger reading with lexeme-exact record_sha256, validation, scope, log linkage with the specified warnings, the run-row builder with measurement v1 and the logless re-run rule (exported for the fixture), content-addressed artifacts with protected blobs, run_events and tool_calls, parse-only and dry-run output. Verified with the C.1/C.2 vectors and CLI tests against PocketBase covering claude, opencode and codex logs, idempotence, logless re-runs and scoping.
<!-- SECTION:FINAL_SUMMARY:END -->
