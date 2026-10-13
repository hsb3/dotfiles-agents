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
The `site` binary (`bun src/cli.ts <command>`). It passes the command-line arguments to Commands and exits with the code Commands returns.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [cli](cli.md) | [commands](commands.md) | Passes command-line arguments | function call |
