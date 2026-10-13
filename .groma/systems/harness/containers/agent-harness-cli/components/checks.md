---
type: C4 Component
title: Checks
description: Runs a case's deterministic check.py
status: stable
groma:
  id: checks
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/checks.ts
      symbol: runChecks
---

Runs `python3 <case dir>/check.py` with cwd = the final workspace, the trial's child environment and a 120 s timeout; its exit code is ignored. Its stdout must be a JSON array of `{id, passed, evidence}`; a missing `python3`, a timeout, stdout that is not JSON, not an array or holds malformed entries all become one failed `check.py` entry with `check-error: <reason>`.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/checks.ts](../../../../../../src/checks.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Runs check.py | function call |
| [checks](checks.md) | [python3](../../../../../externals/python3.md) | Runs check.py | stdout JSON array |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/checks.ts](../../../../../../src/checks.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Calls imported function: runProcess | typescript |
