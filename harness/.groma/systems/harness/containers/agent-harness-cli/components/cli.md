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
description: Process entry of the agent-harness binary
---
Hands the process arguments to the command dispatcher and exits with the code it returns.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/cli.ts](../../../../../../src/cli.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Dispatches the command line | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/cli.ts](../../../../../../src/cli.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Calls imported function: main | typescript |
