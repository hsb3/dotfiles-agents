# Waiting — the wait that can never end, and what to do instead

Field reports, one failure: an agent blocks on something that cannot happen, and nothing stops
it or even notices `[field]`. Deadlock is not a rare pathology here; it is the default outcome of
a wait whose producer was never named. Later reports add the same failure from the other end —
the event really happened and the notification of it was delivered somewhere else — so the
routing section below is part of the same rule, not a separate concern.

## The rule — no wait without a producer

**Every wait names three things, or it is not a wait** `[untested]`**:**

1. **What would satisfy it** — the observable event, not the feeling of being unblocked.
2. **Who produces that** — a named live agent, a running command, or the user. Not "the
   builder" in general; the dispatch you actually made.
3. **What you do when it does not arrive** — the fallback, with the bound that triggers it.

Missing any one of the three, you are not waiting, you are deadlocked. This is the
self-adopted half of the constraint rule in `briefs.md` §1: that rule bounds constraints
handed **to** a worker, and every reported deadlock came from a stop condition an agent
adopted **for itself**, which no brief had ever bounded.

The three commonest producers that do not exist:

| The wait | Why nothing can satisfy it |
|---|---|
| "waiting for the builder to reply" | An execution agent has no channel to reply on (below). |
| "waiting until the tests are green" | Green is a state a worker passes through mid-run; nothing publishes "done". |
| "waiting for the manager to confirm" | Confirmation is its final report; there is no earlier one. |

## Messages to a live execution agent are one-way

`manager` is the only shipped agent with a channel pointing downward; `scout`, `builder`, and
`reviewer` have none (`agents/*.md` frontmatter). So a message to a live execution agent
**arrives and cannot be answered**. The callee has no tool with which to send anything before it
finishes. Waiting on that answer is the deadlock two managers hit in one session `[field]`.

<!-- harness:claude-code -->
The channel is `SendMessage`, and only `manager` carries it.
<!-- /harness -->

Grant the tool downward and the layer boundary goes with it: a worker that can message can
message its siblings, and the negative list in `briefs.md` §3 — the information asymmetry that
makes a differential or a panel mean anything — stops being structural. The channel stays
closed on purpose.

**So a message down is an amendment, never a question.** Send it to change what the callee is
doing; the answer, when it comes, is the callee's final report. If you need an answer *before*
the callee finishes, you have three moves and none of them is waiting:

- **Read it out of the brief.** The answer to most mid-flight questions is already the
  contract; re-read it rather than asking.
- **Dispatch a scout.** An independent read-only agent answers a question about the repo
  faster than the busy worker would, and costs the worker nothing.
- **Let it finish.** Completion is a real event that really arrives. Do other work against it.

The callee's side of the same rule: **a message you receive is an amendment to your brief.**
Fold it in and keep working. Do not stop to acknowledge it, and never wait for a follow-up —
your report is the only thing you can send, and it is sent by finishing.

## Where a worker's completion actually goes

**A worker's completion reaches the agent that dispatched it only if that agent is still mid-turn
when the worker finishes** `[measured]`. An agent whose turn has already ended is never re-invoked by
its child's completion. Delivery is therefore a race against the dispatcher's own turn ending, and
a manager that dispatches in the background and then stops talking loses it by construction. This
was established by a controlled headless probe rather than by unreproduced observation — but the
probe ran on one harness, so the mechanism it measured is recorded as that harness's rather than as
doctrine.

<!-- harness:claude-code -->
**The mechanism, measured here.** Every completion is enqueued to the top-level session first and
then re-routed down to the real dispatcher, and that re-route lands only while the dispatcher is
still running and interruptible. Three outcomes were measured from one dispatch shape, differing
only in what the manager was doing at that moment:

- **Manager still mid-turn** — the completion arrives inside the manager's own transcript
  carrying the worker's full result, and the manager continues past it. The only delivery
  observed.
