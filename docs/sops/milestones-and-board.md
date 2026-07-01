---
title: SOP — milestones and the project board
status: active
created: 2026-07-01
---

# SOP — establishing & managing milestones and the project board

*How a project's work state is made visible and steered: one project board, one set of fields,
many views, plus milestones for real date commitments. Harness-neutral — the board is a GitHub
Project (v2) driven through `gh`/GraphQL, readable and writable by any agent.*

Delivered by the **`github-project-board`** extender (setup + bulk changes), with
**`board-reporting`** (status readouts) and **`board-triage`** (the recurring cadence).

## Principles

- **One project, many views — not many boards.** Create a single Project (v2) with one set of
  fields over one item set, then slice it into multiple *views* (timeline, priority, by-area,
  current iteration). Same items, different lenses; change a field once and every view updates.
- **The board is the single source of truth for work state.** What is being worked on, in what
  order, and why, lives on the board — not in a doc, a sheet, or an agent's memory. Planning desks
  hold detail; the board holds state.
- **Fields carry state; don't derive what you can store.** A signal you filter or sort on is a
  field (Status, Iteration, Gate), not something re-computed from labels or titles each time.
- **Readiness is a gate, not a count.** "What blocks the next promise?" is answered by a
  `gate:<promise>` signal, separately from the raw backlog size. An empty gate means the promise is
  safe to make — check the gate, not the issue count.

## The field model (baseline)

Create these once; add only what a real view needs.

| Field | Type | Purpose |
| --- | --- | --- |
| **Status** | single-select | `Backlog · Active · Review · Done` — the day-to-day lane. |
| **Iteration** | iteration | timeline / current-cycle slicing (GraphQL-only to create; see scriptability). |
| **Gate** | single-select or label | readiness — `gate:<promise>`; drives "safe to promise" views. |
| **Area** / **Priority** | single-select | optional lenses; add when a view needs them. |

> **Editing single-select options safely:** re-pass existing option ids when updating a field, or
> items on removed options are orphaned. Renames preserve items; deletes do not.

## Milestones

- **One milestone per phase or promise level.** Use them to group deliverables, not to schedule.
- **No due dates by default.** Add a date only for a genuine external commitment, and record it as
  a *constraint*, not a plan. Deliverables and acceptance criteria drive sequencing; dates don't.

## Dependencies & structure

- **Epics as parent issues; native sub-issues** for their pieces; **blocked-by** links for ordering.
- Let the parent/child + blocked-by graph express sequence — don't encode order in titles or a
  separate doc. Linear solo work doesn't need the epic structure; reach for it when work parallelizes.

## What is scriptable vs UI-only

The common myth is that option edits and iteration fields are UI-only. They are **not**. Genuinely
UI-only is narrow: **views and workflows.** Everything else an agent can do via `gh`/GraphQL —
create the project and fields, create/edit iteration buckets, add/rename/reorder single-select
options, set field values, add items, wire sub-issues and blocked-by. Script the item-and-field
work; create the views and automation once in the UI.

## Cadence

Run a **recurring triage** (weekly is typical): groom the backlog, set Status/Iteration/Gate on new
items, re-check blocked-by chains, and cut a status readout from the board's own state. The readout
is derived from the board, never maintained in parallel.

## Setup checklist

1. Create the project; add the **Status** field (`Backlog · Active · Review · Done`).
2. Add **Iteration** (GraphQL) if the project needs a timeline; add **Gate** for readiness.
3. Create the **views** (UI): a board by Status, a table by Iteration, a "blocked / ready" gate view.
4. Create **milestones** — one per phase/promise, no due dates unless a real commitment.
5. Seed items, set field values, wire sub-issue + blocked-by dependencies (scripted).
6. Establish the triage cadence and the readout it produces.

## Harness portability

`gh` + GraphQL are harness-neutral CLIs; nothing here depends on a specific coding agent. The
`github-project-board` extender renders into every target harness, so the same board procedure runs
identically under Claude Code, opencode, or any agent that can shell out to `gh`.
