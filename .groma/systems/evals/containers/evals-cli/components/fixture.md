---
type: C4 Component
title: Fixture
description: Runs a disposable seeded PocketBase for the UI
status: draft
groma:
  id: fixture
  parent: evals-cli
  technology: TypeScript
  draft: v1
---

Serves `evals fixture`: builds a fresh package from the synthetic source tree (or `--source-root`), starts its `start.sh` on a free loopback port with an empty data directory, creates a verified synthetic user, seeds synthetic records including 27 runs built like `load-runs` builds them, prints the URL and credentials, and deletes everything on Ctrl-C.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [fixture](fixture.md) | [packager](packager.md) | Builds a fresh package | function call |
| [fixture](fixture.md) | [runs](runs.md) | Builds run rows | function call |
| [fixture](fixture.md) | [store](store.md) | Seeds synthetic records | function call |
| [fixture](fixture.md) | [local-pocketbase-binary](../../../../../externals/local-pocketbase-binary.md) | Starts a disposable server | child process, loopback HTTP |
