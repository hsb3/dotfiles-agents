---
name: delegation
description: >
  How to split a substantial task across agents: the three-layer model, the architecture matrix,
  effort and model-tier calibration, brief rules, and the never-delegated floor. Use when sizing
  a feature build, refactor, migration, audit, or multi-file fix; when the work arrived as a
  goal ("clean this up", "get it published") rather than as a list of slices; when crews, teams,
  managers, subagents, or waves come up; when token cost on a big job is a worry; or when a
  session has been editing files itself for a long stretch without delegating.
---

# Delegation

Delegated work runs on three layers: **strategy**, **management**, **execution**. Each has work
that is irreducibly its own, a context it must carry and a context it must never be handed, and
things it must never do. Three layers is the default for anything non-trivial. Collapsing one is
an exception that has to be justified against the conditions below, not a tiebreak.

Premium session tokens buy decomposition, judgment, and verification. They do not buy
file-reading or bounded edits.

Self-contained: usable without any other skill; `rubric-panel`, `layer-cycle`, and `handoff`
extend it where named below.

**Provenance tags.** `[lab]` was measured in the inventory lab (three controlled experiments ×
three languages, anchored-rubric panels). `[cost]` comes from measured delegation-cost and
context-economics findings. `[field]` was observed in practice by the repo owner but has not been
reproduced under measurement. `[untested]` is reasoning that has never been measured. Change
`[untested]` first when evidence arrives, and never defend any tag as if it were a finding it is
not. The map from rule to measurement is `references/provenance.md`.

## The three layers

| Layer | Role | May amend the contract | May spawn agents | User reads its output | Context lifetime |
| --- | --- | --- | --- | --- | --- |
| Strategy | `strategist` — the session itself | yes | yes | yes | the whole job; never resets |
| Management | `manager` | no, escalates | yes | no | one chain; disposable |
| Execution | `scout`, `builder`, `reviewer` | no, escalates | no | no | one slice; disposable |

Spawn authority is structural, not a rule to be observed: `manager` carries the dispatch tool and
the execution agents do not. The consequence is easy to miss and deadlocks managers: a message to
an execution agent cannot be answered, because the callee has no tool to answer with
(`references/waiting.md`).

<!-- harness:claude-code -->
The tools are `Agent` and `SendMessage`.
<!-- /harness -->

### Strategy — `strategist`

The session itself, never a spawned agent. It pins no model — the model in the seat stays the
effort signal (Step 0).

<!-- harness:claude-code -->
The role noun exists because other harnesses let the primary agent be set as a named profile;
naming it now means that mapping is already made. Claude Code plugins ship subagents only, so
there is no `strategist` agent file here.
<!-- /harness -->

**Irreducibly its own — the floor, never delegated at any effort level:**

1. **Decomposition and architecture choice** — the slicing IS the plan; a bad slice cannot be
   fixed downstream.
2. **Definition of done** — written before any delegation (Step 3).
3. **Judging conflicting or high-impact reports.** Subagent findings are **hypotheses**. Anything
   that changes the plan gets re-derived from the cited source; dispatch the `reviewer` agent
   to do the re-derivation, and judge what it returns here.
4. **Final validation.** Run the hard gates personally before telling the user it is done. A
   manager's proof package is evidence, not verdict.
5. **User-facing synthesis** — the user hears one coherent account from the session they hired.
6. **Contract amendment.** When a finding shows the DoD itself was incomplete, only this layer
   edits it `[lab]`. Evaluation is a layer in the loop, not a verdict on it: in the lab, error-path
   quality stayed low in every round (the rubric floor under +test-first, tied for it under the
   rig) and moved only once judged findings were folded back into the spec. Gates enforce what they
   measure; they cannot invent a missing clause. Expect each amendment to surface the next layer
   of ambiguity — a contract is never finished, only converged-for-now.

What makes the floor irreducible is that every item requires holding the user's actual intent
next to the result. A layer below can satisfy a contract. It cannot notice that the contract was
the wrong one.

**Context it needs:** the user's goal and the constraints the user never stated, the standing
project rules, the definition of done, and the verdicts coming back up. Conclusions, not material.

**Context it must never be given:** the raw material of execution. File contents, log dumps, tool
transcripts, intermediate diffs, per-worker back-and-forth. This is the one context that never
resets, so anything read here is paid for on every later turn, while the same bytes read one layer
down are paid for once and thrown away.

