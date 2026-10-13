---
type: C4 Component
title: Commands
description: Parses and validates the command line and dispatches it
status: draft
groma:
  id: commands
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Turns argv into one of the four commands (run, `--smoke`, `--report`, `campaign`) plus `--help`. Applies the run-flag defaults, which resolve against the package directory rather than the current directory, and validates in the spec's order: unknown harness names exit 3 first, then usage errors, bad configs and a missing `--candidate-dir` exit 2. Prints usage to stdout for `--help` and to stderr when there are no arguments.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [commands](commands.md) | [harnesses](harnesses.md) | Validates harness names | function call |
| [commands](commands.md) | [grid](grid.md) | Runs a candidate's grid | function call |
| [commands](commands.md) | [smoke](smoke.md) | Runs loadability checks | function call |
| [commands](commands.md) | [report](report.md) | Prints a candidate report | function call |
| [commands](commands.md) | [campaign](campaign.md) | Runs the weekly campaign | function call |
