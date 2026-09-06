# planning-desk

Stands up and runs a source-grounded planning desk under `_meta/plans/`: author conformant
GitHub issue bodies, write deep build plans, and drive both through a multi-round draft ->
review -> fix -> reconcile loop, backed by a bundled toolkit of governance scripts
(conformance, coverage, reconcile, sequence, deps, sync, evidence). Every claim is grounded
in cited source, plans state deliverables/criteria/parallelism — never timelines — and the
toolkit keeps the board and the desk in sync.

## When it triggers

Use it to file or fix a GitHub issue with real acceptance criteria, plan a feature or epic
before building, run a planning or backlog-grooming session, organize work in `_meta/plans/`,
audit issue/plan drift, or set up this planning system in a new repo — even phrased loosely
as "write me an issue", "plan this out", "groom the backlog", "what should I work on next",
or "get this repo's planning organized".

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships in the `mise-en-place` bundle.
