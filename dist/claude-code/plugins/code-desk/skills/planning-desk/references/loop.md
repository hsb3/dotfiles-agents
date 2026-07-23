# Mode: loop — run a multi-round planning session over a batch

The loop is how a batch of plans gets from "drafted" to "trustworthy". It's a foreman pattern: you
orchestrate crews and judge their output against the rubric; you don't write every plan yourself.
The payoff is concentrated where a plan rests on a shaky premise — the biggest quality gains come
from catching an overstated diagnosis or an infeasible recommendation that *read* as authoritative
until someone re-checked the source.

Read `references/plan.md` (the plan shape + rubric) and `_meta/plans/_config.md` (this project's
gates) before starting.

## Two operating principles

- **Run the review/verify agents on your strongest model tier.** Cheaper tiers have repeatedly
  returned right-citation/wrong-mechanism findings and missed cross-process bugs. Use the best model
  for the adversarial passes; a weaker tier is fine for mechanical drafting.
- **Parallelize every fan-out step** — one agent per item, not one sequential agent walking a list.
  For a cross-cutting batch, run one shared scout/research pass into a single fact-base first, then
  fan out the drafts off it so they don't each re-derive the same facts.

## The cycle

1. **Draft in parallel.** One agent per item, each scoped to its own `_meta/plans/<slug>/` folder,
   every claim grounded in cited `path:line` source. Each brief states its file-scope ownership;
   shared files (a single specs module, a Makefile) get a serialized chain of agents, not parallel
   writers. Run in the main tree (the desk may be invisible in a bare worktree).

2. **Review adversarially against the rubric.** One read-only verifier per plan, told to RE-DERIVE
   the load-bearing claims from source and find what is wrong, overstated, or missing — *not* to
   praise. Every "verified" claim is a hypothesis until re-checked. You (the foreman) personally
   re-check any finding that would change a plan's core recommendation — even a strong-tier reviewer
   gets line numbers and mechanisms wrong.

3. **Fix.** One write agent per plan, handed the *verified* facts so it doesn't re-derive the same
   error. Disjoint file scopes.

4. **Augment the rubric and re-review.** Each round teaches the rubric something — a blind spot that
   recurs becomes a new dimension (this is how G and H got added). Re-score; confirm the fixes landed
   and introduced no regressions.

5. **Apply the bodies + update state.** When an issue is being conformed alongside its plan, apply
   the rewritten body via **issue** mode's `gh issue edit` step and update the README + any triage
   record — re-verifying any scope-flipping claim against source yourself before it lands. **Gate the
   wave on `reconcile.py` exiting clean** at the start (trust the table before working off it) and
   the end (catch rows left stale). When it flags an ACTIVE plan whose issue CLOSED, that's a human
   call — reopen the issue if acceptance criteria are unmet, or archive the plan if genuinely done.

## Gates over green reports

The run isn't done when the agents say done; it's done when the repo's own hard gates pass and the
desk reconciles. Before declaring a wave complete, run from the main tree:

- `reconcile.py` — clean (README ↔ live issues ↔ folders agree)
- `conformance.py` — every issue touched in the wave conforms
- `sync-bodies.py` — staged bodies match GitHub (or you deliberately haven't pushed yet)
- the project's own test/lint gate from `_config.md`, for any plan that also shipped code

A gate that can fail loudly is worth more than any number of agent self-reports.

## Scope discipline

- **No silent caps.** If a wave bounds coverage (verify top-N of M, sample K files), say what was
  dropped and carry it to the backlog — silent truncation reads as "covered everything" when it wasn't.
- **Handoff notes are the inter-crew API.** Each builder records what changed, why, and what was
  deliberately deferred; the deferred lists are the authoritative backlog after the run.
- **Budget a reconciliation pass.** Parallel crews always leave drift (stale tests, rename fallout,
  mirrors out of sync). Collect the punch list from the handoffs and give it to ONE serial agent —
  don't fan out the cleanup.
