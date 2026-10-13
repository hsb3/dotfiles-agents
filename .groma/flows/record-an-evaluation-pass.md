---
type: Groma Flow
title: Record an evaluation pass
groma:
  id: record-an-evaluation-pass
---

The owner records one evaluation pass in three loads: `evals load-eval-run <manifest>` writes the eval run and its responses with their measurement (and may stamp `eval_run` on one assessor), `evals load-verdicts <file>...` writes that pass verdicts as assessments, and `evals load-curation <file>` writes job coverage and relationships; each names the eval run it came from. `evals compare-verdicts` measures agreement between two verdict sets offline, without the database.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Owner](../actors/owner.md) | [evals CLI](../systems/evals/containers/evals-cli/container.md) | Run `evals load-eval-run`, then `load-verdicts`, then `load-curation` |
| [Entry point](../systems/evals/containers/evals-cli/components/cli.md) | [Commands](../systems/evals/containers/evals-cli/components/commands.md) | Pass the arguments |
| [Commands](../systems/evals/containers/evals-cli/components/commands.md) | [Evaluations](../systems/evals/containers/evals-cli/components/evaluations.md) | Load the manifest, verdict or curation file |
| [Evaluations](../systems/evals/containers/evals-cli/components/evaluations.md) | [Store](../systems/evals/containers/evals-cli/components/store.md) | Resolve eval runs, extenders and elements, plan and write |
| [Store](../systems/evals/containers/evals-cli/components/store.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Write eval_runs and eval_responses, then assessments, then job_coverage and relationships |
| [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | [PocketBase database](../systems/evals/containers/pocketbase-database/container.md) | Store the evaluation records |
