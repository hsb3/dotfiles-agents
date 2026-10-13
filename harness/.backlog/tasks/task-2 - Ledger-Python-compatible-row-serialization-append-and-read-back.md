---
id: TASK-2
title: 'Ledger: Python-compatible row serialization, append and read-back'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:11'
labels: []
milestone: m-0
dependencies: []
references:
  - ledger
  - results-ledger
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/ledger.md
  - src/ledger.ts
  - test/fixtures/spec-row.json
  - test/ledger.test.ts
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The ledger is a contract with the evals loader: rows must be byte-identical to Python json.dumps(row, sort_keys=True), appended one write per trial so an interrupted run resumes cleanly, and read back for resume keys and the report while silently skipping lines that are not valid rows (SPEC.md Ledger, resume key and logs; Persistence). Builds groma component ledger and its store results-ledger.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Serialization sorts keys by code point at every depth, uses ", " and ": " separators, escapes every non-ASCII character as lowercase \uXXXX UTF-16 code units, leaves / unescaped and prints numbers as JavaScript does; the spec example row round-trips byte for byte
- [x] #2 Appending creates the file and its parent directory on first use and writes each row plus newline in a single write
- [x] #3 Reading returns valid rows and skips lines that are not JSON objects with the row fields; a missing campaign reads as ""
- [x] #4 The resume key is campaign|harness|model|candidate|case|config|trial and the set of done keys covers passed, failed and skip rows
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/ledger.ts: Row type (29 fields), pythonJson(value) reproducing json.dumps(sort_keys=True): code-point key sort at every depth, ', ' and ': ' separators, non-ASCII as lowercase \uXXXX UTF-16 units, JS number printing.
2. appendRow(path,row): mkdir parent, single appendFileSync of line+newline.
3. readRows(path): parse each line, keep objects with the key fields (string harness/model/candidate/case/config, integer trial, optional string campaign defaulting to ''), skip the rest; resumeKey(row) and doneKeys(rows, candidate).
4. test/ledger.test.ts: spec example row round-trip byte for byte, unicode and nested sorting, append creating dirs, read skipping junk lines, resume keys.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 10 pass, 0 fail. test/ledger.test.ts: the spec example row (test/fixtures/spec-row.json, copied verbatim from SPEC.md) round-trips byte for byte; code-point key order incl. astral vs U+FB01; unicode escapes; a cross-check against the real python3 json.dumps (skips without python3) which caught that Python escapes DEL (0x7f) too, now matched; append creates dirs; junk lines skipped; resume keys. `groma scan` matched 1; accepted ledger and ledger -> results-ledger; lint clean.
Product call: a row is valid for resume/report when it is a JSON object with string harness/model/candidate/case/config and an integer trial; campaign may be absent or null (reads as "").
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/ledger.ts: the 29-field Row type, pythonJson (byte-compatible with Python json.dumps sort_keys=True, verified against real python3), appendRow (single write, creates dirs), readRows (skips invalid lines), resumeKey and doneKeys. Verified by 6 ledger tests in the gate.
<!-- SECTION:FINAL_SUMMARY:END -->
