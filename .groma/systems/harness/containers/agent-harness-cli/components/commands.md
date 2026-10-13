---
type: C4 Component
title: Commands
description: Parses and validates the command line and dispatches it
status: stable
groma:
  id: commands
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/commands.ts
---

Turns argv into one of the four commands (a candidate run, `--smoke`, `--report`, `campaign`) plus `--help`, and returns the exit code. Validation follows the spec's order before any agent CLI runs: unknown harness names exit 3 first; then usage errors (no candidate name, an unknown or misplaced flag, a missing value, `--trials` or `--timeout` not an integer of at least 1), a config other than `with` or `baseline` and a missing `--candidate-dir` exit 2, with candidate and dataset errors following in the grid. Applies the run-flag defaults, which resolve against the package directory rather than the current directory, resolves relative paths against the cwd and keeps the results path as given for the summary line. Prints usage to stdout for `--help` and to stderr when there are no arguments. It also defines the output channel the other commands write through.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Validates harness names | function call |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Runs a candidate's grid | function call |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/report.ts](../../../../../../src/report.ts) | Prints a candidate report | function call |

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [commands](commands.md) | [smoke](smoke.md) | Runs loadability checks | function call |
| [commands](commands.md) | [campaign](campaign.md) | Runs the weekly campaign | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/grid.ts](../../../../../../src/grid.ts) | Calls imported function: runCandidate | typescript |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported function: parseHarnessList | typescript |
| [src/commands.ts](../../../../../../src/commands.ts) | [src/report.ts](../../../../../../src/report.ts) | Calls imported function: report | typescript |
