# Chain width — how wide a chain may be, and when a manager is retired

`SKILL.md` gives the manager "one chain; disposable" and forbids showing it sibling waves. Neither
bounds how **wide** one chain may be, and nothing there retires a manager between slices. That gap
is not theoretical: the repo owner wrote an eleven-task manager brief after reading the whole
skill, and every clause of it was defensible `[field]`. **Principles without calibration anchors
do not constrain.** The effort calibration in `SKILL.md` binds because it carries anchors; this
file is the management layer's.

## The bound

- **A chain is what fits before one report — two to three tasks as the working default**
  `[field]`. Width is measured in what the manager must hold live at once, not in file count or
  diff size.
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
- **The smell test:** if the brief has to tell the manager which of its own tasks may run at the
  same time, the brief **is a wave and not a chain** — split it before dispatching. Deciding what
  runs concurrently is the strategy layer's floor (floor item 1), and a brief phrased as guidance
  to the manager hands that decision down without ever appearing to break the rule.

## The anchor — eleven tasks that read as one chain `[field]`

Observed in a consuming project, not reproduced under measurement here. One `manager` on opus,
one worktree, over an hour and roughly 200k tokens, most of it spent reasoning about cross-task
serialization the strategy layer should have settled before dispatch.

**The brief as written.** Eleven tasks (141 152 154 159 160 161 162 166 167 168 178) to one
manager in one worktree; they overlap on `nav-model.ts` and the settings screens, so workers on
shared files must run serially; the manager may PARK an entangled task with a written reason.

Every clause was defensible and the whole was wrong:

- **Shared files were read as chain membership.** They do need ordering, but **file overlap is a
  merge-ordering constraint, not evidence of one chain.** Only 141/152/154 genuinely collided; 159,
  166 and 167 barely touched the shared files and could have run as concurrent slices in separate
  worktrees.
- **"Workers on shared files run serially" is decomposition pushed downward.** It states a real
  constraint, and what may run concurrently is the strategist's floor — phrased as guidance to the
  manager, handing it over never looks like a violation.
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
- A–C are file-disjoint, so they run **concurrently in separate worktrees**; each manager reports
  and is retired.
- **TASK-160 is its own wave** after its ruling, with its own review.
- **161 + 178** form a slice briefable only after 160 lands, because where settings lives
  determines how they are entered.

The corrected shape holds three slices of two, one wave of one, and one slice that does not exist
yet. Nothing was dropped; the sequencing moved up a layer, where it was always due.

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

## Applying it

At dispatch, three checks in order. Any failure re-slices before a worktree opens.

1. **Strip the decision-gated items out.** They become questions for the user, not tasks.
2. **Run the smell test on the brief text.** Any sentence sequencing the manager's own tasks means
   the split is not done.
3. **Count what is left.** Past two to three tasks, cut at the first point where a task's output
   stops changing the next task's brief — that boundary is where one chain ends and the next
   begins, and the next one gets a fresh manager.
