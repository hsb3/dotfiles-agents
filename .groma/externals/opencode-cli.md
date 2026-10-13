---
type: C4 System
title: opencode CLI
description: Agent CLI under test
status: stable
groma:
  id: opencode-cli
  technology: opencode 2.0.25
---

Run as `opencode run --format json --auto --standalone` with `OPENCODE_CONFIG_DIR` pointing into the run dir, where injected skills and agents are written. Emits JSONL events.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [opencode-cli](opencode-cli.md) | [anthropic-api](anthropic-api.md) | Calls Claude models | HTTPS |
