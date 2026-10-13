---
type: C4 System
title: Evals loader
description: Downstream consumer that ingests the ledger
status: stable
groma:
  id: evals-loader
  technology: separate tool
---

Outside this system. Reads the ledger rows (the 29-field row schema and the 7-field resume key) and the per-trial logs they link through `log_path`. The harness never reads or writes the evals unit or its database.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [evals-loader](evals-loader.md) | [ledger](../systems/harness/containers/results-ledger/container.md) | Reads trial rows | JSONL, 29-field row and 7-field key |
| [evals-loader](evals-loader.md) | [trial-logs](../systems/harness/containers/trial-logs/container.md) | Reads per-trial logs | files linked by log_path |
