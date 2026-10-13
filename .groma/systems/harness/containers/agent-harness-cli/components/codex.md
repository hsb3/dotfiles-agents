---
type: C4 Component
title: Codex adapter
description: 'Codex adapter: argv, isolation, injection, plugin install and item-event fold'
status: draft
groma:
  id: codex
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Builds `codex exec --json … -C <workspace> -m <model>`, scrubs `CODEX_*` variables, sets a per-run `HOME` and `CODEX_HOME` and passes `OPENAI_API_KEY` on as `CODEX_API_KEY`. Injects a skill under `codex-home/skills/`, agents as `codex-home/agents/<name>.toml`, and a plugin by building a local marketplace and running the two `codex plugin` install commands, whose failure becomes an injection-failure row. Folds `item.completed`, `turn.completed`, `turn.failed` and `error` events into the trial record.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [codex](codex.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [codex](codex.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill or plugin | filesystem |
| [codex](codex.md) | [subprocess](subprocess.md) | Runs the plugin install | function call |
| [codex](codex.md) | [codex-cli](../../../../../externals/codex-cli.md) | Installs the plugin | codex plugin marketplace add / plugin add --json |
