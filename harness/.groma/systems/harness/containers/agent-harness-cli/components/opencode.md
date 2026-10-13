---
type: C4 Component
title: opencode adapter
description: 'opencode adapter: argv, isolation, injection and JSON-event fold'
status: stable
groma:
  id: opencode
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/opencode.ts
---

Builds `opencode run <prompt> --format json --auto --standalone -m <provider/model>`; `--standalone` is mandatory, since without it opencode starts a background service that outlives the trial, and a model id without `/` gets the `anthropic/` prefix. Its per-run env sets `HOME` and `OPENCODE_CONFIG_DIR` (the config root) inside the run dir for both configs, after the `OPENCODE*` and `XDG_*` scrub. Injects a skill whose name opencode accepts into `oc-config/skills/` with a permission `opencode.json`, or agents translated into `oc-config/agents/<name>.md` subagents (description, model and permission rules); a plugin, or a skill with an invalid name, cannot be hosted. Folds `step_start`, `tool_use`, `text`, `step_finish` and `error` events into the trial record; duration is the wall-clock time of the run. Success is exit 0.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [opencode](opencode.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [opencode](opencode.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill | filesystem |
| [src/opencode.ts](../../../../../../src/opencode.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Parses stream events into a trial record | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/opencode.ts](../../../../../../src/opencode.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: emptyRecord, jsonLines, num | typescript |
