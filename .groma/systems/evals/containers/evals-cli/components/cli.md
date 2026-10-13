---
type: C4 Component
title: Entry point
status: stable
groma:
  id: cli
  parent: evals-cli
  code:
    - scanner: typescript
      file: src/cli.ts
  draft: v1
description: Starts the evals binary
---
The `evals` executable named in `package.json` `bin`. It hands the process arguments to the command dispatcher and exits with the code the command returns.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [cli](cli.md) | [commands](commands.md) | Passes the arguments | function call |
