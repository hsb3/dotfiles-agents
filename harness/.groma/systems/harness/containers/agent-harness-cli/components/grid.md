---
type: C4 Component
title: Grid
description: Runs the harness × model grid for one candidate, with resume
status: stable
groma:
  id: grid
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/grid.ts
---

Loads the candidate and its cases (their errors exit 2), then for each (harness, model) cell, harness-major in the order given and with each harness's default model when `--model` is omitted, runs preflight (a failed cell prints why to stderr and is skipped), reads the CLI version, prints the preconditions line and walks cases × configs × trials, skipping every resume key already in the ledger and printing a `✓`/`✗`/`∅` progress line per trial it runs; then the summary line and the candidate's report. Exits 0 when any cell passed preflight, else 1. The campaign runs each candidate through it.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/candidate.ts](../../../../../../src/candidate.ts) | Loads the candidate | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/cases.ts](../../../../../../src/cases.ts) | Loads the cases | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Preflights each cell | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Reads done resume keys | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Runs each trial | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/report.ts](../../../../../../src/report.ts) | Prints the report | function call |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Writes command output | Io callbacks |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/candidate.ts](../../../../../../src/candidate.ts) | Calls imported function: loadCandidate | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/cases.ts](../../../../../../src/cases.ts) | Calls imported function: loadCases | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Invokes supplied callbacks: err, out | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: adapterFor, authEnvPresent, cliVersion, preflight | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Calls imported functions: doneKeys, resumeKey | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/report.ts](../../../../../../src/report.ts) | Calls imported function: report | typescript |
| [src/grid.ts](../../../../../../src/grid.ts) | [src/trial.ts](../../../../../../src/trial.ts) | Calls imported function: runTrial | typescript |
