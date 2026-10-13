---
type: C4 Component
title: Cases
description: Loads and validates a candidate's case dataset
status: draft
groma:
  id: cases
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Reads `<cases-dir>/<candidate>/<case-id>/case.json` (non-empty `prompt`, optional `assertions` of `{id, text}`), notes each case's optional `fixture/` and `check.py`, sorts cases by id and applies `--case`. Every dataset error exits 2 with the spec's message.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [cases](cases.md) | [cases-directory](../../../../../externals/cases-directory.md) | Reads case datasets | case.json files |
| [cases](cases.md) | [shipped-cases](../../shipped-cases/container.md) | Reads the shipped cases | case.json files |
