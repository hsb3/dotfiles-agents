---
type: C4 Component
title: Harnesses
description: 'Knows the three harnesses: names, default models, preflight and adapters'
status: stable
groma:
  id: harnesses
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/harnesses.ts
---

Validates harness lists (order kept, duplicates dropped; an unknown name fails with the message the dispatcher turns into exit 3), runs preflight (CLI on `PATH`, and the credential variables opencode and codex need), reads `<exe> --version` with a 30 s limit (`unknown` when empty, `unavailable` when missing or slow), lists the auth variables that are set (names only), and builds a child environment: the harness's own minus the adapter's variable prefix and the four `XDG_*` variables, plus the adapter's per-run values. It defines the adapter contract (argv, per-run env, injection, fold, success test), the trial record a fold produces and the JSONL parsing the folds share, and hands out the adapter for each harness.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/harnesses.ts](../../../../../../src/harnesses.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Reads the CLI version | function call |
| [src/harnesses.ts](../../../../../../src/harnesses.ts) | [src/claude.ts](../../../../../../src/claude.ts) | Hands out the claude adapter | module import |
| [src/harnesses.ts](../../../../../../src/harnesses.ts) | [src/opencode.ts](../../../../../../src/opencode.ts) | Hands out the opencode adapter | module import |
| [src/harnesses.ts](../../../../../../src/harnesses.ts) | [src/codex.ts](../../../../../../src/codex.ts) | Hands out the codex adapter | module import |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/harnesses.ts](../../../../../../src/harnesses.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Calls imported functions: findExecutable, runProcess | typescript |
