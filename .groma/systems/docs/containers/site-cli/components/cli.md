---
type: C4 Component
title: CLI entry point
status: stable
groma:
  id: cli
  parent: site-cli
  code:
    - scanner: typescript
      file: src/cli.ts
  draft: v1
description: Hands the process arguments to the command dispatcher
---
The `site` binary (`bun src/cli.ts <command>`). It hands the command-line arguments to Commands and sets the process exit code from the result; `serve` keeps the process running through its server.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/cli.ts](../../../../../../src/cli.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Passes command-line arguments | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/cli.ts](../../../../../../src/cli.ts) | [src/commands.ts](../../../../../../src/commands.ts) | Calls imported function: run | typescript |
