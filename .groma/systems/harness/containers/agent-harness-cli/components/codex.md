---
type: C4 Component
title: Codex adapter
description: 'Codex adapter: argv, isolation, injection, plugin install and item-event fold'
status: stable
groma:
  id: codex
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/codex.ts
      symbol: codex
---

Builds `codex exec --json --skip-git-repo-check --ephemeral --sandbox workspace-write -c sandbox_workspace_write.network_access=true --dangerously-bypass-hook-trust -C <workspace> -m <model> <prompt>`, never `--ignore-user-config`. Its per-run env sets `HOME` and `CODEX_HOME` inside the run dir and passes `OPENAI_API_KEY` on as `CODEX_API_KEY`, after the `CODEX_*` and `XDG_*` scrub; no `auth.json` is written. Injects a skill under `codex-home/skills/`, agents as `codex-home/agents/<name>.toml` (name, description, developer instructions), and a plugin by building a local `agent-harness` marketplace in `codex-market/` and running `codex plugin marketplace add` and `codex plugin add` (60 s each, in the workspace, with the trial env); a failing step becomes an injection-failure with that step's error text and exit code. Folds `item.completed`, `turn.completed`, `turn.failed` and top-level `error` events into the trial record; duration is the wall-clock time of the run. Success is exit 0 with a non-empty result.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [codex](codex.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [codex](codex.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill or plugin | filesystem |
| [src/codex.ts](../../../../../../src/codex.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Runs the plugin install | function call |
| [codex](codex.md) | [codex-cli](../../../../../externals/codex-cli.md) | Installs the plugin | codex plugin marketplace add / plugin add --json |
| [src/codex.ts](../../../../../../src/codex.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Parses stream events into a trial record | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/codex.ts](../../../../../../src/codex.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: emptyRecord, jsonLines, num | typescript |
| [src/codex.ts](../../../../../../src/codex.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Calls imported function: runProcess | typescript |
