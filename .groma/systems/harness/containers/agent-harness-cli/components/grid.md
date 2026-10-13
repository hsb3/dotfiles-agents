---
type: C4 Component
title: Grid
description: Runs the harness × model grid for one candidate, with resume
status: draft
groma:
  id: grid
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Loads the candidate and its cases, then for each (harness, model) cell runs preflight, reads the CLI version, prints the preconditions line and walks cases × configs × trials, skipping every resume key already in the ledger and printing a progress line per trial it runs; then the summary line and the candidate's report. Exits 0 when any cell passed preflight. The campaign runs each candidate through it.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [grid](grid.md) | [candidate](candidate.md) | Loads the candidate | function call |
| [grid](grid.md) | [cases](cases.md) | Loads the cases | function call |
| [grid](grid.md) | [harnesses](harnesses.md) | Preflights each cell | function call |
| [grid](grid.md) | [ledger](ledger.md) | Reads done resume keys | function call |
| [grid](grid.md) | [trial](trial.md) | Runs each trial | function call |
| [grid](grid.md) | [report](report.md) | Prints the report | function call |
