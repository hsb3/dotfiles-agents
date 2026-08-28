# Dispatch knobs — the per-invocation settings and the git policy

These are decided at the dispatch, not baked into the agent definitions. The definitions carry
defaults; the dispatch carries the deviation.

## Model tier

Tier is a separate axis from the layer an agent sits on: the layer says what the agent is for, the
tier says how much judgment is being bought for it. See `tier-cutoff.md` for the protocol behind
the defaults and the state of the evidence for them.

<!-- harness:claude-code -->
`model` on the Agent call overrides the definition's default for one invocation. It is set at
dispatch precisely so the same agent can serve a cheap slice and an expensive one.
<!-- /harness -->

## Worktree isolation

Runs the agent in a fresh git worktree. Costs setup time and disk per agent. Use **only** when
parallel workers genuinely must mutate the same files. Disjoint file scopes are cheaper and
usually available — prefer re-slicing over isolating. A project can arm this per agent type
through the `isolate:` key in `atelier.local.md`, which the `worktree-isolation` hook reads
(`references/activation.md`).

<!-- harness:claude-code -->
Per dispatch, the knob is `isolation: worktree` on the Agent call.
<!-- /harness -->

## Deliberate turn caps

A **deliberate** per-wave cap, not a default backstop. None of the builder, reviewer, or scout
definitions impose a turn limit: each self-regulates by scope and escalates loudly — an oversized
slice for builder/reviewer, an unanswerable or over-broad question for scout — rather than
stalling silently at a clock.

Impose a cap only when a specific wave has a reason (a known-small transform where a long run
means something went wrong). An arbitrary cap on open-ended work produces silent partial results,
which is the failure mode the definitions were changed to avoid.

<!-- harness:claude-code -->
The knob is `maxTurns` on the Agent call.
<!-- /harness -->

## Continuing an agent

To extend or course-correct an agent you already dispatched, continue the same one rather than
dispatching a fresh agent with a longer brief. A re-brief discards the accumulated context that is
most of what that agent already cost. This matters most for the `manager`, whose value is
precisely the chain context it has absorbed.

<!-- harness:claude-code -->
The channel is `SendMessage` addressed to the agent's id. It reaches an agent that is still
running as well as one that has finished.
<!-- /harness -->

**Downward it is one-way.** `scout`, `builder`, and `reviewer` have no channel of their own, so a
message to a live execution agent arrives and cannot be answered: the callee has no tool with
which to send anything before it finishes. Send amendments, never questions, and never block on
the reply — it is the callee's final report. `waiting.md` has the rule and the alternatives.

<!-- harness:claude-code -->
Waiting on that reply instead deadlocked two managers in one session `[field]`. `waiting.md` also
carries the liveness check for telling a dead callee from a slow one.
<!-- /harness -->

## Agent capabilities and the git policy

- **Spawn authority is structural.** `manager` is the only shipped agent that can dispatch;
  `scout`, `builder`, and `reviewer` cannot delegate onward. That is the layer boundary enforced
  by the tool list rather than by prose.
- `builder`, `reviewer`, and `manager` have full shell. Briefs should require them to run their own
  verification commands and paste the actual output.
- `scout` has a shell but no write or edit tools — it cannot write a file, and that half
  of its read-only guarantee is structural (the tools are absent). Shell *authority* is not
  structural: scout's default posture is no shell, and a brief must name the exact read-only
  command(s) it grants — no substitutes, no ungranted flags. Granting scout a command is a real
  decision with a real cost; grant reads only, and only what the brief needs answered.
- **Read-only git** (`status`, `diff`, `log`, `show`) is allowed to every full-shell agent
  (`builder`, `reviewer`, `manager`); a brief may grant scout a specific read-only git command the
  same way it grants any other read.
- **Mutating git inside a worker's own worktree is the worker's.** An agent working in a worktree
  of its own commits there as it goes — that branch is its. What is reserved to the orchestrating
  session is **pushing, merging, and any branch, worktree, or repo state outside the worker's
  own**, because integration is not a worker's job. This is prompt-level policy, not a tool-layer
  block, so it can be violated. Treat a push, a merge, or a commit on a shared branch from below
  the session as a protocol breach and check what else that agent did.
- **Config is read-only below the strategy layer** unless a brief explicitly hands ownership over.
  Gate, lint, typecheck, coverage thresholds, and CI belong to the strategist, because an agent
  that can edit its own acceptance criteria can satisfy any brief. An unsatisfiable gate is an
  escalation.

<!-- harness:claude-code -->
The tools behind the first bullet: `manager` carries `Agent` and `SendMessage`, and `scout`,
`builder`, and `reviewer` do not. `scout` additionally lacks `Edit`, `Write`, and `NotebookEdit`.
<!-- /harness -->
