---
type: C4 Component
title: Trial
description: Runs one trial from run dir to ledger row
status: stable
groma:
  id: trial
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/trial.ts
---

Runs one trial and appends its row at once, so an interrupted run resumes cleanly. It creates the run dir `<tmp>/harness-<harness>-<candidate>-<case>-<config>-<trial>-<random>/` (honouring `$TMPDIR`) with `ws/` copied from the case fixture or empty. When the harness cannot host the candidate's kind it writes a skip row for either config and deletes the run dir. Otherwise it builds the child environment through the harness adapter, injects the candidate for `with` (a failed codex plugin install becomes an injection-failure row and keeps the run dir), runs the agent CLI in `ws/` under the timeout, writes the per-trial log (`# preconditions:` header, then raw stdout) under `--runs-dir`, folds stdout, runs `check.py` and the grader, and applies the pass rule and the `error` rules. The run dir is deleted after a pass unless `--keep-workspaces` is set; a failing trial keeps it and records `ws/` in the row. Its agent-run step (injection, CLI run, fold) is shared with the smoke check.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Gets the adapter and child environment | function call |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/claude.ts](../../../../../../src/claude.ts) | Injects and folds a claude run | adapter interface |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/opencode.ts](../../../../../../src/opencode.ts) | Injects and folds an opencode run | adapter interface |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/codex.ts](../../../../../../src/codex.ts) | Injects and folds a codex run | adapter interface |
| [trial](trial.md) | [run-dirs](../../run-dirs/container.md) | Creates the run dir and workspace copy | filesystem |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Runs the agent CLI | function call |
| [trial](trial.md) | [claude-code-cli](../../../../../externals/claude-code-cli.md) | Runs the agent under test | argv/env, stream-json events |
| [trial](trial.md) | [opencode-cli](../../../../../externals/opencode-cli.md) | Runs the agent under test | argv/env, JSON events, --standalone |
| [trial](trial.md) | [codex-cli](../../../../../externals/codex-cli.md) | Runs the agent under test | exec --json events |
| [trial](trial.md) | [trial-logs](../../trial-logs/container.md) | Writes the trial log | file |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/checks.ts](../../../../../../src/checks.ts) | Runs check.py | function call |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/grader.ts](../../../../../../src/grader.ts) | Grades the assertions | function call |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Appends the row | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/checks.ts](../../../../../../src/checks.ts) | Calls imported function: runChecks | typescript |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/grader.ts](../../../../../../src/grader.ts) | Calls imported function: grade | typescript |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: adapterFor, authEnvPresent, childEnv, scrubEnv | typescript |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/ledger.ts](../../../../../../src/ledger.ts) | Calls imported functions: appendRow, pythonJson | typescript |
| [src/trial.ts](../../../../../../src/trial.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Calls imported function: runProcess | typescript |
