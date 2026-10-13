---
type: C4 Component
title: Report
description: Aggregates a candidate's ledger rows into the report
status: draft
groma:
  id: report
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Groups rows with a pass signal into (campaign, harness, model, case, config) cells and prints the aligned table (n, pass rate, pass@n, pass^n, cost and duration mean±stdev), one with − baseline delta line per matched pair and the skip rows. Serves `--report` and ends every grid and campaign run.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [report](report.md) | [ledger](ledger.md) | Reads the candidate's rows | function call |
