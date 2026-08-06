# Architecture playbooks

The matrix is in `SKILL.md`. These are the five playbooks in full, plus what going wrong looks
like in each.

## A. Direct — just do it

The task fits in a few tool calls, or the validation itself needs delicate judgment. Delegation
overhead would exceed the labor.

**Sign you chose wrong:** three files deep in mechanical edits. Stop and re-slice.

## B. Scouts — parallel read-only agents

Fan out `scout` agents wherever the value is the conclusion, not the traversal. Scouts default to
haiku; override to sonnet only when the question needs real cross-file synthesis.

Ask for concise evidence: `path:line`, commands run, uncertainties, and any stop condition hit.
Ask each scout a **question**, not a territory ("does any hook write outside CLAUDE_PROJECT_DIR"
beats "look at the hooks").

B is also the mandatory first phase of C, D, and E whenever the work-list does not exist yet. A
scout wave that returns an inventory is an input to sizing, not the end of the job.

**Sign you chose wrong:** the reports need a second pass because the questions were vague. Re-ask,
do not read the tree yourself.

## C. Flat fan-out — brief N scoped workers directly

The session is its own lead. Parallelizable work with disjoint file ownership.

1. **Write the plan**: deliverables, DoD per slice, and the parallelism map. Externalize it (plan
   doc or task list) so it survives compaction.
2. **One slice = one owner = disjoint file scope.** Shared files get a *serialized chain*, never
   parallel writers. State file ownership in every brief, including which config is read-only.
3. **Pick a model per slice at dispatch.** `builder` on its sonnet default for bounded
   well-specified edits; `model: opus` where being wrong is expensive to unwind. For
   audit-and-fix sweeps, split by role: `scout` agents read everything and report violations,
   `builder` fixers touch only the violators. Paying edit-tier rates for read-only scanning is
   the most common silent overspend.
4. **Require a handoff note per worker**: what changed, why, the verification commands run with
   their actual output, the failure observed before each behavior was implemented, what was
   deferred, what other slices must know.
5. **Budget ONE serial reconciliation pass.** Parallel work always leaves drift (stale tests,
   rename fallout, two owners solving the same sub-problem differently). Give the punch list to a
   single agent; never fan out cleanup. Where slices produce comparable observable output, make
   the reconciliation a **differential** — diff the outputs, do not read the diffs
   (`verification.md`).
6. **Validate personally** against the DoD, running the gates yourself.

**Sign you chose wrong:** workers keep escalating for decisions the brief should have made, or two
workers need the same file. Both mean the slicing was wrong, which is foreman work, not worker
work.

**Named variant — migrate-at-scale.** One mechanical transform repeated across many sites (a
rename, an API-signature change, a codemod) has its own playbook: site inventory and slicing, a
transform brief for cheap-model workers, what stays with the foreman, and the grep-zero +
full-suite + no-silent-caps gates that close it out. See `migrate-at-scale.md`.

## D. Lead-driven team — one `lead` drives a coupled chain

Coupled work: implement → wire → test → fix, where each step consumes the previous step's output.

Spawn **one `lead`** as the session's proxy with the full brief (`lead-brief.md`): objective, DoD
verbatim, constraints, worker-model guidance, evidence format, stop and escalation conditions.

The lead decomposes the chain, takes the judgment-heavy links itself, and spawns its own `builder`
workers for bounded links, steering them with SendMessage rather than re-briefing. The lead is the
**first-pass checker**: it verifies each worker's output before building the next link, then
assembles a **proof-of-completion package** (per-criterion evidence, commands plus actual output).

While the team runs, answer escalations only, and **continue the lead with SendMessage, never
re-brief** — a re-brief discards the accumulated context that is most of what the lead cost.

When the lead reports done, **spot-check, then validate**. The lead catches worker errors cheaply;
the session catches the lead's blind spots. The classic failure is a plausible proof package for a
subtly wrong mechanism, which is exactly why this is layered verification rather than a handoff.

**Why a lead at all:** management traffic compounds. Every brief and report in the main session
lands in the ever-growing prefix and is re-read at cache rates on every subsequent turn. The lead
absorbs that chatter into a disposable context and hands back one package. Note that at `standard`
effort a lead is the *same tier* as the session, so D buys context absorption, not tier arbitrage.

**Sign you chose wrong:** the lead's links turn out to be independent. That was C, and you paid
for a layer that reconciled nothing.

## E. Phased crews — audit → fold-back → build → verify

Architectural work with real unknowns. The phase boundaries are hard, and the session stays deeply
engaged at each one.

1. **Audit.** Findings reports only, no code changes. Usually a scout wave, sometimes reviewers on
   specific claims.
2. **Fold-back.** Amend the contract from what the audit found, before anyone builds against it.
   This is floor item 6 and the phase most often skipped: an audit that does not change the
   definition of done was either unnecessary or is being ignored.
3. **Build.** C owners for parallelizable subsystems, D leads for coupled ones.
4. **Verify.** Adversarial checks on high-impact claims, then the gates, run by the session.

**Sign you chose wrong:** the audit produced no contract change and no re-slice. The work was
better understood than E assumes; drop to C or D.
