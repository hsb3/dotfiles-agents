---
type: Groma Flow
title: Check loadability
groma:
  id: check-loadability
---

The owner runs `agent-harness <candidate> --candidate-dir <path> --smoke` before spending a campaign on a candidate. Each cell injects the candidate into an empty workspace as a `with` trial would, asks the agent CLI to reply `OK`, logs the raw stdout and prints whether the candidate loaded; nothing reaches the ledger.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [agent-harness CLI](../systems/harness/containers/agent-harness-cli/container.md) | Run `agent-harness <candidate> --candidate-dir <path> --smoke` |
| [Entry point](../systems/harness/containers/agent-harness-cli/components/cli.md) | [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/harness/containers/agent-harness-cli/components/commands.md) | [Smoke](../systems/harness/containers/agent-harness-cli/components/smoke.md) | Run the loadability check |
| [Smoke](../systems/harness/containers/agent-harness-cli/components/smoke.md) | [Candidate](../systems/harness/containers/agent-harness-cli/components/candidate.md) | Load and classify the candidate |
| [Smoke](../systems/harness/containers/agent-harness-cli/components/smoke.md) | [Harnesses](../systems/harness/containers/agent-harness-cli/components/harnesses.md) | Preflight each cell |
| [Smoke](../systems/harness/containers/agent-harness-cli/components/smoke.md) | [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | Inject and run the agent as a with trial |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Claude Code adapter](../systems/harness/containers/agent-harness-cli/components/claude.md) | Inject the candidate and build the argv |
| [Trial](../systems/harness/containers/agent-harness-cli/components/trial.md) | [Claude Code CLI](../externals/claude-code-cli.md) | Run `Reply with exactly: OK` |
| [Smoke](../systems/harness/containers/agent-harness-cli/components/smoke.md) | [Trial logs](../systems/harness/containers/trial-logs/container.md) | Write the raw stdout log |