**Never:** do labor it could brief (see the ceiling); accept a report as a verdict; hand the
definition of done to anyone else; let a layer below edit a gate it owns.

### Management — `manager`

**Irreducibly its own:** holding the live state of a coupled chain. What link N actually produced,
whether that output is good enough to build link N+1 on, and which worker to steer with a
follow-up rather than re-brief. It turns one contract into N sub-briefs and is the **first-pass
checker** on everything returned before anything is built on it.

That work cannot move up, because it is high-volume and short-lived and the strategy layer's
context is the one that never resets. It cannot move down, because a worker is deliberately blind
to its siblings (the negative list in `references/briefs.md`), so no worker can sequence the chain
or notice that two of them solved the same sub-problem differently.

Its standard execution loop on every building link is **build → review → revise → simplify**
`[field]`: builder implements test-first, `reviewer` (or `rubric-panel`) attacks the diff, fix
briefs continue the same builder, then `deletion-pass` once green. The `layer-cycle` skill is
that loop formalized for module-scale links.

**Bounded width, retired between slices `[field]`.** A chain is what fits before one report, with
**two to three tasks** as the working default `[untested]` — the eleven-task failure was observed,
the number was not — and the next slice goes to a **fresh manager** rather than the same one
continued. (Follow-ups *within* a chain still go to the same running
manager; that accumulated context is what the layer bought.) Two rules keep the width honest.
**Decision-gated items never enter a build slice**: an owner call or a pending ruling returns to
the strategy layer as a question for the user before any worktree opens. **A manager writes each
task's result to the tracker as it lands**, so a lost manager costs one slice's report rather
than the wave's. The anchors, and the eleven-task brief that forced them, are in
**`references/chain-width.md`**.

**Context it needs:** the objective, the DoD verbatim, the constraints, worker-model guidance, the
evidence format, and the stop conditions — plus everything its own workers return, which is the
bulk of it and which it exists to absorb rather than forward.

**Context it must never be given:** the user's conversation, the strategist's plan beyond this
chain, sibling waves, or how this work will be judged later. A manager that can see the whole plan
starts optimizing for the plan instead of reporting the chain honestly.

**Never:** amend the DoD (an unverifiable criterion is an escalation, not an edit); choose the
architecture above its own chain; address the user; treat its own proof package as the verdict;
touch read-only config; edit a file inside a live worker's owned list, or wait on a reply an
execution agent has no tool to send (`references/waiting.md`).

### Execution — `scout`, `builder`, `reviewer`

**Irreducibly its own:** contact with the material. Reading the tree, running the commands, making
the edits, producing the evidence. Also **independence** — the differential and the panel are
worth something only because these agents cannot see each other, and that property is destroyed
the moment the work moves up into a context that already knows the answer.

**Context it needs:** the brief, written for an agent with **zero chat context**. Repo path, exact
objective, owned files, read-only config, evidence format, verification commands, stop conditions
(`references/briefs.md`).

**Context it must never be given** — the negative list, which held across every round of the lab
`[lab]`: cycle budgets, remaining passes, or the fact that a later pass exists; rubric scores or
rankings; sibling implementations, prior rounds, or git history of the same work; the plan beyond
this slice.

**Never:** spawn another agent; edit the config that defines its own acceptance criteria; push,
merge, or touch any branch or worktree outside its own (committing inside its own worktree is
expected); widen its own scope to unblock itself; improvise past a stop condition; present a
self-report as proof; wait for an answer to a message it received — it has no channel to ask on, and its
report is its reply (`references/waiting.md`).

### Which layer am I on

Three questions settle it. May you amend the definition of done? May you spawn agents? Does the
user read your output? Strategy answers yes to all three, management only to the second, execution
to none. **If you were handed a written brief you did not write, you are not the strategist**,
however much judgment the work seems to want.

### Why three layers pay

**Context, measured `[cost]`.** Management traffic compounds. Every brief and report in the main
session lands in the ever-growing prefix and is re-read at cache rates on every subsequent turn. A
manager absorbs that chatter into a disposable context and hands back one package. Note that at
`standard` effort a manager is the *same model tier* as the session, so the layer buys context
absorption, not tier arbitrage. That is the mechanical reason the layer pays for itself, and it is
why "one fewer agent" is not the same as "cheaper".

