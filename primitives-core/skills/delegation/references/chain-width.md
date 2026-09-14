# Chain width and lifetime — how wide a chain may be, how long one manager carries it

`SKILL.md` gives the manager "one chain; disposable" and forbids showing it sibling waves. Neither
bounds how **wide** one chain may be or how long one manager context can pay for it, and nothing
there retires a manager between slices. That gap is not theoretical: the repo owner wrote an
eleven-task manager brief after reading the whole skill, and every clause of it was defensible
`[field]`. **Principles without calibration anchors do not constrain.** The effort calibration in
`SKILL.md` binds because it carries anchors; this file is the management layer's.

## The bound

- **A chain is what fits before one report** `[field]`. The report is the unit because it is the
  only artifact the layer produces, so width is measured in what the manager must hold live at
  once, not in file count or diff size. **Two to three tasks is the working default**
  `[untested]`: what was observed is one eleven-task chain failing, and no run has located the
  number. It is calibrated between "one task is not worth a manager" and the incident, and matches
  the same default in `references/concurrent-chains.md` — one construct, one tag.
- **The next slice goes to a fresh manager, not the same one continued** `[field]`. A manager's
  context is disposable by design; carrying it across slices converts the cheap layer into a
  second long-lived context competing with the strategist's. This does not contradict
  `references/manager-brief.md` — follow-ups and escalation answers **within** a chain go to the
  same running manager, because that context is what the layer bought. A new slice is a new
  contract, so it is a new manager.
- **Decision-gated items never enter a build slice** `[field]`. Anything recorded as an owner
  call, a pending ruling, or a question for the user goes back to the strategy layer and is put to
  the user **before any worktree opens**. It is not work yet. A manager that reaches an open
  decision either stalls or decides for the owner, and it decides.
- **A manager writes its per-task result to the tracker as each task lands**, not only in its
  final report `[field]`. The report is the artifact that gets lost — to a crash, a stop
  condition, or a context ceiling. Writing through means a lost manager costs one slice's report
  rather than the whole wave's.
- **The smell test `[field]`:** if the brief has to tell the manager which of its own tasks may
  run at the same time, the brief **is a wave and not a chain** — split it before dispatching.
  What this claims is narrow. *Task-specific* sequencing, naming which of **these** tasks may run
  together, is decomposition, and decomposition is the strategy layer's floor (floor item 1); a
  brief phrased as guidance to the manager hands it down without ever appearing to break the rule.
  A standing policy about disjoint slices is not that. Once the chain is narrow enough that the
  question no longer needs answering in the brief, the manager fans out its own disjoint slices —
  the strategist sizes the chain, the manager schedules inside it (`SKILL.md`, "Briefs").

## The anchor — eleven tasks that read as one chain `[field]`

Observed in a consuming project, not reproduced under measurement here. One `manager` at the heavy
tier, one worktree, over an hour and roughly 200k tokens, most of it spent reasoning about
cross-task serialization the strategy layer should have settled before dispatch.

<!-- harness:claude-code -->
The run was on opus.
<!-- /harness -->

**The brief as written.** Eleven tasks (141 152 154 159 160 161 162 166 167 168 178) to one
manager in one worktree; they overlap on `nav-model.ts` and the settings screens, so workers on
shared files must run serially; the manager may PARK an entangled task with a written reason.

Every clause was defensible and the whole was wrong:

- **Shared files were read as chain membership.** They do need ordering, but **file overlap is a
  merge-ordering constraint, not evidence of one chain.** Only 141/152/154 genuinely collided;
  159, 166 and 167 barely touched the shared files, so overlap never made them one chain with the
  rest.
- **"Workers on shared files run serially" is decomposition pushed downward.** It states a real
  constraint, and deciding which of **these eleven** may run together is the strategist's floor.
  Phrased as guidance to the manager, handing it over never looks like a violation.
- **An epic rode with the one-liners.** They are all "tasks": TASK-160 rebuilds the settings area
  and deletes four screens, TASK-154 flips a capability flag. The epic sets the wall-clock for
  everything queued behind it.
- **Two decision-gated tasks sat in a build batch.** TASK-160 was recorded as an owner call and
  TASK-166 as needing a UX ruling. The manager decided both for the owner.
- **"May PARK with a written reason" reads as a safety valve and is not one.** The written reason
  lives in the manager's report, which is the artifact that gets lost.

**The same eleven tasks, sliced correctly:**

- **Before any worktree opens:** TASK-160 and TASK-166 go to the owner as two questions. They are
  not work yet.
- **Slice A (2 tasks):** 141 + 152 — admin list chrome and capabilities, same files.
- **Slice B (2 tasks):** 167 + 168 — show-section prose and the workspace-root landmark.
- **Slice C (2 tasks):** 154 + 162 — trash/inbox board capabilities, palette copy.
- **A and B are disjoint and run concurrently** in separate worktrees; each manager reports and is
  retired.
- **C is not free of A.** 154 collides with 141 and 152 by the collision analysis above, so C
  either takes an assigned merge order behind A or 154 moves into A's chain. This is the ordinary
  case, not an exception: concurrency between slices is what is left **after** merge order is
  assigned for the collisions, never a substitute for assigning it. Merge order and ownership of
  every gated shared resource are settled before the first dispatch
  (`references/concurrent-chains.md`).
