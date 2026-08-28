# Waiting — the wait that can never end, and what to do instead

Four field reports, one failure: an agent blocks on something that cannot happen, and nothing
stops it or even notices `[field]`. Deadlock is not a rare pathology here; it is the default
outcome of a wait whose producer was never named.

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

## The liveness check

To tell a dead in-flight agent from a slow one, check whether it is still writing `[untested]`.
Read that signal twice, a few minutes apart:

- **It advanced** → alive and working. Slow is not dead; do not re-dispatch.
- **Unchanged across two checks** → presumed dead. Stop waiting, and treat the work as not done
  rather than as done-and-unreported.

**What is not a liveness check:** polling the work product. A test suite is green between
mutants, a file is complete between edits, and a gate passes on a tree a worker is halfway
through rewriting. Polling for the outcome is how a session commits over live work. The
completion notification is the only signal that the work is finished; a liveness signal only
tells you whether anyone is still there.

<!-- harness:claude-code -->
The signal is on disk. Every running agent appends to its own transcript under the session
directory, so the file's mtime is the liveness reading — available to a `manager` and to the
`strategist` alike, since both have Bash:

```sh
# The session's agent transcripts. Slug = the project path with every
# non-alphanumeric character replaced by '-'; if that misses, take the
# most recently written subagents/ directory instead.
slug=$(pwd | sed 's/[^A-Za-z0-9]/-/g')
d=$(/bin/ls -dt ~/.claude/projects/"$slug"/*/subagents 2>/dev/null | head -1)
[ -n "$d" ] || d=$(/bin/ls -dt ~/.claude/projects/*/*/subagents | head -1)
/bin/ls -lt "$d"/agent-*.jsonl | head
```

Two things make the reading trustworthy. The `agent-<id>.meta.json` beside each transcript
carries `agentType`, `description`, and — for a manager's own workers — `spawnDepth: 2` and
`parentAgentId`, so you can confirm the row you are staring at is the dispatch you made rather
than a sibling's. And a manager's workers land in the **same** session directory as the
manager, so one listing covers both layers. Both facts are the on-disk layout the
`subagent-telemetry` hook already reads and documents; re-verify them there before relying on
a detail this file does not name.

The strategist also has `ListAgents`, which lists the agents it spawned in one call. A manager
does not carry that tool, which is why the check above is written against the filesystem: it is
the one form both layers can run.
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

## The four reports, walked

Each ends in termination under the rules above.

1. **Manager messages a live builder and waits for a reply.** The wait names no producer that
   can satisfy it (§1, item 2), and the one-way rule says so explicitly at the point of
   sending. The manager sends the amendment and keeps working; the reply is the builder's
   report, which arrives on completion. **Terminates.**
2. **An agent adopts an unbounded stop condition for itself.** The rule requires the fallback
   and its bound before the wait starts (§1, item 3). A condition that cannot name what
   satisfies it is rejected as a wait at adoption, and the agent proceeds or escalates.
   **Terminates.**
3. **A manager cannot tell a dead worker from a slow one.** It runs the liveness check. A signal
   still advancing means keep waiting on a real producer; a signal frozen across two checks
   means presumed dead, and the work is reported not-done rather than waited on further.
   **Terminates.**
4. **A manager overwrites its own live builder's file.** The ownership rule denies the edit
   before it happens; the fix goes on the punch list or into the worker as an amendment, and
   lands after the completion notification. **No lost write, and nothing waits.**