**Specialization, observed `[field]`.** Each layer's job and context differ enough that three
focused prompts beat two larger ones. A collapsed layer's prompt has to describe both jobs, and
its agent has to decide which mode it is in on every turn. This is the owner's field observation,
not a measurement; a backlog card is open to run the same non-trivial job with and without a
manager layer, holding brief quality and the DoD constant, and to promote or refute the default
from the result. Until then it is a default, not a finding.

### When collapsing a layer is correct

Delegation is not free: every brief written, report read, and check performed costs briefing
overhead, hallway losses, and verification. For a small job that overhead exceeds the labor.
**Sizing a job honestly, including "too small to delegate, just do it", is the strategist's first
act.** Never ceremonialize a three-tool-call task into a crew.

**Collapse management** (the strategist runs the management layer itself, architecture B or C)
only when every one of these holds before the first dispatch `[untested]`:

1. **The work-list is final.** The slices already exist and no result is expected to re-slice
   them. If discovery is still needed, that is a scout wave first, then decide again.
2. **The slices are independent in outcome, not merely in file ownership.** No slice's result
   changes another slice's brief.
3. **You can name what each worker will hand back, and it is a note rather than an artifact.** Any
   wave returning diffs, logs, or inventories that must be read to proceed belongs in a disposable
   context.
4. **Reconciliation is mechanical** — a gate or a differential, not a reading task.

One condition failing puts a manager on the job. Two failing means C will fail loudly and late,
usually as workers escalating decisions the brief should have made.

**Collapse execution too** (architecture A, strategy alone) only when the job fits in a few tool
calls, or when the validation itself needs judgment that cannot be handed over.

**Never collapse strategy.** There is no layer above it, and the floor is what that means.

## The ceiling — delegate these even though they feel like judgment

A floor with no ceiling is not a constraint; every floor item stretches to cover almost any inline
action. These are the stretches, named so they can be refused `[untested]`:

- **Grounding recon.** "I need to understand the repo before I can brief anyone" is true, and is
  not a reason to read the tree personally. Dispatch it; read the report.
- **Probe and fixture writing.** Adversarial inputs, test fixtures, and throwaway scripts that
  prove a guard works are bounded and verifiable. Builder work.
- **The bounded fix discovered mid-flight.** Individually faster to do inline; collectively where
  most retained labor goes. Punch list, then one agent.
- **Re-derivation.** Independently checking a worker's claim is the `reviewer`'s whole job. Judging
  its verdict is floor item 3; performing the check is not.

**The check is a streak, not a ratio.** A lifetime ratio stays high even in healthy sessions,
because the strategist's own gate runs are floor work: the lab's actively-delegating sessions
measured ~7–19 delegable calls per dispatch (12.5:1 overall). What separates them from the
sessions that delegated nothing is the unbroken run: mid-fan-out solo runs clustered around 10–25
calls, the longer stretches (36–69) were grounding or closing work done by hand, and the
zero-delegation sessions ran 80–103 without a single dispatch `[lab]`. **A run of ~25 delegable
calls with no delegation is the line** — calibrated between the clusters, not measured
`[untested]`. Past it on a C/D/E job, stop and either dispatch the remaining work-list or name
which floor item this stretch is. The `delegation-watermark` hook counts the run and says so
without being asked.

## Step 0 — Determine the effort level

The model in the session's strategist seat IS the effort signal.

| Session model | Level | Meaning |
| --- | --- | --- |
| The everyday strategist model, or anything below it | `standard` | The default — everyday delegation work |
| A model deliberately above it | `deep` | A problem hard enough to justify the most expensive seat available |

<!-- harness:claude-code -->
Concretely here: Opus or below is `standard`; Fable is `deep`.
<!-- /harness -->

Overrides, highest wins: the user says so; or an `effort:` key in the frontmatter of
`atelier.local.md` (check for it; absence is normal — `references/activation.md` has the path).
State the level in effect when proposing an architecture.

At **`deep`**, the session's tokens cost roughly 2× the standard seat's, and a deep-tier
strategist measures at ~80–100k tokens just to get grounded plus ~50–100k to drive the work — past the context watermark before real work starts
`[cost]`. So: **never self-ground** (dispatch it, read the report, not the tree); **never collapse
management on a building wave** (collapse condition 3 binds hardest when the strategist's tokens
are the most expensive in the system, which puts C out of reach, though a scout wave returning
conclusions is still fine); **verify in layers by default**, one `reviewer` on every
plan-changing claim; **run one `reviewer` over every judgment-heavy link**, not just plan-changing
ones.