- **TASK-160 is its own wave** after its ruling, with its own review.
- **161 + 178** form a slice briefable only after 160 lands, because where settings lives
  determines how they are entered.
- **TASK-159 goes unplaced.** The reconstruction never finds a slice for it. It barely touched the
  shared files, which is what keeps it out of A–C, and the record does not say what it should have
  been paired with. The gap is left standing rather than filled with an invented slice.

The corrected shape holds three slices of two, one wave of one, one slice that does not exist yet,
and one task nobody can place. The sequencing moved up a layer, where it was always due — and that
eleven tasks resist clean slicing even in hindsight, with the whole incident laid out, is itself
the argument for the bound.

## Two further shapes `[untested]`

Reasoned from the same failure mode, not observed. Both are chains only in the brief's phrasing.

**(a) Links that are actually independent — no manager at all.** Four tasks add a `--json` flag to
four unrelated CLI subcommands, briefed as a chain because one person will review them together.
**The tell: no link's output changes another link's brief.** That is flat fan-out (architecture C)
if the collapse conditions hold, and the manager layer is pure overhead — it would spend its
context re-reading four reports that never needed reconciling.

**(b) A slice whose DoD can only be evaluated after a sibling slice lands.** Slice A writes the
schema exporter; slice B's acceptance criterion is a command that validates fixtures against the
exported schema. Briefed as parallel, B's gate cannot be proved red or green until A's artifact
exists, so B either idles, stubs the artifact and certifies against its own stub, or widens scope
into A's files. **The tell: run each slice's acceptance command against the tree as it stands at
dispatch time.** One that cannot run is a hidden dependency wearing parallelism, and the two
slices are one chain or two waves — never one wave of two.

## The lifetime bound — a brief that fits at once but not in one manager

The bound above sizes what a manager holds at once. **Lifetime is what its context can pay for**,
and a brief can pass every width check and still outlive the agent it was written for.

**The anchor `[field]`.** Reported from a consuming project, not reproduced under measurement: one
correctly scoped brief — port a framework across roughly ninety source files, nine slices, no
decision-gated items, one worktree — spent an entire manager context (~160k tokens) on its first
three slices. The slicing was not wrong. The brief was simply three times longer than one agent.
What saved it was improvised: rather than compact and continue blind, the manager externalized a
plan file, marked the three finished slices, and reported up with the remainder written down; a
second manager took that file and finished the other six with no rework. It worked because that
manager invented the pattern under pressure — nothing in the brief asked for it, and the next
manager in that position may simply compact.

### The estimate `[untested]`

Cost per slice is **dispatch + verify**: the brief written down, the worker's report read, and the
manager's own first-pass check of it. Take the worst slice rather than the average — the estimate
exists to refuse an oversized brief, so it is biased toward refusing.

    slices × (brief + report + first-pass check)  vs.  one manager context window

Applied to the anchor: three slices for ~160k is ~55k a slice, so nine project to ~500k against a
context with roughly 200k to spend. The brief is 2–3 managers of work, and the line was in fact
crossed on slice three. **Past 60–70% of the window, one manager cannot be trusted to finish.**
Neither the ratio nor the arithmetic is measured: the fraction is calibrated so that a brief
landing on the line still has room for the escalation, the follow-up, and the report it owes at
the end, and every term in the estimate is a guess until a run instruments one.

### Split, or contract a successor

Two answers, both decided **before the dispatch**, never after — once the manager is full, the
only agent that could re-slice the work is the one out of room.

- **Pre-split into sequential manager briefs.** Cut at the seam check 3 already names: the first
  point where a slice's output stops changing the next slice's brief, chosen far enough forward
  that each half lands under the line. Each brief is its own contract and its manager is retired
  on its report. Prefer this whenever the seams are visible — two clean contracts beat one
  contract with a contingency.
- **Mandate a successor contract in the brief `[field]`.** When the work does not seam — one
  mechanical transform whose slices differ only in which files they touch, as in the anchor — the
  brief names a plan file, requires it kept current **from slice 1** rather than written once the
  manager notices it is full, and makes "report up with the plan file" a stop condition that
  outranks compacting. The successor is briefed on the plan file, not on its predecessor's report.

Compaction is not a third answer. A manager's context is disposable by design, so it has no one
to hand a summary to but itself, and mid-chain it would keep the same agent alive holding a lossy
copy of the state it is judged on — silently lossy, which is the part that costs. The strategy
layer hands off at a watermark; the management layer's equivalent is a successor, contracted at
brief time (`SKILL.md`, "Context hygiene").

## Applying it

At dispatch, four checks in order; any failure re-slices before a worktree opens. The first two
are "The bound" applied to the brief text; the last two are reasoning, not observation
`[untested]`.

1. **Strip the decision-gated items out.** They become questions for the user, not tasks.
2. **Run the smell test on the brief text.**
3. **Count what is left.** Past two to three tasks, cut at the first point where a task's output
   stops changing the next task's brief `[untested]` — that boundary is where one chain ends and
   the next begins, and the next one gets a fresh manager.
4. **Price what is left against one manager context**, per the lifetime bound above. Over the
   line, the brief either pre-splits at the check-3 seam or carries a successor contract.
