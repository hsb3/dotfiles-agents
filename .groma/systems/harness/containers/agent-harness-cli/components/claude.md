---
type: C4 Component
title: Claude Code adapter
description: 'Claude Code adapter: argv, isolation, injection and stream-json fold'
status: stable
groma:
  id: claude
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/claude.ts
---

Builds the `claude -p … --output-format stream-json --verbose --permission-mode acceptEdits` argv with `--setting-sources ""` and `--strict-mcp-config`, never `--bare`. Its per-run env sets `HOME` and `CLAUDE_CONFIG_DIR` inside the run dir with `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` (shared with the grader), after the `CLAUDE*` scrub. Injects a plugin with `--plugin-dir`, a skill through a synthetic `eval-<skill>` plugin under `<run>/plugin/`, and agents with `--agents` JSON. Folds the stream-json `init`, `assistant` and `result` events into the trial record: loaded plugins, plugin errors, tool names, result, cost, duration, turns, tokens and the error of an `is_error` result. Success is exit 0.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [claude](claude.md) | [run-dirs](../../run-dirs/container.md) | Writes the injection and per-run homes | filesystem |
| [claude](claude.md) | [candidate-extender](../../../../../externals/candidate-extender.md) | Copies the skill | filesystem |
| [src/claude.ts](../../../../../../src/claude.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Parses stream events into a trial record | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/claude.ts](../../../../../../src/claude.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported functions: emptyRecord, jsonLines, num | typescript |
