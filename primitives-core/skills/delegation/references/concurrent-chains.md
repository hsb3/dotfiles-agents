# Concurrent Chains — several architecture-D managers in flight at once

Architecture D drives one coupled chain; E sequences phases behind hard boundaries. Neither says
how many chains the strategy layer may have running at the same time, and the default reading of
both is one. A work-list whose entries do not depend on each other, worked one chain at a time,
turns the strategist into a dispatch → wait → verify → merge loop for the length of the list — an
evening of four independent tasks has been spent that way, with the only real parallelism a
read-only scout running alongside one crew `[field]`.

This is the shape D takes when the work-list has several such entries. Nothing inside a chain
changes: each one is still D in full, with its own manager, its own DoD, and its own package.

## When chains may run concurrently

The test is the one `SKILL.md` already applies to collapsing management, used one level up:
**the tasks are independent in outcome, not merely in file ownership.** No chain's result changes
another chain's brief. A chain whose DoD would have to be rewritten once a sibling lands is
coupled work wearing two branch names — sequence it, or make it one chain.

Disjoint file ownership is necessary and not sufficient. Two chains that touch no common source
file still collide on whatever a gate makes single-writer.

Board bookkeeping can hide the opportunity: a session that claims one tracker task at a time has a
work-list of one by construction. That is an artifact of how the work is recorded, not a property
of the work.

## The cap, and what bounds it

**Two to three concurrent chains** `[untested]`. The bound is not machine capacity or dispatch
limits — it is the strategist's own verification capacity. Every returning chain costs a
spot-check of a criterion or two plus a gate run, and those land in the one context that never
resets. Chains also return whenever they return, so packages arrive interleaved with each other
and with escalations from chains still running.

That number is a working default reasoned from the argument above, not a measurement. Take fewer
when two packages would be hard to tell apart on inspection, and never take more merely because
the dispatch tool would allow it.

## Isolation

Each chain gets its own worktree and its own branch. This is the case `dispatch-knobs.md` reserves
worktree isolation for: concurrent chains sharing one working copy are parallel writers to it
whatever their file scopes say.

The documented caveat binds harder here than anywhere else. **A worktree is a clean checkout of a
ref, so the session's uncommitted and untracked work does not exist inside it.** Commit whatever
the chains must build on before the first dispatch, or leave that one chain un-isolated and give
up concurrency for it.

## Dispatch-time contracts

Settle all three of these **before the first dispatch**, and write each into the brief of the chain
it binds `[untested]`:

1. **Merge order.** Which chain integrates first, second, third. Finishing order is arbitrary and
   cannot serve as the contract.
2. **Ownership of every gated shared resource.** Any single file a gate forces every source-
   touching change to write: a version field, a changelog, a lockfile, a generated artifact, a
   manifest or registry listing. Either split it by assignment (this chain takes the next version,
   that one the version after) or name a single owner and tell the others to leave it alone and
   report.
3. **The rebase-or-reorder duty.** Name it on the second-to-merge chain: after its predecessor
   lands, rebase onto it and re-run the gates before merging, or hand the work back for the
   strategist to reorder. Unassigned, it lands on the strategist at merge time for every chain.

**What skipping step 2 costs.** A CI gate requires every source-touching PR to bump the package
version. Chains dispatched without an assignment each bump to the same next version. Each passes
CI alone, because on its own branch the gate is satisfied — then they fail one after another as
each predecessor merges and takes that version. The collision is discovered at merge time,
serially, by the strategist, which is the loop the concurrency was bought to escape `[field]`.

Inside a chain, the manager runs the same reasoning over its own workers: disjoint builder slices
go out together, review pipelines behind whichever returns first (`manager-brief.md`).

## What does not parallelise

- Chains that share a gated resource with no assignable split. One writer, or one chain.
- A chain whose definition of done can only be evaluated after a sibling has landed. That is a
  dependency, so it is sequencing — architecture E, or one longer chain.
- Any wave where the strategist cannot verify two returning packages without conflating them.
  Verification is the cap; a package that cannot be checked on its own terms was dispatched too
  wide.
- Anything the work-list has not actually sliced yet. Discovery is a scout wave first, then decide
  again — concurrency multiplies a bad slice.

## The failure mode this replaces

The strategist as a serial merge-and-wait loop: one task claimed, one crew dispatched, the session
idle until it returns, verified, merged, next task claimed. It looks disciplined and it costs the
whole work-list in sequence. Independence in outcome is the permission to stop doing that.
