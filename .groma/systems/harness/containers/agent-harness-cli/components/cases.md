---
type: C4 Component
title: Cases
description: Loads and validates a candidate's case dataset
status: stable
groma:
  id: cases
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/cases.ts
---

Reads `<cases-dir>/<candidate>/<case-id>/case.json` (a non-empty `prompt`, optional `assertions` of `{id, text}`, other keys ignored), notes each case's optional `fixture/` directory and `check.py`, ignores subdirectories without `case.json`, sorts cases by id and applies `--case`. The default cases dir is the shipped `cases/`; real cases come from an external directory. Every dataset error fails with the spec's message, which the caller turns into exit 2.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [cases](cases.md) | [cases-directory](../../../../../externals/cases-directory.md) | Reads case datasets | case.json files |
| [cases](cases.md) | [shipped-cases](../../shipped-cases/container.md) | Reads the shipped cases | case.json files |
