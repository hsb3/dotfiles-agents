---
type: C4 Component
title: Claude Code adapter
description: 'Claude Code adapter: argv, isolation, injection and stream-json fold'
status: draft
groma:
  id: claude
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Builds the `claude -p … --output-format stream-json` argv, scrubs `CLAUDE*` variables and sets a per-run `HOME` and `CLAUDE_CONFIG_DIR` with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`. Injects a plugin with `--plugin-dir`, a skill through a synthetic `eval-<skill>` plugin, and agents with `--agents` JSON. Folds the stream-json events into the trial record: loaded plugins, plugin errors, tool names, result, cost, duration, turns and tokens.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [claude](claude.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [claude](claude.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill | filesystem |
