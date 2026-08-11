---
id: decision-5
title: 'evals/ and harness/ extraction: both, but deferred (dev is the workbench)'
date: '2026-08-04 02:54'
status: accepted
---
## Context

`evals/` tracked `data.db` is ~16MB of the repo's ~29MB; under the pointer model consumers
clone the marketplace repo. The owner had signalled intent to extract the harness to its
own repo (backlog task-6).

## Decision

**Direction:** extract **both** `evals/` and `harness/` to their own repos eventually
(harness first — it's self-contained — then evals), each owning its history with
consume-pointers left behind.

**Timing: deferred / not now.** Owner's words: *"not yet — they don't travel to main, for
now dev is my workbench; we'll move after things mature a bit."* task-6 is dropped to Low
priority and parked; no extraction is scheduled this cycle.

## Consequences

- task-6 stays open at Low, parked; revisit once the workbench stabilises.
- Reinforces decision-4: `evals/`/`harness/` are excluded from what publishes to `main`
  regardless of extraction timing — they live only on `dev` until moved.
- No DAG/`flow.yaml` changes yet (the 3 workbench nodes stay for now).
