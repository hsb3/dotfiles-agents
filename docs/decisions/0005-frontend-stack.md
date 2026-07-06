# 0005 · Frontend stack for agent-built UI: Vite + React + shadcn/ui + Tailwind

_If a UI surface ever enters scope, build it on the stack coding agents are most fluent in, pinned by
a constraint doc. Proposed — binds only when a deliverable actually has a UI._

- **Status:** Proposed (ballot — the recommendation + the open question below)
- **Date:** 2026-07-01 (migrated from the strategy vault to a repo ADR 2026-07-05)
- **Raised by:** the frontend-stack shortlist research (strategy desk `analyses/frontend-stack-shortlist.md`)

## Context

If this project (or repos adopting its standards) grows UI surfaces built by coding agents, the stack
should be the one agents write with fewest first-try errors, pinned so agents don't drift. This ADR
captures the researched recommendation now so it isn't lost; it does **not** bind unless a UI surface
enters scope.

## Decision (pending scope trigger)

- **Recommended:** Vite + React + shadcn/ui + Tailwind CSS (+ TanStack Router/Query, React Hook Form +
  Zod). Rationale: largest agent training corpus → fewest correction cycles; shadcn/ui is copy-paste
  components, not a runtime dependency; swappable to TanStack Start / Next.js later without rewriting
  components. Cost: React boilerplate; no SSR out of the box.
- **The constraint doc matters more than the stack choice** — adoption means a `CLAUDE.md` constraint
  block in the repo so agents stay on the pinned stack.

## Consequences

- When accepted, a reusable stack-constraint block becomes a candidate extender (a rule or skill) in
  the workflow-standards plugin.

## Open question (what gates acceptance)

- **Q-07:** does any near-term deliverable actually have a UI? If none, this stays `Proposed`. Decide
  against the frontend-extenders inventory (#48). Tracked as an open decision on the strategy desk.

## Affects

Nothing today (Proposed). On acceptance: a stack-constraint rule/skill; any repo that adopts a UI.
