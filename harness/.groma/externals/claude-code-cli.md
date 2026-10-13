---
type: C4 System
title: Claude Code CLI
description: Agent CLI under test and the rubric grader
status: stable
groma:
  id: claude-code-cli
  technology: claude 2.1.296
---

Run as `claude -p` with `--output-format stream-json` as an agent under test, with the candidate injected through `--plugin-dir` or `--agents`; and run again with `--bare --output-format json --json-schema` as the grader, whose JSON result carries `structured_output.grades`. Each run has its own `HOME` and `CLAUDE_CONFIG_DIR` inside the run dir.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [claude-code-cli](claude-code-cli.md) | [anthropic-api](anthropic-api.md) | Calls Claude models | HTTPS |
