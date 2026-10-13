---
type: Groma Flow
title: Weekly campaign
groma:
  id: weekly-campaign
---

Every Monday at 09:00 launchd runs `scripts/launchd.sh run`, which sets up `PATH` and any missing API keys and runs `agent-harness campaign`. The campaign discovers the cased candidates, runs each one's grid under the `weekly-<YYYYMMDD>` label (each trial as in the Evaluate a candidate flow), prints every report and appends everything it prints to the campaign log. Later, as a separate and deliberate step, the owner runs the evals loader over the ledger and the logs its rows link to.

## Steps

| From | To | Action |
| --- | --- | --- |
| [launchd](../externals/launchd.md) | [launchd script](../systems/harness/containers/launchd-script/container.md) | Fire the Monday 09:00 LaunchAgent |
| [launchd script](../systems/harness/containers/launchd-script/container.md) | [agent-harness CLI](../systems/harness/containers/agent-harness-cli/container.md) | Run `agent-harness campaign --cases-dir <dir> --candidates-root <dir>` |
| [Entry point](../systems/harness/containers/agent-harness-cli/components/cli.md) | [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | Run the campaign |
| [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | [Cases directory](../externals/cases-directory.md) | Discover the cased candidates |
| [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | [Candidate extender](../externals/candidate-extender.md) | Resolve each candidate path |
| [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | Run each candidate with the dated label |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | Run each pending trial as in Evaluate a candidate |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Ledger](../systems/harness/containers/agent-harness-cli/components/ledger.md) | Append the trial row |
| [Ledger](../systems/harness/containers/agent-harness-cli/components/ledger.md) | [Ledger (results.jsonl)](../systems/harness/containers/results-ledger/container.md) | Append one JSON line |
| [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | [Report](../systems/harness/containers/agent-harness-cli/components/report.md) | Print each candidate report |
| [Campaign](../systems/harness/containers/agent-harness-cli/components/campaign.md) | [Campaign logs](../systems/harness/containers/campaign-logs/container.md) | Append everything printed to the campaign log |
| [Owner](../actors/owner.md) | [Evals loader](../externals/evals-loader.md) | Later, run the evals loader |
| [Evals loader](../externals/evals-loader.md) | [Ledger (results.jsonl)](../systems/harness/containers/results-ledger/container.md) | Read the trial rows |
| [Evals loader](../externals/evals-loader.md) | [Trial logs](../systems/harness/containers/trial-logs/container.md) | Read the logs linked by log_path |
