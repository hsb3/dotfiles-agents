---
type: Groma Flow
title: Render the reports
groma:
  id: render-the-reports
---

The owner runs `evals report --out <dir>`: the frameworks, elements, extenders, sources, job coverage, relationships, assessments and eval runs are read whole (from the database, or from JSON dumps with `--fixtures`, which needs no credentials), retired extenders and the rows that reference them are excluded, and `coverage-matrix.md` and `analysis.md` are written to the report directory, byte-identical for the same data.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals report --out <dir>` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Reports](../systems/evals/containers/evals-cli/components/reports.md) | Render the reports |
| [Reports](../systems/evals/containers/evals-cli/components/reports.md) | [Store](../systems/evals/containers/evals-cli/components/store.md) | Fetch the eight collections whole |
| [Store](../systems/evals/containers/evals-cli/components/store.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Read records as superuser |
| [Reports](../systems/evals/containers/evals-cli/components/reports.md) | [Report directory](../systems/evals/containers/report-directory/container.md) | Write coverage-matrix.md and analysis.md |
