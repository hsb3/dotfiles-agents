---
type: C4 System
title: Drift guards CI job
status: stable
groma:
  id: drift-guards-ci-job
  technology: GitHub Actions
---

The `drift guards (roster · marketplace · catalog)` job, run on every pull request. It runs `site build` as the repo-wide link check; the exit code is the outcome.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [drift-guards-ci-job](drift-guards-ci-job.md) | [site-cli](../systems/docs/containers/site-cli/container.md) | Runs the link check | shell |
