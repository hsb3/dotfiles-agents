---
type: C4 Component
title: Entry point
status: stable
groma:
  id: cli
  parent: agent-harness-cli
  code:
    - scanner: typescript
      file: src/cli.ts
  draft: v1
description: Process entry of the agent-harness binary
---
Hands the process arguments to the command dispatcher and exits with the code it returns.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [cli](cli.md) | [commands](commands.md) | Dispatches the command line | function call |
