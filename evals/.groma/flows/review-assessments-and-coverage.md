---
type: Groma Flow
title: Review assessments and coverage
groma:
  id: review-assessments-and-coverage
---

A Toolbox reader follows "View assessments" from an extender's documentation, or opens Evaluations directly, reads the current assessments and job coverage, and follows an eval run to its campaign in Performance.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Toolbox reader](../actors/toolbox-reader.md) | [Toolbox UI](../systems/evals/containers/toolbox-ui/container.md) | Open `#evaluations`, possibly as `#evaluations?extender=<id>` |
| [UI entry](../systems/evals/containers/toolbox-ui/components/main.md) | [App](../systems/evals/containers/toolbox-ui/components/app.md) | Mount the shell, which shows sign-in until a session exists |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Evaluations View](../systems/evals/containers/toolbox-ui/components/evaluations-view.md) | Show the Evaluations area with the route parameters |
| [Evaluations View](../systems/evals/containers/toolbox-ui/components/evaluations-view.md) | [Api](../systems/evals/containers/toolbox-ui/components/api.md) | Read the assessments (for one extender when given) with their expanded names, and the job coverage |
| [Api](../systems/evals/containers/toolbox-ui/components/api.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Read assessments and job coverage with the user token |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Performance View](../systems/evals/containers/toolbox-ui/components/performance-view.md) | Follow an eval run link to `#performance?campaign=<id>` for its responses and assessments |
