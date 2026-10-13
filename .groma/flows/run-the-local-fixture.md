---
type: Groma Flow
title: Run the local fixture
groma:
  id: run-the-local-fixture
---

The owner runs `evals fixture` to look at Toolbox without real data: a fresh package is built from the synthetic checkout, served by the local PocketBase binary on loopback, seeded through the store, and removed on Ctrl-C.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals fixture` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Fixture](../systems/evals/containers/evals-cli/components/fixture.md) | Start the fixture |
| [Fixture](../systems/evals/containers/evals-cli/components/fixture.md) | [Packager](../systems/evals/containers/evals-cli/components/packager.md) | Build a fresh package from the synthetic checkout |
| [Packager](../systems/evals/containers/evals-cli/components/packager.md) | [Deploy package](../systems/evals/containers/deploy-package/container.md) | Write the package into a temporary directory |
| [Fixture](../systems/evals/containers/evals-cli/components/fixture.md) | [Local PocketBase binary](../externals/local-pocketbase-binary.md) | Run start.sh with the local binary on loopback |
| [Fixture](../systems/evals/containers/evals-cli/components/fixture.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Wait for /api/health |
| [Fixture](../systems/evals/containers/evals-cli/components/fixture.md) | [Store](../systems/evals/containers/evals-cli/components/store.md) | Seed the synthetic records |
| [Store](../systems/evals/containers/evals-cli/components/store.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Create records as the fixture superuser |
