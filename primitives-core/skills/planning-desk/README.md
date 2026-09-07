# planning-desk

Stands up and runs a source-grounded planning desk under `_meta/plans/`: deep build plans driven
through a multi-round draft -> review -> fix -> reconcile loop, over a tracker read through a
pluggable adapter, with three analysis scripts (conformance, coverage, reconcile) that can gate a
wave. Every claim is grounded in cited source, and plans state deliverables, acceptance criteria,
and parallelism — never timelines.

## When it triggers

Use it to plan a feature or epic before building, run a planning or backlog-grooming session,
organize work under `_meta/plans/`, audit plan/tracker drift, or set the desk up in a new repo —
even phrased loosely as "plan this out", "groom the backlog", or "get this repo's planning
organized".

It also carries two standing standards the desk cites (`references/entry-forms-and-milestones.md`):
the queue-entry forms a unit of work takes to enter a backlog or an incubator, and the ordered
`P<n> — <promise>` milestone and `gate:<promise>` label vocabulary a board speaks — the latter
written as one board's worked example, not a claim that every tracker has milestones.

**Writing the body of a tracked work item is not this skill's job.** Title, acceptance criteria,
thresholds, and scope belong to `task-authoring`. A desk folder holds `plan.md` and nothing else:
the tracked item is the contract, the plan is the build detail.

## The decision behind the current shape

The desk used to be explicitly GitHub-issue-backed and carried an issue-authoring mode. That mode
duplicated `task-authoring` and is deleted. The discipline it sat next to — `plan.md`, the review
loop, the governance scripts — is kept and now runs over a tracker adapter, Kata first.

- **The `gh` path is removed, not kept as a second adapter.** The authoring mode carried most of
  the GitHub coupling, and a second adapter with no live user doubles the surface for no present
  need. `references/adapters/contract.md` is the extension point: a `gh` adapter can be written
  from it when someone actually needs one.
- **Seven scripts became three, plus one adapter and a loader.** `sync-bodies.py` was pure
  issue-authoring machinery. `deps-suggest.py` proposed GitHub-native dependency edges, which a
  tracker has first-class. `evidence-audit.py` backstopped closing without evidence, which a
  tracker requires. `sequence.py` computed readiness and "what's next", which the tracker computes
  itself and which the `board-triage` skill prioritizes. `_repo.py` derived a GitHub repo and had
  no callers left. The generic issue templates the desk used to seed went with them.

## What it needs

The scripts are stdlib-only Python with no install step. The govern mode additionally needs
the tracker's own CLI on `PATH` and already authenticated — the adapter shells out to it,
exports a snapshot, and the three analysis scripts read that snapshot rather than the network.
Plan mode works with no tracker at all.

Every analysis script is a read-only view. The single write path is a changeset the adapter
applies, and it dry-runs by default; a plan folder whose tracking ref parses ambiguously is
withheld from that changeset rather than guessed at, so an unclear desk never writes to the
tracker.

Board-facing conventions — the issue entry forms, the milestone promise levels, and the
GitHub Projects field set the desk maps onto — live in
`references/entry-forms-and-milestones.md`.

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships in the `mise-en-place` bundle.
