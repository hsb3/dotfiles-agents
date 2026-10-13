---
type: C4 Component
title: Packager
description: Builds a deterministic deploy directory
status: draft
groma:
  id: packager
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `evals package`: validates the UI build and the catalog inputs (marketplace manifest and the "Choose a workflow" table), writes `toolbox-catalog.json` and the `toolbox-package.json` receipt, copies the catalog hook, every migration and the UI build, and writes the exact `Dockerfile`, `start.sh` and `railway.toml`. Never deploys; refuses an existing `--out` and leaves nothing behind on failure.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [packager](packager.md) | [dotfiles-agents-checkout](../../../../../externals/dotfiles-agents-checkout.md) | Reads catalog inputs | filesystem, read-only |
| [packager](packager.md) | [toolbox-ui](../../toolbox-ui/container.md) | Copies the UI build | files from ui/dist |
| [packager](packager.md) | [pocketbase-service](../../pocketbase-service/container.md) | Copies migrations and the catalog hook | files |
| [packager](packager.md) | [deploy-package](../../deploy-package/container.md) | Writes the package | files |
