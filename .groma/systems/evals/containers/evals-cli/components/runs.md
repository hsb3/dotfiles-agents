---
type: C4 Component
title: Runs
description: Loads harness ledgers and logs into runs and their children
status: stable
groma:
  id: runs
  parent: evals-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/runs.ts
---

Serves `evals load-runs`: reads the JSON Lines ledger (later rows with the same key replace earlier ones), scopes it by `--campaign` and `--candidate`, links each row to its log by `log_path` or name prefix, builds each run row with its `measurement` v1 envelope and `record_sha256`, deduplicates artifacts by sha256 and writes runs, artifacts, run events and tool calls without ever erasing stored evidence on a logless re-run.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [runs](runs.md) | [agent-harness-output](../../../../../externals/agent-harness-output.md) | Reads the ledger and logs | filesystem, read-only |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/store.ts](../../../../../../src/store.ts) | Plans and writes runs and evidence | function call |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/logs.ts](../../../../../../src/logs.ts) | Parses trial logs | function call |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/canonical.ts](../../../../../../src/canonical.ts) | Hashes ledger rows canonically | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/canonical.ts](../../../../../../src/canonical.ts) | Calls imported functions: canonicalSha256, parseJson, plain, sha256Hex | typescript |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/logs.ts](../../../../../../src/logs.ts) | Calls imported function: parseLog | typescript |
| [src/runs.ts](../../../../../../src/runs.ts) | [src/store.ts](../../../../../../src/store.ts) | Calls imported functions: CommandError, ValidationError, applyPlans, connect, diff, fetchAll, fetchWhereIn, formatPlan, formatWarnings, newId | typescript |
