---
type: Groma Flow
title: Package and deploy
groma:
  id: package-and-deploy
---

The owner runs `evals package --source-root <dir> --out <dir>`: the catalog inputs and the UI build are validated, the catalog and its receipt are written beside the catalog hook, every migration and the UI build are copied, and the exact `Dockerfile`, `start.sh` and `railway.toml` complete the package. Deploying it is the owner step: `railway up` builds the image (downloading the pinned PocketBase release), and at start `start.sh` bootstraps the superuser and the server applies pending migrations to the database on the volume.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals package --source-root <dir> --out <dir>` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Packager](../systems/evals/containers/evals-cli/components/packager.md) | Build a package |
| [Packager](../systems/evals/containers/evals-cli/components/packager.md) | [dotfiles-agents checkout](../externals/dotfiles-agents-checkout.md) | Read marketplace.json and the workflows table |
| [Packager](../systems/evals/containers/evals-cli/components/packager.md) | [Toolbox UI](../systems/evals/containers/toolbox-ui/container.md) | Copy the validated UI build |
| [Packager](../systems/evals/containers/evals-cli/components/packager.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Copy the migrations and the catalog hook |
| [Packager](../systems/evals/containers/evals-cli/components/packager.md) | [Deploy package](../systems/evals/containers/deploy-package/container.md) | Write the catalog, receipt, Dockerfile, start.sh and railway.toml |
| [Owner](../actors/owner.md) | [Railway](../externals/railway.md) | Deploy the package with `railway up` |
| [Railway](../externals/railway.md) | [PocketBase release](../externals/pocketbase-release.md) | Download and check the PocketBase binary |
| [Railway](../externals/railway.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Run `start.sh` with the volume at /pb/pb_data |
| [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | [PocketBase database](../systems/evals/containers/pocketbase-database/container.md) | Apply pending migrations at start |
