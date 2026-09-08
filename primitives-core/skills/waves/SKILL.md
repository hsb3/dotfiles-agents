---
name: waves
description: >
  Drive a project's open backlog to closed through triage, wave planning, and isolated agent
  crews — the full loop: refresh the triage view, group buildable items into branch-sized waves,
  launch worktree-isolated teams via the delegation skill, verify and land each wave in order,
  reconcile, and externalize. Tracker-agnostic: the backlog can live on GitHub issues, a kata
  board or any tracker that can list open items and hold a written plan — see
  the tracker bindings under references/. Use when the user says "work through the waves",
  "launch isolated teams to resolve/close the issues", "run the backlog", "triage and execute",
  points at the triage view, or asks to plan development branches around open items. Use
  "/waves init" to create the triage view in a project that lacks one. Composes the delegation
  skill (execution) and the handoff skill (boundaries).
---

# Waves

Run one session as a **backlog-execution loop**: orient from the handoff and the triage view,
refresh the triage, plan items into waves, launch isolated crews, personally verify and land
each wave, reconcile, and externalize — so the owner's only inputs are the launch prompt and
the decisions that are genuinely theirs.

This skill is the *campaign* layer. The **delegation** skill governs each wave's delegation
architecture; the **handoff** skill closes the session. Waves adds what neither has: the triage
view as the living plan, the wave-shaping rules, the landing queue, and the end-of-run
externalization contract.

## The two artifacts

1. **The handoff** (per the handoff skill — a file in the repo, or an external tracker item when
   the project routes it there) — session bridge; carries owner rulings and gotchas.
2. **The triage view** — a curated, ranked view of the open backlog plus the current delivery
   plan, held wherever the tracker binding says. **The inventory is the source of truth; this is
   a view** — if they disagree, fix the view.

## The backlog seam

Waves needs three operations from whatever tracks the work. Everything else in this skill is
tracker-agnostic.

| Seam | What it must do |
|---|---|
| **Inventory** | List every open item with id, title, state, and the ranking signals — labels, priority, milestone or epic, blocked-by. |
| **Triage view** | Hold the ranked backlog and the delivery plan where the owner reads it without asking the session. Durable, fully rewritable, and **off commit history**. |
| **Landing a wave** | Verify and land a wave's code, then close its items with a link back to what landed them. |

**Bind the seam before Phase 0.** Read the binding for the tracker in play:

- `references/tracker-github.md` — issues, a pinned issue body, PRs
- `references/tracker-kata.md` — the kata CLI

For a tracker with no binding file, name the three operations explicitly in your first message
and confirm them with the owner before triaging. A campaign run against a seam nobody wrote
down is how a wave closes the wrong items.

**Tracker and forge are separate.** Only GitHub collapses them. Elsewhere the backlog lives in
one system and the code lands in another, which splits two things GitHub fuses: closing an item
and landing its code become separate steps, and there is no PR keyword to do it for you. Say
which system is which at Phase 0, and never assume closing a PR closed a backlog item.

## Phase 0 — Orient (and confirm authority)

- Read the handoff, then the triage view. If none exists, offer `/waves init` (below).
- Confirm once, at the start, that the session has authority to **commit, push, open PRs, and
  merge** for this run. If the user's launch prompt already says "resolve/close all issues as
  planned", that is the grant — don't re-ask per wave.
- Default scope is the items the triage view already ranks as ready this run, never the whole
  open backlog: a bare "run the waves" plans only that ranked set into crews. Never infer, from
  a general request, that the whole backlog should go into crews in one run — widen only on
  explicit say-so.
- **Check for a live coordination signal on this branch before planning anything.** Read what
  the session start surfaced about other recent sessions here, and record the trunk tip
  (`git rev-parse HEAD`) that the plan is being built on. A concurrent session moving the trunk
  underneath a running campaign is a real failure mode, not a hypothetical. If another session
  is live on the branch, settle the landing order with it — or with the owner — before launching
  a single crew; two campaigns merging into one trunk unaware of each other is how a landing
  gets clobbered.
  <!-- harness:claude-code -->
  The `branch-activity-surfacer` hook does the detecting: it warns at session start when another
  session recorded a start on this repo and branch, or when the tip moved since the last one, and
  names the commits and the merged PR that moved it.
  <!-- /harness -->

## Phase 1 — Triage refresh

Reconcile the view with the truth before planning anything. Run the **Inventory** operation from
the tracker binding, then:

- Close what's actually done (epics whose children all shipped); merge green dependency-bump PRs.
- Route anything known-but-untracked (deferred items from prior runs, findings, a previous
  run's hardening list) through Phase 6's fold order before filing it — a line a previous run
  deliberately left unfiled is not intake.
- **Split the backlog into two queues:** *buildable* (crews can close it) and **owner-gated**
  (needs a ruling, sign-off, or missing decision). Crews never pick up owner-gated items — a
  crew "resolving" an undecided question is the workflow's worst failure mode. If a cited
  decision can't be found in the repo, that's a triage find: comment it onto the open item that
  cites it, or file it as an owner-gated item when none does.
- Rank by the binding's ranking chain, then by owner rulings in the handoff.

The inventory is the source of truth and the triage view is a view of it. When they disagree,
fix the view.

## Phase 2 — Wave planning

Group the buildable queue into waves. **One wave = one branch = one landing = one crew.**
Shaping rules, in priority order:

1. **Minimize landings, but keep each one reasonably sized** — batch small related items into
   one wave; never let a wave grow past what one review can hold.
2. **Disjoint file surfaces run in parallel; overlapping surfaces get sequenced** — waves that
   touch the same files are ordered, not concurrent (or one wave absorbs the other).
3. **Dependencies sequence waves** — an item consuming another's output goes in a later wave.
   Where the tracker models blocked-by, read it; where it doesn't, derive it and write it down.
4. **Declare the landing order now**, at plan time — collisions get resolved against a known
   queue, not ad hoc.

**Write the plan into the triage view as "Delivery plan vN" before launching** — a table of
`wave | branch | items resolved | gate`, plus the owner decision queue. It goes in the
**Delivery history** block at the bottom: expanded while `PLANNED`, collapsed on `EXECUTED` —
never above the open sections. The plan must survive compaction and be visible to the owner
without asking the session.

## Phase 3 — Launch (delegation executes)

Invoke the **delegation** skill for architecture and briefs. The shape that has worked: one
worktree-isolated crew per parallel wave — typically one `manager` (with its own builders) for
coupled waves, flat `builder` fan-out for bounded ones. Non-negotiables regardless of
architecture:

- Every brief states the wave's **file ownership** and its **item list with acceptance
  criteria** ("closes \<id\> when \<verifiable check\>").
- Crews build and open the landing; **all git mutation on the trunk and every merge is reserved
  to the session.**
- Predictable cross-wave collisions (a shared Makefile, CI config) are named in the briefs with
  the resolution rule (usually: later-landing wave rebases and takes the union).

## Phase 4 — Verify and land, in order

For each wave, as crews report back — the session, personally:

1. **Verify the branch against the plan**: diff touches only owned files; run the repo's gates
   (`make check` / `make test` / `make verify` or equivalents) yourself; a crew's green report
   is a hypothesis.
2. **Disposition every review finding**: address blocking concerns *and* nits, or record why
   not; commit/push; **re-review; repeat until no concerns remain and CI passes.** Then land —
   in the declared order.
3. **Close the wave's items** per the binding's landing operation, each with a pointer to what
   landed it. Where the tracker cannot close from the forge, closing is a separate step you owe
   at the end of the wave, not the end of the run. Record the wave's closed count against what it
   filed as you land it — the attribution is not recoverable later.
4. A finding you can fix faster than you can brief, fix yourself; anything larger goes back to
   the wave's crew as an amendment to the crew that is still live — never a re-brief.

<!-- harness:claude-code -->
Send that amendment with `SendMessage` to the running manager.
<!-- /harness -->

## Phase 5 — Reconcile and prove

- **One serial reconciliation pass** over the punch list from crew handoff notes: CHANGELOG,
  stale counts/refs in docs, the repo's standing agent-instructions file. Never fan out cleanup.
- **Run the full gate battery bare on the final union of the trunk** — landing N individually
  green branches does not prove the union. Watch CI to green on the tip; the run is not done
  until it is.

## Phase 6 — Externalize (the run isn't done without this)

- **Dispose of the undisposed remainder by the fold order, filing last.** Each wave's proof
  package says what its manager already fixed, commented, or filed; that is placed, and filing it
  again is the double this order prevents. For the rest: a sibling site of what a wave fixed goes
  into that wave, a finding that belongs to an open item becomes a comment on it, one with no home
  rides the wave's hardening list, and only what none of those hold is filed, with the reason.
  Never file a draft for someone else to finish. Tracked is still the bar for "will not be
  forgotten" — a new item is the last rung of it, not the first.
- **Update the triage view**: mark the delivery plan **EXECUTED** with the actual landing table,
  refresh the ranking and date — then **move the plan below the open sections** into the
  delivery-history block and collapse it. Position is the reader's only done/outstanding cue; an
  executed plan left on top reads as current standing. Collapse prior executed plans to one-line
  pointers.
- **Reconcile the view against the inventory one last time.** Every item the run closed should
  be closed in the tracker, not just in the view — on a split tracker/forge this is where a
  missed close surfaces.
- **Present the owner decision queue as one batch**, not a dribble — options + a recommendation
  per item. For a multi-item queue, use the **owner-signoff** skill if installed (local HTML
  form); record rulings back onto the items and the handoff, and execute any that unblock
  same-session work.
- Run the **`handoff`** skill; prune worktrees and branches (`git worktree prune`).

<!-- harness:claude-code -->
There is no `/handoff` command: in Claude Code a command silently shadows a same-named skill in
the same plugin, so atelier ships the skill only (`primitives-core/commands/README.md`).
<!-- /harness -->
- Close with session totals: waves landed, closed against filed per wave plus the run total, what
  remains and *why* (owner-gated / parked / next wave). **Filed over closed is the signal** — a
  wave above 1.0 grew the backlog it was run to shrink, so name what drove it.

## `/waves init` — create the triage view

When the project has a backlog but no triage view, create one. The binding for the tracker in
play carries the concrete mechanism and a seed template; the contract it must satisfy is the
same everywhere:

- **A curated, ranked view of the open backlog**, stating in its own header that the inventory
  is the source of truth and this is a view of it.
- **Sections for the open work** — actionable-and-unblocked, what remains against a milestone
  or epic, unscheduled backlog, parked-by-owner-ruling, and the owner decision queue.
- **A delivery-history block at the bottom** holding delivery plans, collapsed once executed.
- **A maintenance protocol** in the artifact itself: open work leads and executed plans sit last;
  every item from the inventory appears exactly once with its state explicit; refresh at session
  boundaries or whenever the backlog changes in bulk.
- **A refresh date and the item count at refresh time**, so staleness is visible.
- It lives in the tracker, never as a tracked file — refreshes must not touch commit history.

Record the view's id in the handoff's map section so future sessions find it by pointer, not by
search.

## The compact launch prompt this replaces

A session with this skill should need no more than:

> review handoff and the triage view · update the triage · launch isolated teams to
> resolve/close all items as planned, leveraging the delegation skill

Everything else above is what that sentence expands to.
