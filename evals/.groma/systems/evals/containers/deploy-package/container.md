---
type: C4 Container
title: Deploy package
description: Generated deploy directory, untracked
status: stable
groma:
  id: deploy-package
  parent: evals
  technology: Directory with Dockerfile
---

Written by `evals package --out <dir>`: `Dockerfile`, `start.sh`, `railway.toml`, the catalog hook with its catalog and receipt, every migration and the UI build in `pb_public`. Deterministic, and free of credentials, data, ledgers and source-tree files.
