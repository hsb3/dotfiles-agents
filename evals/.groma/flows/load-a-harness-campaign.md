---
type: Groma Flow
title: Load a harness campaign
groma:
  id: load-a-harness-campaign
---

The owner runs `evals load-runs --ledger <path>` after a harness campaign: the ledger rows are read and validated, each row is linked to its trial log, the logs are parsed into events, tool calls and artifacts, every run gets its `measurement` v1 envelope, and runs, artifacts, run events and tool calls are planned against what is stored and written without erasing evidence.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals load-runs --ledger <path>` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Runs](../systems/evals/containers/evals-cli/components/runs.md) | Load the campaign |
| [Runs](../systems/evals/containers/evals-cli/components/runs.md) | [Agent harness output](../externals/agent-harness-output.md) | Read the ledger and the linked logs |
| [Runs](../systems/evals/containers/evals-cli/components/runs.md) | [Logs](../systems/evals/containers/evals-cli/components/logs.md) | Parse each log into events, tool calls, artifacts and a rollup |
| [Runs](../systems/evals/containers/evals-cli/components/runs.md) | [Store](../systems/evals/containers/evals-cli/components/store.md) | Plan runs, artifacts, events and tool calls, then write |
| [Store](../systems/evals/containers/evals-cli/components/store.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Write records and protected artifact blobs |
| [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | [PocketBase database](../systems/evals/containers/pocketbase-database/container.md) | Store runs and their evidence |
