---
type: C4 Actor
title: Owner
description: Maintainer of the coding-agent extenders
status: stable
groma:
  id: owner
---

Runs `agent-harness` by hand to evaluate one candidate, check its loadability or read its report, installs the weekly schedule, and later runs the evals loader over the ledger as a separate, deliberate step.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [owner](owner.md) | [agent-harness-cli](../systems/harness/containers/agent-harness-cli/container.md) | Runs evaluations, smoke checks and reports | shell |
| [owner](owner.md) | [launchd-script](../systems/harness/containers/launchd-script/container.md) | Installs the weekly schedule | shell |
| [owner](owner.md) | [evals-loader](../externals/evals-loader.md) | Ingests the ledger | shell |
