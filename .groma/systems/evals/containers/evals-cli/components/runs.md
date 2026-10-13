---
type: C4 Component
title: Runs
description: Loads harness ledgers and logs into runs and their children
status: draft
groma:
  id: runs
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `evals load-runs`: reads the JSON Lines ledger (later rows with the same key replace earlier ones), scopes it by `--campaign` and `--candidate`, links each row to its log by `log_path` or name prefix, builds each run row with its `measurement` v1 envelope and `record_sha256`, deduplicates artifacts by sha256 and writes runs, artifacts, run events and tool calls without ever erasing stored evidence on a logless re-run.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [runs](runs.md) | [agent-harness-output](../../../../../externals/agent-harness-output.md) | Reads the ledger and logs | filesystem, read-only |
| [runs](runs.md) | [logs](logs.md) | Parses trial logs | function call |
| [runs](runs.md) | [store](store.md) | Plans and writes runs and evidence | function call |
