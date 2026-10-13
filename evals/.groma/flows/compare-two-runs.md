---
type: Groma Flow
title: Compare two runs
groma:
  id: compare-two-runs
---

A Toolbox reader opens Performance, finds runs by search, configuration and a duration or cost sort, selects one baseline and one with-configuration run, and reads their comparison: n=1, with minus baseline, no causal claim, and only metrics the measurement envelope marks available. The reader then inspects a run and opens its evidence through a short-lived file token.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Toolbox reader](../actors/toolbox-reader.md) | [Toolbox UI](../systems/evals/containers/toolbox-ui/container.md) | Open `#performance` and select a baseline and a with-configuration run |
| [UI entry](../systems/evals/containers/toolbox-ui/components/main.md) | [App](../systems/evals/containers/toolbox-ui/components/app.md) | Mount the shell, which shows sign-in until a session exists |
| [App](../systems/evals/containers/toolbox-ui/components/app.md) | [Performance View](../systems/evals/containers/toolbox-ui/components/performance-view.md) | Show the Performance area with the route parameters |
| [Performance View](../systems/evals/containers/toolbox-ui/components/performance-view.md) | [Api](../systems/evals/containers/toolbox-ui/components/api.md) | Read the runs (every page for a duration or cost sort), compare the selected pair, then inspect one run and request a file token for its evidence |
| [Api](../systems/evals/containers/toolbox-ui/components/api.md) | [PocketBase service](../systems/evals/containers/pocketbase-service/container.md) | Read runs, artifacts, events and tool calls with the user token; `POST /api/files/token` for the protected blob |
