# Architecture playbooks

The matrix is in `SKILL.md`. These are the playbooks in full, plus what going wrong looks like in
each.

Every architecture is a shape the three layers take, so read each playbook's layer line first. Any
architecture that collapses the management layer (A, B, C) is available only when every collapse
condition in `SKILL.md` holds; D is the default shape for non-trivial work.

## A. Direct — just do it

**Layers: strategy only.** The task fits in a few tool calls, or the validation itself needs
delicate judgment. Delegation overhead would exceed the labor.

**Sign you chose wrong:** three files deep in mechanical edits. Stop and re-slice.

## B. Scouts — parallel read-only agents

**Layers: strategy + execution**, management collapsed. Fan out `scout` agents wherever the value
is the conclusion, not the traversal. Scouts default to haiku; override to sonnet only when the
question needs real cross-file synthesis.

Ask for concise evidence: `path:line`, commands run, uncertainties, and any stop condition hit.
Ask each scout a **question**, not a territory ("does any hook write outside CLAUDE_PROJECT_DIR"
beats "look at the hooks").

Asking questions is what makes the collapse legitimate: a scout that answers a question returns a
conclusion, so nothing raw climbs into the session's permanent context. A sweep wide enough that
the reports must be cross-read before they mean anything has failed that condition — put a
`manager` over the wave and take one synthesis back.

B is also the mandatory first phase of C, D, and E whenever the work-list does not exist yet. A
scout wave that returns an inventory is an input to sizing, not the end of the job.

**Sign you chose wrong:** the reports need a second pass because the questions were vague. Re-ask,
do not read the tree yourself.

## C. Flat fan-out — brief N scoped workers directly

**Layers: strategy + execution**, management collapsed into the strategist, who runs it personally.
This is D with a layer removed, so it is earned by satisfying every collapse condition, never
chosen as the cheaper option.

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
workers need the same file. Both mean the slicing was wrong, which is strategy work, not worker
work. Persistent escalation is also the signature of a collapse that should not have happened:
re-check the collapse conditions and promote the wave to D rather than absorbing the chatter here.

**Named variant — migrate-at-scale.** One mechanical transform repeated across many sites (a
rename, an API-signature change, a codemod) has its own playbook: site inventory and slicing, a
transform brief for cheap-model workers, what stays with the strategist, and the grep-zero +
full-suite + no-silent-caps gates that close it out. See `migrate-at-scale.md`.

## D. Manager-driven team — one `manager` drives a chain

**Layers: all three.** The default shape for non-trivial work, and mandatory for coupled work:
implement → wire → test → fix, where each step consumes the previous step's output.

Spawn **one `manager`** as the session's proxy with the full brief (`manager-brief.md`): objective,
DoD verbatim, constraints, worker-model guidance, evidence format, stop and escalation conditions.

The manager decomposes the chain, takes the judgment-heavy links itself, and spawns its own
`builder` workers for bounded links, steering them with SendMessage rather than re-briefing. The
manager is the **first-pass checker**: it verifies each worker's output before building the next
link, then assembles a **proof-of-completion package** (per-criterion evidence, commands plus
actual output).

While the team runs, answer escalations only, and **continue the manager with SendMessage, never
re-brief** — a re-brief discards the accumulated context that is most of what the manager cost.

When the manager reports done, **spot-check, then validate**. The manager catches worker errors
cheaply; the session catches the manager's blind spots. The classic failure is a plausible proof
package for a subtly wrong mechanism, which is exactly why this is layered verification rather
than a handoff.

**Why the layer pays** is the measured context argument in `SKILL.md` under "Why three layers
pay": management traffic compounds in the session's permanent prefix and is re-read at cache rates
forever, while a manager absorbs it into a context that gets thrown away `[cost]`.

**Sign you chose wrong:** the chain's links turn out to be independent *and* everything the wave
returns is a note rather than material. That was C, and the layer reconciled nothing. Independence
alone is not the signal, because a wide independent fan-out still floods the session.

## E. Phased crews — audit → fold-back → build → verify

**Layers: all three, with a manager per phase.** Architectural work with real unknowns. The phase
boundaries are hard, and the strategist stays deeply engaged at each one.

1. **Audit.** Findings reports only, no code changes. Usually a scout wave, sometimes reviewers on
   specific claims.
2. **Fold-back.** Amend the contract from what the audit found, before anyone builds against it.
   This is a strategy-floor item and the phase most often skipped: an audit that does not change
   the definition of done was either unnecessary or is being ignored.
3. **Build.** C owners for parallelizable subsystems, D managers for coupled ones.
4. **Verify.** Adversarial checks on high-impact claims, then the gates, run by the session.

Phase boundaries are the one place the strategist takes material rather than conclusions, because
amending a contract needs the finding itself. Keep that intake to the audit's findings report and
let the phase's manager hold everything behind it.

**Sign you chose wrong:** the audit produced no contract change and no re-slice. The work was
better understood than E assumes; drop to D.
