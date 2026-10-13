---
id: TASK-2
title: 'Ledger: Python-compatible row serialization, append and read-back'
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - ledger
  - results-ledger
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
- [ ] #1 Serialization sorts keys by code point at every depth, uses ", " and ": " separators, escapes every non-ASCII character as lowercase \uXXXX UTF-16 code units, leaves / unescaped and prints numbers as JavaScript does; the spec example row round-trips byte for byte
- [ ] #2 Appending creates the file and its parent directory on first use and writes each row plus newline in a single write
- [ ] #3 Reading returns valid rows and skips lines that are not JSON objects with the row fields; a missing campaign reads as ""
- [ ] #4 The resume key is campaign|harness|model|candidate|case|config|trial and the set of done keys covers passed, failed and skip rows
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
