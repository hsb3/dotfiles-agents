---
type: C4 Actor
title: Owner
description: Maintainer of dotfiles-agents who runs evals from the shell
status: stable
groma:
  id: owner
---

Runs `evals` subcommands to project the checkout, load evaluation passes and harness campaigns, render reports and build deploy packages, and deploys the package to Railway themself. Holds the PocketBase superuser credentials (`PB_ADMIN_EMAIL`, `PB_ADMIN_PASSWORD`).

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [owner](owner.md) | [evals-cli](../systems/evals/containers/evals-cli/container.md) | Runs evals subcommands | shell |
| [owner](owner.md) | [railway](../externals/railway.md) | Deploys a package | railway up |
