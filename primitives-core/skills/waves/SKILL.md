---
name: waves
description: >
  Drive a repo's open-issue backlog to closed through triage, wave planning, and isolated agent
  crews — the full loop: refresh a pinned triage issue, group buildable issues into branch-sized
  waves, launch worktree-isolated teams via the foreman skill, verify and merge each PR in order,
  reconcile, and externalize. Use when the user says "work through the waves", "launch isolated
  teams to resolve/close the issues", "run the backlog", "triage and execute", points at the
  pinned triage issue, or asks to plan development branches around open issues. Use "/waves init"
  to create the pinned triage issue in a repo that lacks one. Requires a GitHub repo with issues;
  composes the foreman skill (execution) and the handoff skill (boundaries).
---

# Waves

Run one session as a **backlog-execution loop**: orient from the handoff and the pinned triage
issue, refresh the triage, plan issues into waves, launch isolated crews, personally verify and
merge each wave, reconcile, and externalize — so the owner's only inputs are the launch prompt
and the decisions that are genuinely theirs.

This skill is the *campaign* layer. The **foreman** skill governs each wave's delegation
architecture; the **handoff** skill closes the session. Waves adds what neither has: the pinned
triage issue as the living plan, the wave-shaping rules, the merge queue, and the
end-of-run externalization contract.

## The two artifacts

1. **The handoff file** (`_meta/HANDOFF.md` per the handoff skill) — session bridge; carries
   owner rulings and gotchas.
2. **The pinned triage issue** — a curated, ranked view of the open backlog plus the current
   delivery plan. Pinned so it is the first thing a session or collaborator sees. **The issue
   list / labels / milestones are the source of truth; this body is a view** — if they disagree,
   fix the body. It is maintained **by editing the issue body, never by commits**, precisely so
   refreshes never touch the repo history.

## Phase 0 — Orient (and confirm authority)

- Read the handoff, then the triage issue. If no triage issue exists, offer `/waves init` (below).
- Confirm once, at the start, that the session has authority to **commit, push, open PRs, and
  merge** for this run. If the user's launch prompt already says "resolve/close all issues as
  planned", that is the grant — don't re-ask per wave.

## Phase 1 — Triage refresh

Reconcile the view with the truth before planning anything:

```sh
gh issue list --state open --limit 300 \
  --json number,title,labels,milestone \
  --jq '.[] | "\(.number)\t\(.title)\t[\([.labels[].name]|join(","))]\t\(.milestone.title // "-")"' | sort -rn
```

- Close what's actually done (epics whose children all shipped); merge green dependabot PRs.
- File issues for anything known-but-untracked (deferred items from prior runs, findings).
  Tracked-in-an-issue is the bar for "will not be forgotten".
- **Split the backlog into two queues:** *buildable* (crews can close it) and **owner-gated**
  (needs a ruling, sign-off, or missing decision). Crews never pick up owner-gated items — a
  crew "resolving" an undecided question is the workflow's worst failure mode. If a cited
  decision can't be found in the repo, that's a triage find: file it as an owner-gated issue.
- Rank by: `gate:*` labels → milestone → epic/sub-issue links → owner rulings in the handoff.

## Phase 2 — Wave planning

Group the buildable queue into waves. **One wave = one branch = one PR = one crew.** Shaping
rules, in priority order:

1. **Minimize PR count, but keep each PR reasonably sized** — batch small related issues into
   one wave; never let a wave grow past what one review can hold.
2. **Disjoint file surfaces run in parallel; overlapping surfaces get sequenced** — waves that
   touch the same files are ordered, not concurrent (or one wave absorbs the other).
3. **Dependencies sequence waves** — an issue consuming another's output goes in a later wave.
4. **Declare the merge order now**, at plan time — collisions get resolved against a known
   queue, not ad hoc.

**Write the plan into the triage issue body as "Delivery plan vN" before launching** — a table
of `wave | branch | issues resolved | gate`, plus the owner decision queue. It goes in the
**Delivery history** block at the bottom of the body: expanded while `PLANNED`, collapsed into
`<details>` on `EXECUTED` — never above the open sections. The plan must survive compaction and
be visible to the owner without asking the session.

## Phase 3 — Launch (foreman executes)

Invoke the **foreman** skill for architecture and briefs. The shape that has worked: one
worktree-isolated crew per parallel wave — typically a `lead` (with its own builders) for
coupled waves, flat `builder` fan-out for bounded ones. Non-negotiables regardless of
architecture:

- Every brief states the wave's **file ownership** and its **issue list with acceptance
  criteria** ("closes #N when \<verifiable check\>").
- Crews build and open the PR; **all git mutation on main and every merge is reserved to the
  session.**
- Predictable cross-wave collisions (a shared Makefile, CI config) are named in the briefs with
  the resolution rule (usually: later-merging wave rebases and takes the union).

## Phase 4 — Verify and merge, in order

For each wave, as crews report back — the session, personally:

1. **Verify the branch against the plan**: diff touches only owned files; run the repo's gates
   (`make check` / `make test` / `make verify` or equivalents) yourself; a crew's green report
   is a hypothesis.
2. **Disposition every review-bot finding**: address blocking concerns *and* nits, or record
   why not; commit/push; **re-review; repeat until no concerns remain and CI passes.** Then
   merge — in the declared order, closing issues via PR keywords.
3. A finding you can fix faster than you can brief, fix yourself; anything larger goes back to
   the wave's crew via SendMessage (never a re-brief).

## Phase 5 — Reconcile and prove

- **One serial reconciliation pass** over the punch list from crew handoff notes: CHANGELOG,
  stale counts/refs in docs, CLAUDE.md tables. Never fan out cleanup.
- **Run the full gate battery bare on the final union of main** — merging N individually-green
  branches does not prove the union. Watch CI to green on the tip; the run is not done until
  it is.

## Phase 6 — Externalize (the run isn't done without this)

- File issues for every deferred item and new finding from the run.
- **Update the triage issue**: mark the delivery plan **EXECUTED** with the actual PR table,
  refresh the ranking and date — then **move the plan below the open sections** into the
  delivery-history block and collapse it in `<details>`. Position is the reader's only
  done/outstanding cue; an executed plan left on top reads as current standing. Collapse
  prior executed plans to one-line pointers.
- **Present the owner decision queue as one batch**, not a dribble — options + a
  recommendation per item. For a multi-item queue, use the **owner-signoff** skill if
  installed (local HTML form; answers land in `_meta/signoff/<date>-<topic>/`); record
  rulings back onto the issues and the handoff, and execute any that unblock same-session
  work.
- Run **/handoff**; prune worktrees and branches (`git worktree prune`).
- Close with session totals: PRs merged, issues closed, issues filed, what remains and *why*
  (owner-gated / parked / next wave).

## `/waves init` — create the triage issue

When the repo has issues but no pinned triage issue, create one titled
`meta: triaged open-issue backlog (living list)`, pin it, and seed the body:

```markdown
_A curated, ranked view of the open backlog — pinned so it's the first thing a session sees.
**The issue list / milestones / labels are the source of truth; this body is a view.** Maintained
by editing this issue (no repo commits). Excludes itself and dependabot PRs._

**Last refreshed: YYYY-MM-DD** · N open issues at refresh time

## Now — actionable, unblocked
| # | Title | State | Blocked by |

## Milestone — what actually remains
## Backlog — no milestone
## On hold — parked by owner ruling, don't pick up
## Decision gaps — the owner queue

# Delivery history — shipped, provenance only

## Delivery plan vN — PLANNED | EXECUTED YYYY-MM-DD
| Wave | Branch | PR | Resolves | Gate |

## Maintenance protocol
- **Open work leads; executed plans sit last, collapsed.** Never let an EXECUTED plan sit above
  the open backlog — position is the only done/outstanding cue a reader gets.
- **Every issue from the inventory appears exactly once** in the open-work sections above, with
  its state explicit — outstanding-or-not must be answerable at a glance, never inferred.
- Refresh at session boundaries alongside the handoff pass, or whenever issues change in bulk —
  a stale ranked view is worse than none.
- Regenerate the inventory (gh issue list …), re-rank, edit this body, bump the refresh date.
- Ranking inputs: gate:* labels → milestone → epic/sub-issue links → owner rulings in the handoff.
- Keep pinned; it lives here (not a tracked file) so refreshes never touch commit history.
```

Record the issue number in the handoff's map section so future sessions find it by pointer,
not by search.

## The compact launch prompt this replaces

A session with this skill should need no more than:

> review handoff and the triage issue · update the triage · launch isolated teams to
> resolve/close all issues as planned, leveraging the foreman skill

Everything else above is what that sentence expands to.