<!-- harness:claude-code -->
At `deep`, also **override builders to opus** more liberally — the per-dispatch `model` knob is
the cheapest way to buy judgment on a link the strategist cannot afford to take itself.
<!-- /harness -->

## Step 1 — Size the job on four axes

- **Complexity** — `trivial` → `bounded` (well-specified) → `coupled` (step N needs step N-1) →
  `architectural` (many unknowns).
- **Parallelizability** — disjoint file ownership, or a dependent chain?
- **Work-list** — do the slices already exist, or must they be discovered?
- **Change scope** — how much material one brief's owned-file list actually is, in files and
  bytes.

The third axis is the one sessions skip, and skipping it is the documented way a strategist ends up
doing the work itself. Work that arrives pre-sliced ("build this in three languages", "fix these
five issues") can be briefed immediately. Work that arrives as a goal ("restructure the repo",
"get this published") has no slices at t=0, so the default path is to discover them by hand, and
that is where the retained labor lands. In the lab's own record, every session whose work arrived
pre-sliced delegated heavily; every session whose work arrived as a goal delegated **nothing**
across 11+ hours and 278 self-performed tool calls `[lab]`.

**When the work-list does not exist yet, discovery is the first delegation.** Dispatch scouts
(architecture B), then size and slice from their report. Do not fix while inventorying: a defect
found during recon goes on the punch list, not into the working tree `[untested]`.

### Slice coupled work as releases from a spine

When complexity reaches `coupled` or `architectural`, do not slice by component — slice as
**incremental releases building out from a spine** `[field]`. Release 1 is a walking skeleton:
the thinnest end-to-end path through every layer of the system, one real input to one real
output, built, wired, and provable by a gate. Each later release widens exactly one dimension of
it (a behavior, a surface, a hardening pass), and every release ends with the **whole system
green**, never with a part of it finished.

Waves fall out of that ladder: the spine is wave one, and each increment is a wave whose DoD is a
machine check on the running whole rather than a promise about parts. The ordering spends
integration risk first — whether the pipeline connects at all is settled in the cheapest release —
and an interrupted job ends at its last green release instead of a pile of finished components
that have never met. The spine choice is floor work (it IS the decomposition, floor item 1); a
manager sequences links within a release and never re-plans across releases.

### Measure the owned-file list before dispatching

The first three axes are judged; the fourth is counted, once per brief. **A brief scoped above
10 files or 100 KB of owned files should be split** `[untested]`. Either term trips it alone. The
line is calibrated, not derived: across this kit's merged history the file-count distribution is
bimodal with a trough between roughly ten and twenty files, and a worker's own context runs out
around the same place — but nothing yet measures whether splitting at that boundary improves
anything, and both corpora are still growing, so the figures live in `references/provenance.md`
with their n and the date they were read rather than in this sentence. The byte term is what
catches the single-topic doctrine change: rewriting one skill and its reference set sits under
the file bound and well over the byte one.

**An entry that cannot be measured makes the figure a floor rather than a total — treat the
brief as over the threshold until that entry is resolved.** Four ways an entry goes unmeasurable,
each with one answer: a **glob** is expanded deliberately and re-measured, never expanded at
measurement time (that measures whatever directory the measuring process sits in, not the tree
the brief was written against); a **directory** means the brief is not scoped, so list the files
or accept the figure as a floor; a **missing** path is a typo or a file the worker is meant to
create, which costs nothing to read today and is excluded deliberately rather than left reading
as measured; an **unreadable** path is permissions, resolved before dispatch. A measurement that
cannot complete is red, never green.

<!-- harness:claude-code -->
`scripts/scope.py` in this skill does the counting:
`python3 primitives-core/skills/delegation/scripts/scope.py <owned-file> ...` from a checkout of
this kit, or, from an installed plugin,
`python3 ~/.claude/plugins/cache/dotfiles-agents/atelier/<version>/skills/delegation/scripts/scope.py <paths...>`.
With argv omitted it reads one path per line on stdin; `--json` is the machine form. It prints
`files`, `bytes`, `lines`, `binary`, `unresolved <n>`, then one `reason  path` line per
unresolved entry. Exit 0 is fully measured, 1 is a floor, and 2 is no paths given at all — an
empty owned-file list is a defect in the brief, not a zero figure.
<!-- /harness -->