- **Manager's turn already over** — the completion is delivered to the top-level session instead,
  whose model reads a report for a wave it is not running. The manager's transcript ends where it
  ended; nothing resumes it.
- **Manager stopped seconds after its worker finished** — the completion reached no one: enqueued
  above, then dropped. Why is not established `[untested]`, so treat a backgrounded completion as
  a signal that may simply never exist rather than one that is merely late.
<!-- /harness -->

**So never let a completion notification be the thing you are blocked on.**

- **Dispatch synchronously unless you actually need concurrency** `[measured]`. A synchronous
  dispatch hands the worker's result back as an ordinary tool result — no queue, no notification,
  no race — and it is the only route measured on this harness to deliver every time. It is the
  default; a background dispatch is the deviation and needs a reason.
- **Fan out inside one turn, and stay in that turn until the fan-in** `[untested]`. Concurrency is
  still worth having; what breaks it is ending the turn while workers run. Hold the turn open with
  your own real work — reviewing the last link, drafting the next brief — never with a sleep,
  which the liveness check below forbids for its own reasons.
- **A dispatch you backgrounded and then walked away from is not a wait, it is a bet.** It names a
  producer, but that producer's message may never be delivered at all, which is exactly the third
  clause of §1: name what you do when it does not arrive, and make that fallback reading the
  worker's own record — never waiting longer on a notification that may not exist.

**The standing relay.** A report for a wave it is not running lands in the top-level session
often enough to need a protocol: that session neither acts on it nor quietly absorbs it. It
relays the report down, in full and verbatim, to the manager that dispatched the worker, on the
manager's own channel. This is the field workaround already in use, and it stays the recovery
path for a race that has already been lost `[field]`.

**A manager's word that "the result came back" is not evidence** `[measured]`. In the probe the
manager reported the expected result while already holding that same text in its own briefing, so
its line would have read identically had nothing been delivered. Delivery is proven by the
receiving transcript's record of it, never by the receiver's summary — the evidence ranking in
`verification.md` applies to the plumbing as much as to the work.

<!-- harness:claude-code -->
The knob is the Agent call's background flag; leaving it off is the synchronous default above.
The relay channel is `SendMessage` addressed to the manager's agent id, which reaches a finished
agent as well as a live one, so the relay restarts a manager that had already stopped. A delivered
completion appears in the recipient's transcript as an attachment carrying the child's whole
result, which is the record to read when checking whether delivery happened.

**Transcript location is not routing evidence.** Every agent at every depth writes its transcript
under the top-level session's directory; parentage lives only in the sibling
`agent-<id>.meta.json` (`parentAgentId`, `spawnDepth`). A worker's file sitting under the top
session's directory therefore says nothing about where its completion went — a symptom once read
as proof of misrouting is only the normal layout.

What the probe did not cover `[untested]`: a manager that sends a resume message and then ends
its own turn — the originally reported shape, which should be presumed to lose the same race
until someone measures it — and interactive sessions, since every arm ran headless (`claude -p`).
<!-- /harness -->

## The liveness check

**An unconditional fixed-duration sleep loop is a violation, not a wait** `[field]`. It names no
event, so it cannot end when the event arrives, and it makes the waiter itself look dead.
Polling with a real break condition and a bound is the degraded-but-honest form; doing other
work and letting the completion notification arrive beats both.

**Look outside the transcript first** `[field]`. A stalled agent and a dead one are
indistinguishable from inside it, but a working chain leaves traces anywhere else: `git status`
and `git log` in the worker's worktree, `gh pr list` for anything opened, containers or servers it
was told to run. Those cost one cheap command each and answer "is anything landing?" rather than
"is anyone there?", which is the question you actually have. Take them before any reading below.

Reading silence wrong costs more than over-waiting — it abandons a live chain and reports
finished work as not done — so take the rest in this order:

1. **Live children first.** A parent blocked on a child writes nothing; silence is the correct
   state of a correctly-waiting parent. Silence only means dead for an agent with no live
   children, and applied recursively the signal is the leaf.
