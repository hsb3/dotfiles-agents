---
type: C4 Component
title: Trial
description: Runs one trial from run dir to ledger row
status: draft
groma:
  id: trial
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Creates the run dir and its `ws/` fixture copy, injects the candidate for `with` through the harness adapter (or writes a skip row when the harness cannot host the kind), runs the agent CLI under the timeout, writes the per-trial log, folds stdout, runs `check.py` and the grader, applies the pass rule, keeps or deletes the run dir, and appends the 29-field row at once. Its agent-run step is shared with the smoke check.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [trial](trial.md) | [harnesses](harnesses.md) | Gets the harness adapter | function call |
| [trial](trial.md) | [claude](claude.md) | Injects and folds a claude run | adapter interface |
| [trial](trial.md) | [opencode](opencode.md) | Injects and folds an opencode run | adapter interface |
| [trial](trial.md) | [codex](codex.md) | Injects and folds a codex run | adapter interface |
| [trial](trial.md) | [run-dirs](../../run-dirs/container.md) | Creates the run dir and workspace copy | filesystem |
| [trial](trial.md) | [subprocess](subprocess.md) | Runs the agent CLI | function call |
| [trial](trial.md) | [claude-code-cli](../../../../../externals/claude-code-cli.md) | Runs the agent under test | argv/env, stream-json events |
| [trial](trial.md) | [opencode-cli](../../../../../externals/opencode-cli.md) | Runs the agent under test | argv/env, JSON events, --standalone |
| [trial](trial.md) | [codex-cli](../../../../../externals/codex-cli.md) | Runs the agent under test | exec --json events |
| [trial](trial.md) | [trial-logs](../../trial-logs/container.md) | Writes the trial log | file |
| [trial](trial.md) | [checks](checks.md) | Runs check.py | function call |
| [trial](trial.md) | [grader](grader.md) | Grades the assertions | function call |
| [trial](trial.md) | [ledger](ledger.md) | Appends the row | function call |