## Step 2 — Pick the architecture

The architectures are shapes the three layers take, not alternatives to them. The layer column is
the part to check first.

| Task shape | Architecture | Layers | Strategist's share |
| --- | --- | --- | --- |
| Trivial / conversational | **A. Direct** — just do it | strategy only | All of it (overhead > labor) |
| Read-only breadth: searches, inventories, log reduction | **B. Scouts** — parallel read-only agents | strategy + execution | Ask, judge answers |
| Parallelizable, slices final, mechanical reconciliation | **C. Flat fan-out** — brief N scoped workers directly | strategy + execution | Plan, DoD, slice, reconcile, validate |
| Anything else non-trivial, and every coupled chain | **D. Manager-driven team** — one `manager` drives the chain as proxy | all three | Brief, escalations, final validation |
| Highly complex / architectural | **E. Phased crews** — audit → fold-back → build → verify | all three, a manager per phase | Deep planning, design calls, every gate |

Full playbooks, including what choosing wrong looks like in each: **`references/architectures.md`**.

**B is not only a destination.** When Step 1 says the slices are unknown, B is the mandatory first
phase of C, D, and E, not an alternative to them. A small scout wave collapses management cleanly
because scouts return conclusions rather than material; a wide sweep whose reports have to be
cross-read is a management job, so put one `manager` over it.

