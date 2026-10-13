---
type: C4 Component
title: Campaign
description: Runs the weekly campaign over every cased candidate
status: draft
groma:
  id: campaign
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Discovers the candidates as the subdirectory names of `--cases-dir` (minus `_template` and `smoke-echo`), resolves each one's path under `--candidates-root`, runs the grid for each with the dated `weekly-<YYYYMMDD>` label and prints each report, appending everything it prints to the campaign log. `--dry-run` prints the commands it would run instead.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [campaign](campaign.md) | [grid](grid.md) | Runs each candidate | function call |
| [campaign](campaign.md) | [report](report.md) | Prints each report | function call |
| [campaign](campaign.md) | [campaign-logs](../../campaign-logs/container.md) | Appends the transcript | file |
| [campaign](campaign.md) | [cases-directory](../../../../../externals/cases-directory.md) | Discovers candidates | directory listing |
| [campaign](campaign.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Resolves candidate paths | directory lookup |
