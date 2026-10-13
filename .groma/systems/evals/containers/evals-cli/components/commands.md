---
type: C4 Component
title: Commands
description: Parses subcommands and flags and dispatches them
status: draft
groma:
  id: commands
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Parses the subcommand and its flags for `ingest`, `load-eval-run`, `load-verdicts`, `compare-verdicts`, `load-curation`, `load-runs`, `report`, `package` and `fixture`, prints usage for `--help` (exit 0) and for no or an unknown subcommand, an unknown flag or a missing required flag (stderr, exit 1), refuses `--parse-only` with `--dry-run`, and reports errors as `evals <command>: <what>` with exit 1.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [commands](commands.md) | [ingest](ingest.md) | Runs the projection | function call |
| [commands](commands.md) | [evaluations](evaluations.md) | Loads evaluation files | function call |
| [commands](commands.md) | [runs](runs.md) | Loads a harness campaign | function call |
| [commands](commands.md) | [reports](reports.md) | Renders the reports | function call |
| [commands](commands.md) | [packager](packager.md) | Builds a package | function call |
| [commands](commands.md) | [fixture](fixture.md) | Starts the fixture | function call |
