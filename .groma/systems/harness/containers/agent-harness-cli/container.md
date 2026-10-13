---
type: C4 Container
title: agent-harness CLI
status: stable
groma:
  id: agent-harness-cli
  parent: harness
  technology: TypeScript on Bun
description: Command-line tool that measures whether a candidate extender improves a headless coding agent
---
The `agent-harness` binary. It runs a candidate (a skill, a set of subagent definitions or a Claude Code plugin) through each test case twice, once injected (`with`) and once not (`baseline`), under Claude Code, opencode or Codex, grades each final workspace with the case's `check.py` and an LLM rubric grader, and appends one JSON row per trial to an append-only ledger. It also checks a candidate's loadability (`--smoke`), prints a pass-rate report per candidate (`--report`) and runs the weekly `campaign` over every cased candidate. It has no server, no database and no parallelism.
