---
id: decision-7
title: Minimum task-definition standard
date: '2026-08-06'
status: accepted
---
## Context

The 2026-08-04 GH→Backlog migration produced task cards whose only substance was a
pointer ("Migrated from GH #163.") into GitHub issues that are now closed — and under
decision-1, closed issues are outside the task system, so those cards were effectively
empty. Board review 2026-08-06 also found status rot (shipped work still To Do) and
unverifiable acceptance criteria. Owner ruled (sign-off
`_meta/signoff/2026-08-06-backlog-standards/answers.json`, item A) that a minimum
standard binds every card, and (item B) that the board is repaired in place with stable
task IDs — IDs are load-bearing provenance cited by decisions, ADRs, docs, commits, and
PR bodies.

## Decision

Every task card (and draft promoted to a task) must satisfy all five, at authoring time
and at every edit:

1. **Cold-readable description** — what and why-now, in current-architecture terms,
   readable without opening any external link. A bare "Migrated from GH #N" is not a
   description; if the substance lives elsewhere, it is copied in.
2. **Acceptance criteria on every task**, each independently verifiable — a command that
   passes, an artifact that exists, a grep that returns zero. Never "works well".
3. **References that resolve** — cited paths, decisions, and issues exist in the current
   tree at edit time; a pivot that invalidates a reference re-grounds the card.
4. **Status truth** — shipped work is marked Done with implementation notes citing the
   PR/commit as evidence, in the same PR that ships it.
5. **Decision-type tasks name the question, the options, and that the owner rules.**

Mechanics: task IDs are stable — repair in place; renumber only when the framing
genuinely changed (archive the old card, new card cites its ancestor). Task files are
edited by hand (Edit/Write), never through the backlog CLI's write commands — the CLI
can silently rewrite sibling task files from its index.

## Consequences

- The 2026-08-06 cleanup PR rewrites all non-conforming cards to this standard
  (sign-off items D–H record the per-card dispositions).
- Sessions touching a card that fails the standard fix the card in the same PR.
- CLAUDE.md's task-system section points here.
