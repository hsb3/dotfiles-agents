---
type: C4 Component
title: Fixture
description: Runs a disposable seeded PocketBase for the UI
status: stable
groma:
  id: fixture
  parent: evals-cli
  technology: TypeScript
  draft: v1
  code:
    - scanner: typescript
      file: src/fixture.ts
    - scanner: typescript
      file: src/synthetic-tree.ts
---

Serves `evals fixture`: writes the synthetic dotfiles-agents checkout the tests also use (or takes `--source-root`), builds a fresh package from it and this repository `ui/dist` in a new temporary directory, starts its `start.sh` with the local PocketBase binary on a free loopback port with an empty data directory and the synthetic superuser, waits up to 10 s for `/api/health`, creates the verified synthetic user, seeds synthetic records (catalog, evaluation, coverage, 27 runs built by the `load-runs` run builder with a valid comparison pair, one protected artifact), prints the URL and credentials, and deletes everything on Ctrl-C. It reads no credentials from the environment.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/packager.ts](../../../../../../src/packager.ts) | Builds a fresh package | function call |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/runs.ts](../../../../../../src/runs.ts) | Builds run rows | function call |
| [fixture](fixture.md) | [local-pocketbase-binary](../../../../../externals/local-pocketbase-binary.md) | Starts a disposable server | child process, loopback HTTP |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [pocketbase-service](../../pocketbase-service/container.md) | Waits for health | HTTP /api/health, loopback |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/store.ts](../../../../../../src/store.ts) | Seeds synthetic records | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/packager.ts](../../../../../../src/packager.ts) | Calls imported function: buildPackage | typescript |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/runs.ts](../../../../../../src/runs.ts) | Calls imported functions: buildRun, readLedger | typescript |
| [src/fixture.ts](../../../../../../src/fixture.ts) | [src/store.ts](../../../../../../src/store.ts) | Calls imported functions: CommandError, applyPlans, connect, diff | typescript |
