---
type: C4 Component
title: Report
description: Aggregates a candidate's ledger rows into the report
status: stable
groma:
  id: report
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/report.ts
---

Groups rows with a pass signal into (campaign, harness, model, case, config) cells and prints the aligned table (n, pass rate, pass@n, pass^n, cost and duration mean±stdev), one with − baseline delta line per matched pair and the skip rows. Serves `--report` and ends every grid and campaign run.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/report.ts](../../../../../../src/report.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Reads the candidate's rows | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/report.ts](../../../../../../src/report.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Calls imported function: readRows | typescript |
