---
type: C4 Component
title: Grader
description: Grades a trial's assertions with the Claude rubric grader
status: draft
groma:
  id: grader
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Builds the grader prompt (workspace digest, the first 3000 characters of the result, the assertions as JSON) and runs `claude -p --bare --output-format json --json-schema` under its own per-run home. Reads `structured_output.grades`; anything else marks every assertion failed with `grader-error`.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [grader](grader.md) | [subprocess](subprocess.md) | Runs the grader | function call |
| [grader](grader.md) | [claude-code-cli](../../../../../externals/claude-code-cli.md) | Grades the workspace | JSON result with structured_output |
