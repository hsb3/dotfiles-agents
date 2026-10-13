---
type: C4 System
title: Codex CLI
description: Agent CLI under test
status: stable
groma:
  id: codex-cli
  technology: codex-cli 0.162.1
---

Run as `codex exec --json` with `CODEX_HOME` inside the run dir. A plugin candidate is installed first through `codex plugin marketplace add` and `codex plugin add` from a local marketplace. Emits JSONL item events.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [codex-cli](codex-cli.md) | [openai-api](openai-api.md) | Calls OpenAI models | HTTPS |
