---
title: SOP — issues and plans
status: active
created: 2026-07-01
---

# SOP — how issues and the plans to complete them are created

*How fuzzy intent becomes build-ready work: two artifacts per unit of work — a conformant issue
(the contract) and a source-grounded plan (the detail) — driven through a draft → review → fix →
reconcile loop. Harness-neutral: the desk is plain files under `_meta/plans/` plus `gh`.*

Delivered by the **`planning-desk`** extender.

## Principles

- **Two artifacts, two jobs.** The **issue body** is the *contract* a builder picks up cold — what
  to build, how it's judged, what's out of scope — conforming to the repo's issue template. The
  **plan** is the *build detail* — what already shipped vs what's residual, deliverables sliced into
  ownable units, the gates that fire, and the safe landing order. **The board tracks STATE; the desk
  holds DETAIL.**
- **Ground every claim in cited source.** Present-day facts (what exists, what's already built) are
  cited to `path:line`, never asserted from memory. A plan that invents state sends a builder down a
  wrong road.
- **Deliverables · acceptance criteria · parallelism — never timelines.** Every issue states what
  "done" means as checkable criteria; the plan states what can run in parallel. Owner deadlines are
  constraints, not schedules.
- **Don't fork the backlog.** The desk's issue bodies are *typed inputs that map onto* board items —
  cite the issue, don't maintain a second list. The board and repo remain the single source of truth
  for work state.

## The desk shape

```
_meta/plans/                 # the desk — one folder per unit of work
  README.md                  # the live per-plan status index (active / archived)
  _config.md                 # THIS project's gates, issue-template sections, canonical docs
  <slug>/
    issue-body.md            # the intended issue body (staged, reviewable, conformant)
    plan.md                  # the deep build plan (deliverables, acceptance, gates, order)
```

`_meta/plans/` is a local working desk (gitignored by default). It holds detail and rationale; the
board holds state. `_config.md` records what "conformant" means *for this repo* — its issue-template
sections, its gate labels, its canonical docs — so the same workflow adapts per project.

## What a good issue body contains

- **Title** — a specific, outcome-shaped summary.
- **Context / why** — the problem, linked to the canonical page or decision that motivates it.
- **Deliverables** — the concrete things to produce.
- **Acceptance criteria** — checkable, objective; how a reviewer confirms it's done. Not "works well."
- **Out of scope** — what this explicitly does *not* cover (prevents scope creep).
- **Dependencies** — blocked-by / relates-to, mapped onto the board.

## What a good plan contains

- **Shipped vs residual** — what already exists (cited), so the builder starts from truth.
- **Deliverables sliced into ownable units** — each independently buildable and reviewable.
- **Gates** — the hard checks that must pass (tests, lint, review, a promotion gate).
- **Safe landing order** — the sequence that keeps `main` green at every step; what parallelizes.

## The loop

1. **Draft** — author the issue body + plan from cited source.
2. **Review** — check conformance (does it match the template + carry real acceptance criteria?),
   coverage (are all deliverables planned?), and grounding (is every claim cited?).
3. **Fix** — resolve the review findings.
4. **Reconcile** — keep the desk and the board in sync; when an issue lands, archive its plan and
   move its index row from active to archived so drift audits stay clean.

## Governance checks

The workflow is backed by dependency-free scripts (conformance, coverage, reconcile, sequence,
deps, sync, evidence). Use them to keep issues template-conformant, plans fully covering their
deliverables, and the desk↔board mapping honest. Run them from the main checkout — they read live
`gh` + on-disk state.

## Relationship to decision records

When a plan makes a direction-setting choice (an architecture call, a scope cut), that rationale
graduates into an **append-only decision record** and the issue/plan links it. The plan holds "how
it's built"; the decision record holds "why we chose this."

## Harness portability

The desk is plain markdown + `gh`; nothing depends on a specific coding agent. The `planning-desk`
extender renders into every target harness, so the same authoring, review, and reconcile loop runs
identically under Claude Code, opencode, or any agent.
