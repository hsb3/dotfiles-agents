---
id: decision-4
title: 'Publish model: main as fast-forward release gate'
date: '2026-08-04 02:54'
status: accepted
---
## Context

Post-ADR-0017 there is no tracked dist, so publishing no longer needs the filtered
parented assembly that `publish.yml` built. `publish.yml` was left deliberately broken
until the owner ruled how the pointer surface should publish (backlog task-5). `main`
still serves the frozen 2026-07-22 dist assembly to consumers.

## Decision

Keep `main` as a plain **fast-forward release gate**: publishing = merge dev→main. The
filtered-assembly build and its guards are retired. `main` remains the stable install ref
for consumers.

**Constraint (owner note on task-6):** `evals/` and `harness/` do **not** travel to
`main`. `dev` is the owner's workbench; publish carries only the marketplace surface.

## Consequences

- Rework `publish.yml` to a fast-forward merge (no assembly step), retire the
  filtered-assembly guards, and reconcile the three no-main-checkout guards + the
  `publish-to-main` skill runbook to the new model.
- Confirm `evals/`/`harness/` are excluded from what reaches `main`.
- Cross-referenced by task-5 (implementation) and decision-2 (pointer distribution).