**The C-vs-D fork now points at D.** C is D with the management layer collapsed into the
strategist, so it is chosen by satisfying every collapse condition above, not by being torn. When
genuinely torn, take D `[field]`. The guidance this replaces said the opposite ("prefer the cheaper
architecture") and carried `[untested]`; no run has ever compared the same job under two
architectures, so nothing measured was overturned here.

**Choosing D does not settle how wide the chain is.** One manager takes what it can report on
once; past that the work is a wave of narrow slices, each with its own manager
(`references/chain-width.md`).

**Width is not lifetime.** Width is what a manager holds at once; lifetime is what its context can
pay for, and a brief can pass every width check and still outlive the agent it was written for.
The strategist estimates it while writing the brief: **slice count × (dispatch + verify) against
one manager context window**. Past roughly **60–70%** of that window there are two answers and no
third `[untested]` — **pre-split into sequential manager briefs**, cutting at the seam where a
slice's output stops changing the next slice's brief, or **mandate a successor contract**: an
externalized plan file kept current from slice 1, and report-up-with-the-plan as a stop condition
that outranks compacting, so the next manager resumes from written state rather than a summary
`[field]`. Neither is available once the manager is full: by then the only agent that could
re-slice the work is the one out of room. The arithmetic and the incident behind it are in
**`references/chain-width.md`**.

### Concurrent Chains

**Nor does it settle how many chains run at once.** When the work-list holds entries that are
independent in outcome — no chain's result changes another chain's brief — the strategy layer may
run **two to three architecture-D managers simultaneously**, each in its own worktree and branch,
rather than working the list one chain at a time `[untested]`. The cap is the strategist's own
verification capacity, not machine capacity: every returning package still needs a spot-check and
a gate run, and those land in the context that never resets.

**Assign three things at dispatch time, before the first manager starts** `[untested]`: the merge
order, ownership of every gated shared resource (version fields, changelogs, generated artifacts —
anything a gate makes single-writer), and the rebase-or-reorder duty for the second-to-merge
chain. Skipping this is not caught by CI: concurrent chains each bumping to the same next version
pass their checks individually, then fail one after another as each predecessor merges `[field]`.

Full conditions, the cap's reasoning, and what does not parallelise:
**`references/concurrent-chains.md`**.

## Step 3 — Satisfy four preconditions before the first dispatch

All four are cheap to write and expensive to retrofit `[lab]`.

1. **A definition of done, as machine-checkable criteria** — each one written as **a command plus
   its expected output**: a command that passes, a grep that returns zero, an artifact that
   exists. Never "works well". A criterion only a human can judge is either rewritten until a
   machine can check it or explicitly routed to a judged panel (`rubric-panel`) — never left as
   prose a worker can self-certify. **Include the error paths and the empty case**: unspecified
   edge cases are exactly where independent implementations diverge, and every divergence the
   lab's cross-implementation diffing surfaced traced to a case the contract never named.
2. **A gate that exists, has been proved red, and has this diff in its subject set.** The DoD's
   command must actually fail when *this* work is wrong. A gate that cannot fail is decoration; a
   gate that can only fail somewhere else is decoration for this brief. Break something
   deliberately **inside the files the worker will change**, watch that gate fail, restore, then
   dispatch against it — a break anywhere else in the tree proves the gate is alive, not that it
   is watching. Passing and covering are different facts that look identical from outside: a gate
   with zero real subjects reports the same green as a gate with fifty, so that break is the
   check, and it is the half that always runs. Where the gate can already name or tally the
   subjects it matched, read that too and confirm the worker's files are among them. Where it
   cannot — a stock test runner, linter, typechecker or build target usually cannot — the break
   stands alone: teaching a gate to report its subjects is an edit to config the dispatcher does
   not own, and a precondition that demanded it would be unsatisfiable exactly where it matters.
3. **A premise re-derived against the tree at dispatch time, not at authoring time.** A brief's
   factual claims — what a file asserts about itself, how many sites a rule touches, what a
   tracker item recorded — were true when written and are checked when dispatched, never the
   other way round. So re-derive every premise the brief rests on against the tree you are
   dispatching against. When it has moved, either re-brief, or state the drift in the brief and
   dispatch with the worker informed; never dispatch a premise nobody re-checked `[field]`. A
   lint's own docstring in this kit declared its rule had zero real subjects, deliberately; an
   item filed against it recorded that one assembly had since acquired the rule as a subject; the
   count re-derived at dispatch was three. Both the claim and its correction were stale and the
   gate had been green throughout, because nothing about a passing gate distinguishes zero
   subjects from N. No red gate could have surfaced it.
4. **An ownership map separating owned source from read-only config.** The gate belongs to the
   strategist. A worker that can edit the coverage threshold, the lint config, or the test that
   defines its own acceptance criteria can satisfy any brief. Workers are told: an unsatisfiable
   gate is an escalation, never a config edit. Where the project has activation on, make the map
   machine-readable — list the read-only config under `protected:` in `atelier.local.md`, and the
   `config-custody` hook enforces it (`references/activation.md`) `[untested]`.

## Model × task cheat-sheet

**"Layer" is not "tier", and a brief author who fuses them buys the wrong thing** `[untested]`.
Layer says what an agent is **for** and what it may do — amend the contract, spawn, address the
user. Tier says how much judgment one dispatch buys. So: a slice needing more judgment takes a
higher tier at dispatch, never a promotion to `manager`; a slice needing a decision made takes an
escalation upward, never a bigger model on the same worker. Moving an agent up a layer to buy
judgment hands it authority it must not have, and moving it up a tier to buy authority leaves the
decision with an agent that has no standing to make it.

The same refusal to substitute one rank for another governs the provenance tags: `[field]`
outranks `[untested]` and never outranks `[lab]` or `[cost]`. Only new evidence moves a tag —
never how long it has stood, and never how persuasive one session found it.

`builder` takes bounded, well-specified implementation links. Coupled, costly-to-unwind, or
judgment-heavy links remain with the `strategist` or the `manager`, which can use `reviewer` for
independent re-derivation.

| Agent | Layer | Use for |
| --- | --- | --- |
| `scout` | execution | Read-only audit, convention check, presence/absence, log reduction, reconciliation |
| `builder` | execution | Bounded, well-specified implementation links: scoped edits, test writing, refactors |
| `reviewer` | execution | Independent re-derivation of a high-impact claim or diff |
| `manager` | management | Drives a coupled chain as the session's proxy, spawns builders, verifies |
| `strategist` | strategy | The floor above — **never a spawned agent** |

**These defaults began as reasoning, not evidence** — the lab that produced this kit dispatched
the premium tier for every model-bearing call and never exercised the cheaper tiers.
`references/tier-cutoff.md` is the protocol for measuring the cutoff and the record of how far it
has been measured.

The tier vocabulary is **`light` / `mid` / `heavy`** — semantic bands, deliberately not model
names, so the same words survive a provider change. Role defaults: scout=light; builder and
`code-reviewer`=mid; reviewer and manager=heavy. Which concrete model a band buys is a harness
question, never an agent's.

<!-- harness:claude-code -->
**Tier is a dispatch-time decision, not an agent choice.** Here a band renders to one of Claude
Code's frontmatter keywords — light=`haiku` (with `effort: low`), mid=`sonnet`, heavy=`opus` — and
that rendering lives in `hooks/_lib/model_catalog.json`, not in any agent file. The strategist is
the session itself (Opus at `standard`, Fable at `deep`). Override at dispatch by naming the
keyword the band you want renders to: `model: sonnet` on a scout for cross-file synthesis,
`model: opus` on a builder for a judgment-heavy slice. Reviewer and manager are not downtiered —
verification is where the premium pays. Pass `model:` on the Agent call only when the slice
demonstrably needs the judgment.
<!-- /harness -->

Per-invocation knobs (worktree isolation, deliberate turn caps, continuing a running agent), agent
shell capabilities, and the git policy are in **`references/dispatch-knobs.md`**.

## Briefs

Every delegated prompt is written for an agent with **zero chat context**. Required fields, the
worker template, and the three rules that make briefs hold up are in **`references/briefs.md`**.
Read it before writing the first brief of a wave.

The rule worth stating here, because it governs every prompt this kit emits: **every constraint
gets a budget, a stop condition, or a machine check.** An instruction an agent cannot tell it has
satisfied gets maximized, not satisfied. Measured: an unbounded "define constants at the top" rule
produced a ~90-line wall of mostly single-use constants, costing that solution its worst dimension
score, unanimously, on its round's panel `[lab]`. The other two rules are test-first by default
with the observed failure as evidence (the largest single quality lever the lab measured), and the
negative list of what a worker must never be told (cycle budgets, scores, sibling work).

**A finding outside a brief's file scope folds before it is filed.** Take the first rung that
holds; each one skipped past is a tracker item nobody asked for. **a.** A sibling site of the
defect being fixed is in scope by construction — fix it in the same wave and the same landing.
**b.** A finding that belongs to an open item is commented onto that item; never open a second
item for work already tracked. **c.** A finding with no home goes on the wave's hardening list,
in the manager's proof package. **d.** Only a finding nothing above holds is filed as one new
item, and the report says why a–c did not. Never file a draft for someone else to finish: a
finding whose check you cannot state is a hardening-list line, not work. Blocking is the separate
axis — a finding that stops the DoD escalates from whatever rung it landed on. The `manager` and
`reviewer` contracts and `references/manager-brief.md` state the same order; they are one rule in
four places, not four rules.

**A manager brief carries one more check `[field]`:** if the brief has to tell the manager which of
its own tasks may run at the same time, the brief **is a wave and not a chain** — split it before
dispatching. This does not forbid concurrency below the manager: once the chain is narrow enough
that the question no longer needs answering in the brief, the manager fans out its own disjoint
builder slices itself (`references/manager-brief.md`). The line is who decides — the strategist
sizes the chain, the manager schedules inside it.

## Verification

Rank evidence: **a loud gate > an output differential across independent producers > an
independently re-derived check > a manager's proof package > a worker's self-report** `[lab]`. If
any wave bounded its coverage (top-N, sampling, skipped cases), surface that to the user and the
backlog — **silent caps read as full coverage.**

Two techniques carry most of the weight, both in **`references/verification.md`**: the
**differential** (where two agents produce artifacts that should agree observably, the
reconciliation is a diff of their outputs, and a disagreement is usually a contract defect rather
than an implementation defect) and the **panel escalation** (a judgment-shaped claim needs three
personas scoring against written anchors with disagreement surfaced rather than averaged — the
`rubric-panel` skill implements it; `layer-cycle` drives the create → evaluate → refine loop it
feeds).

## Waiting and liveness

An agent that blocks on something that cannot happen is the most expensive failure this kit has
recorded, and none of the layer rules above prevent it. Four rules do, and
**`references/waiting.md`** carries them in full, with every reported failure walked to
termination:

- **No wait without a producer.** Every wait — including one an agent adopts for itself, which is
  where every reported deadlock came from — names what would satisfy it, who produces that, and
  what happens when it does not arrive `[untested]`.
- **A message down is one-way.** Only `manager` carries a channel pointing downward; an execution
  agent that receives one has no tool to answer with, so its reply is its final report. Send
  amendments, never questions.
- **A live worker's owned files are not the dispatcher's**, manager included, and a green poll is
  not a completion signal. Queue the edit for after that worker finishes, or fold it into the
  worker as an amendment.
- **A completion reaches its dispatcher only while that dispatcher is still mid-turn** `[field]`.
  So dispatch synchronously unless you actually need concurrency, and never block on the
  notification; a report that lands one layer up is relayed down verbatim, never absorbed.

## Context hygiene

Operating defaults from measured findings `[cost]`. The `context-watermark` (UserPromptSubmit),
`delegation-watermark` (PostToolUse), and `handoff-freshness-guard` (PreCompact) hooks plus the
`handoff` skill are the enforcement layer; this skill decides when.

- **Trigger the `handoff` skill at a self-chosen boundary in the 60–80k band.** The economics
  optimum is ~40–60k; the buffer buys boundary quality. `context-watermark` does the nudging.
  **Scale its thresholds to the model's own context window rather than fixing them as a flat
  count** — a fixed number means different things on a 200k-window model and a 1M-window one. How
  far each harness has taken that is its own business; each states its concrete figures below and
  in `references/activation.md`.
- **Prefer handoff + a fresh session over `/compact`** — a fresh session reading the handoff
  restarts at ~10–20k; a compaction summary is similar in size, less curated, and carries a
  re-read tax.
- **Treat any ≥10-minute idle as a handoff point** — the session-break tax makes long gaps both
  expensive and a natural externalization boundary.
- **Clear after messy debugging, even below threshold** — visible prior errors raise future error
  rates independent of context length.
- **Downtier on demonstrably simple work**, gated to clearly simple tasks and paired with a strict
  DoD so an under-powered crew fails loudly and fast; see `references/tier-cutoff.md`.

<!-- harness:claude-code -->
Concretely here the window **caps** the threshold and never lifts it, because the `[cost]`
degradation band is an absolute token count: `context-watermark` sets soft at
`min(120k, 60% of the lead model's window)` and hard at `min(160k, 80%)`, each scaled by a
repo-size factor that only ever points down (tracked files: under 5k → 1.00, 5k–20k → 0.85,
over 20k → 0.75). At a 200k window that is 120k/160k; at 1M it is still 120k/160k,
because percent-of-window thresholds are inert against the ~967k auto-compact default; at 64k it
is 38.4k/51.2k. An unknown model falls back to the absolute pair and says so in its ledger row.
Override with `CONTEXT_WATERMARK_SOFT`/`_HARD`, or a `watermark:` key (`soft`/`hard`/`complexity`)
in `.claude/atelier.local.md` — env beats file beats computed. A delegated worker is watched too,
on `PostToolUse`, at half the session's soft line and with no hard tier: it cannot hand off or
clear, so the nudge tells it to wrap up and report. The fresh session is `/clear`; downtiering is
a `model:` value on the dispatch; and the handoff skill has no slash command — a command would
shadow the skill of the same name.
<!-- /harness -->

These watermarks are the strategy layer's budget. A manager spends a context that gets thrown away
at the end of its chain, so it hands off to a successor rather than to itself. If a chain outgrows
one manager context, that is a slicing defect to escalate, not a compaction to ride out — and one
the brief should have priced before dispatch (Step 2, "Width is not lifetime").

## Additional resources

- **`references/architectures.md`** — the playbooks in full.
- **`references/briefs.md`** — required fields, the worker template, the three brief rules.
- **`references/verification.md`** — evidence ranking, the differential, the panel escalation,
  aiming verification where the stack is weak.
- **`references/manager-brief.md`** — the fill-in-the-blanks architecture-D manager brief.
- **`references/chain-width.md`** — how wide one chain may be, how long one manager context can
  pay for it (the lifetime estimate, the split-or-successor call), retiring a manager between
  slices, and the worked eleven-task anti-example.
- **`references/concurrent-chains.md`** — running two to three manager chains at once, and the
  merge-order and shared-resource contracts that running them makes necessary.
- **`references/migrate-at-scale.md`** — one mechanical transform across many sites.
- **`references/tier-cutoff.md`** — the protocol for measuring where cheap model tiers stop being
  enough.
- **`references/dispatch-knobs.md`** — worktree isolation, turn caps, continuing an agent, the git policy.
- **`references/waiting.md`** — the no-wait-without-a-producer rule, one-way messages down, where
  a completion is routed, the liveness check, and file ownership while a worker is live.
- **`references/activation.md`** — per-project enforcement: `atelier.local.md`, the `enforce`
  modes, the `protected:` map, and the worker covenant.
- **`references/provenance.md`** — which rule came from which measurement, and which are untested.
