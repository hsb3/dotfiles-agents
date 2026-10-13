---
type: C4 Component
title: Grader
description: Grades a trial's assertions with the Claude rubric grader
status: stable
groma:
  id: grader
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/grader.ts
---

Builds the verbatim grader prompt: a digest of every workspace file as `<path> (<size>B)`, sorted and capped at 80 lines (symlinks listed, not followed), the first 3000 characters of the trial's result and the assertions as compact JSON. Runs `claude -p --bare --model <grader model> --output-format json --json-schema <schema>` with `Read,Grep,Glob` only, in the workspace, under the `--timeout`, with the claude scrub and its own `grader-home` and `grader-config` in the run dir. Reads `structured_output.grades`; a missing CLI, a timeout, stdout that is not JSON or holds no grades array marks every assertion failed with `grader-error`. The grader is claude whichever harness ran the trial.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Runs the grader | function call |
| [grader](grader.md) | [claude-code-cli](../../../../../externals/claude-code-cli.md) | Grades the workspace | JSON result with structured_output |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/claude.ts](../../../../../../src/claude.ts) | Builds the grader's isolated claude environment | function call |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Scrubs the grader environment | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/claude.ts](../../../../../../src/claude.ts) | Calls imported function: claudeRunEnv | typescript |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/harnesses.ts](../../../../../../src/harnesses.ts) | Calls imported function: scrubEnv | typescript |
| [src/grader.ts](../../../../../../src/grader.ts) | [src/subprocess.ts](../../../../../../src/subprocess.ts) | Calls imported function: runProcess | typescript |
