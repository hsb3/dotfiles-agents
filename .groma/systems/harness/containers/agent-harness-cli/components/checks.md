---
type: C4 Component
title: Checks
description: Runs a case's deterministic check.py
status: draft
groma:
  id: checks
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Runs `python3 <case dir>/check.py` in the final workspace with a 120 s timeout and parses its stdout as a JSON array of `{id, passed, evidence}`; any failure becomes one failed `check.py` entry with `check-error: <reason>`.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [checks](checks.md) | [subprocess](subprocess.md) | Runs check.py | function call |
| [checks](checks.md) | [python3](../../../../../externals/python3.md) | Runs check.py | stdout JSON array |
