---
type: Groma Flow
title: Project the catalog
groma:
  id: project-the-catalog
---

The owner runs `evals ingest --source-root <dir>`: the checkout is read and validated without the database, the seed data joins it, the plan is computed against the stored records and then written: extenders, files, distributions, frontmatter dimensions and `mechanical-v1` assessments, retiring extenders that left the checkout.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals ingest --source-root <dir>` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Ingest](../systems/evals/containers/evals-cli/components/ingest.md) | Run the projection |
| [Ingest](../systems/evals/containers/evals-cli/components/ingest.md) | [Checkout](../systems/evals/containers/evals-cli/components/checkout.md) | Read roster, externals, units and assemblies |
| [Checkout](../systems/evals/containers/evals-cli/components/checkout.md) | [dotfiles-agents checkout](../externals/dotfiles-agents-checkout.md) | Read the files, never writing |
| [Ingest](../systems/evals/containers/evals-cli/components/ingest.md) | [Seed data](../systems/evals/containers/seed-data/container.md) | Read frameworks, sources, frontmatter spec and stdlib names |
| [Ingest](../systems/evals/containers/evals-cli/components/ingest.md) | [Store](../systems/evals/containers/evals-cli/components/store.md) | Plan against stored records, then write and retire |
| [Store](../systems/evals/containers/evals-cli/components/store.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Read and write records as superuser |
| [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | [PocketBase database](../systems/evals/containers/pocketbase-database/container.md) | Store the projection |
