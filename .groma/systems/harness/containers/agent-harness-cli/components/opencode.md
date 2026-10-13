---
type: C4 Component
title: opencode adapter
description: 'opencode adapter: argv, isolation, injection and JSON-event fold'
status: draft
groma:
  id: opencode
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Builds `opencode run … --format json --auto --standalone -m <provider/model>`, scrubs `OPENCODE*` variables and sets a per-run `HOME` and `OPENCODE_CONFIG_DIR`. Injects a skill (when its name is valid for opencode) or agents translated into opencode agent files with mapped permissions; a plugin is unsupported. Folds `step_start`, `tool_use`, `text`, `step_finish` and `error` events into the trial record.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [opencode](opencode.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [opencode](opencode.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill | filesystem |
