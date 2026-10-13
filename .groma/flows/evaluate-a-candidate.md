---
type: Groma Flow
title: Evaluate a candidate
groma:
  id: evaluate-a-candidate
---

The owner runs `agent-harness <candidate> --candidate-dir <path>`. For each (harness, model) cell that passes preflight, the grid runs every case × config × trial whose resume key is not yet in the ledger: a trial copies the case fixture into a fresh run dir, injects the candidate for `with` the harness's way (claude shown), runs the agent CLI under a per-run home, logs its stdout, grades the final workspace with `check.py` and the rubric grader, and appends one row to the ledger. Each cell ends with the summary line and the candidate's report.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [agent-harness CLI](../systems/harness/containers/agent-harness-cli/container.md) | Run `agent-harness <candidate> --candidate-dir <path>` |
| [Entry point](../systems/harness/containers/agent-harness-cli/components/cli.md) | [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | Run the grid for the candidate |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Candidate](../systems/harness/containers/agent-harness-cli/components/candidate.md) | Load and classify the candidate |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Cases](../systems/harness/containers/agent-harness-cli/components/cases.md) | Load the case dataset |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Harnesses](../systems/harness/containers/agent-harness-cli/components/harnesses.md) | Preflight the cell and read the CLI version |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Ledger](../systems/harness/containers/agent-harness-cli/components/ledger.md) | Read the done resume keys |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | Run each pending trial |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Run dirs](../systems/harness/containers/run-dirs/container.md) | Create the run dir and copy the fixture into ws/ |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Claude Code adapter](../systems/harness/containers/agent-harness-cli/components/claude.md) | Inject the candidate (with only) and build the argv |
| [Claude Code adapter](../systems/harness/containers/agent-harness-cli/components/claude.md) | [Run dirs](../systems/harness/containers/run-dirs/container.md) | Write the plugin wrapper and per-run homes |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Claude Code CLI](../externals/claude-code-cli.md) | Run the agent in ws/ under the timeout |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Trial logs](../systems/harness/containers/trial-logs/container.md) | Write the preconditions header and raw stdout |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Checks](../systems/harness/containers/agent-harness-cli/components/checks.md) | Run the case check.py |
| [Checks](../systems/harness/containers/agent-harness-cli/components/checks.md) | [python3](../externals/python3.md) | Run check.py in the final workspace |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Grader](../systems/harness/containers/agent-harness-cli/components/grader.md) | Grade the assertions |
| [Grader](../systems/harness/containers/agent-harness-cli/components/grader.md) | [Claude Code CLI](../externals/claude-code-cli.md) | Run the --bare rubric grader |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Ledger](../systems/harness/containers/agent-harness-cli/components/ledger.md) | Append the trial row |
| [Ledger](../systems/harness/containers/agent-harness-cli/components/ledger.md) | [Ledger (results.jsonl)](../systems/harness/containers/results-ledger/container.md) | Append one JSON line |
| [Grid](../systems/harness/containers/agent-harness-cli/components/grid.md) | [Report](../systems/harness/containers/agent-harness-cli/components/report.md) | Print the summary and the report |