2. **Then the last tool call before the gap.** A blocking call of known duration — a sleep, a
   poll loop, a long build — is a scheduled wake, not death, and it says so. Presuming death
   before its deadline is always wrong.
3. **Only then read the signal twice**, a few minutes apart `[untested]`. Advancing → alive and
   working; slow is not dead, do not re-dispatch. Unchanged across both checks, with no live
   children and no blocking call in flight → presumed dead. Stop waiting, and treat the work as
   not done rather than as done-and-unreported.

**What is not a liveness check:** polling the work product. A test suite is green between
mutants, a file is complete between edits, and a gate passes on a tree a worker is halfway
through rewriting. Polling for the outcome is how a session commits over live work. The
completion notification is the only signal that the work is finished; a liveness signal only
tells you whether anyone is still there.

**Why the rule reads this way.** The first version — silence across two reads means dead —
produced a false positive within the hour, on the exact agent type it was written for `[field]`.
A live `manager`'s liveness signal was unchanged across two reads 6m13s apart while the harness's
own listing reported it running, and it resumed normally. Read back from its own transcript, the
freeze was not a parent politely blocked on a child: the manager had issued
`for i in $(seq 1 55); do sleep 10; done`, one of five unconditional sleep loops in 52 minutes
totalling 2750 commanded seconds, and it overslept its own worker's completion by ~5.5 minutes. A
live-children check alone would have returned the same false verdict at the second read, since
the child had finished by then; the discriminator was the agent's own last tool call. Only the
false positive is measured — the corrected rule above is still `[untested]` as a rule.

<!-- harness:claude-code -->
The `strategist` reaches for `ListAgents` first: it lists every agent the session spawned and
whether each is still running, in one call, and it reported the truth in the false positive above
when the filesystem reading did not.

A `manager` does not carry that tool, so its reading is the fallback, and the signal is on disk.
Every running agent appends to its own transcript under the session directory, so the file's
mtime is the liveness reading, and both layers have Bash to take it:

```sh
# The session's agent transcripts. Slug = the project path with every
# non-alphanumeric character replaced by '-'; if that misses, take the
# most recently written subagents/ directory instead.
slug=$(pwd | sed 's/[^A-Za-z0-9]/-/g')
d=$(/bin/ls -dt ~/.claude/projects/"$slug"/*/subagents 2>/dev/null | head -1)
[ -n "$d" ] || d=$(/bin/ls -dt ~/.claude/projects/*/*/subagents | head -1)
/bin/ls -lt "$d"/agent-*.jsonl | head
```

Two things make the fallback trustworthy. The `agent-<id>.meta.json` beside each transcript
carries `agentType`, `description`, and — for a manager's own workers — `spawnDepth: 2` and
`parentAgentId`, so you can confirm the row you are staring at is the dispatch you made rather
than a sibling's. And a manager's workers land in the **same** session directory as the
manager, so one listing covers both layers. Both facts are the on-disk layout the
`subagent-telemetry` hook already reads and documents; re-verify them there before relying on
a detail this file does not name.
<!-- /harness -->

## File ownership while a worker is live

`briefs.md` gives every worker an owned file list, and the map is written strategist-to-worker.
It binds a manager to its own workers identically, and the gap cost a silently reverted fix
`[field]`: a manager edited a file, its builder finished, and the builder's write — made
against the file as it stood at dispatch — landed on top.

**A file inside a live worker's owned list is not yours, whoever dispatched that worker**
`[untested]`. The manager's licence to make "fixes too small to brief" stops at the boundary of
every owned list it has handed out. While a worker you dispatched holds a file:

- **Read it freely.** Reading is never the problem.
- **Do not edit it.** Not a typo, not a one-liner, not a merge of your change with theirs.
- **Queue the edit on your punch list** and apply it after that worker's completion
  notification — or fold it into the worker as an amendment.
- **A file two live workers both need is a slicing defect.** Serialize them or re-slice;
  parallel workers on one file is the situation the ownership map exists to prevent.

The same rule read upward: the strategist does not edit inside a live manager's chain either,
and does not commit while any dispatch is in flight — a commit taken mid-run captures whatever
the tree happened to be, including a half-applied edit or a worker's sabotage fixture `[field]`.

## Retiring a worker's worktree

**Do not remove a worker's workspace while it may still be resumed, and once removed, never
resume that worker again** `[field]`. The two halves are the same rule read from either end:
tear-down and "can this worker still answer" end together, in that order — resuming into a
workspace whose custody has already changed hands is what produces an orphan.

<!-- harness:claude-code -->
Concretely: remove a worker's worktree only after its last message, and once removed, never
`SendMessage` that agent again.
<!-- /harness -->

**A removed workspace is not always a deliberate act.** An unchanged worker workspace is
auto-removed by the harness when that worker finishes, with nobody choosing it — the orphan
state can arrive from ordinary completion, not only from an operator tearing one down early.

**A resumed orphan is not merely disoriented — it is aimed at the dispatcher's own workspace.**

<!-- harness:claude-code -->
Its `pwd` and `git rev-parse --show-toplevel` silently re-resolve to the DISPATCHER's tree and
branch, with no error, and the worktree-isolation guard then names that tree as the one it is
"isolated in." An agent that trusts those readings and proceeds writes into a tree its
dispatcher is actively using. Reproduced twice (2026-09-07, 2026-09-08) on Claude Code 2.1.263.
This is reasonable default harness behavior, not a defect — do not file it upstream; design
around it instead.
<!-- /harness -->

**The practical consequence is why the order is integrate, confirm no further resume, then
remove:** a worker that commits its own work to its own branch survives having its workspace
removed — the commit is durable, independent of the tree — while a worker that leaves work
uncommitted does not. Integrate the worker's committed result first, confirm you will not need
to resume that worker again, and only then remove its workspace.

## The reports, walked

Each ends in termination under the rules above.

1. **Manager messages a live builder and waits for a reply.** The wait names no producer that
   can satisfy it (§1, item 2), and the one-way rule says so explicitly at the point of
   sending. The manager sends the amendment and keeps working; the reply is the builder's
   report, which arrives on completion. **Terminates.**
2. **An agent adopts an unbounded stop condition for itself.** The rule requires the fallback
   and its bound before the wait starts (§1, item 3). A condition that cannot name what
   satisfies it is rejected as a wait at adoption, and the agent proceeds or escalates.
   **Terminates.**
3. **A manager cannot tell a dead worker from a slow one.** It runs the liveness check in order:
   live children, then the last tool call before the gap, then the signal twice. Anything
   unresolved means keep waiting on a real producer while doing other work — never sleeping on a
   fixed timer. A frozen signal with no live children and no blocking call in flight means
   presumed dead, and the work is reported not-done rather than waited on further.
   **Terminates.**
4. **A manager overwrites its own live builder's file.** The ownership rule denies the edit
   before it happens; the fix goes on the punch list or into the worker as an amendment, and
   lands after the completion notification. No lost write, and nothing waits. **Terminates.**
5. **A manager spawns a background worker and then ends its turn.** Delivery needs a live
   dispatcher, so the completion goes to the top-level session and the manager is never
   re-invoked. The routing rule refuses that shape at the dispatch: go synchronous, or keep the
   turn open until the fan-in. Made anyway, the top session relays the report down verbatim and
   the manager resumes holding the worker's result; if nothing was ever delivered, the fallback
   is reading the worker's own record, not waiting. **Terminates.**
6. **A manager resumes a finished worker and the reply never appears.** Presumed the same race —
   that arm was not run `[untested]` — so send the message and stay in the turn with real work
   instead of ending it on the send. Where the reply is already missing,
   the manager reads the worker's record rather than waiting on it, and the relay covers anything
   that surfaced above instead. **Terminates.**
