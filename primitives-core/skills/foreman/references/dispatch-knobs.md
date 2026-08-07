# Dispatch knobs — the per-invocation settings and the git policy

These are set on the Agent call, not in the agent definitions. The definitions carry defaults; the
dispatch carries the deviation.

## `model`

Overrides the definition's default for one invocation. This is the tier decision, and it is a
dispatch-time decision precisely so the same agent can serve a cheap slice and an expensive one.
See `tier-cutoff.md` for the state of the evidence behind the defaults (currently: none).

## `isolation: worktree`

Runs the agent in a fresh git worktree. Costs setup time and disk per agent. Use **only** when
parallel workers genuinely must mutate the same files. Disjoint file scopes are cheaper and
usually available — prefer re-slicing over isolating.

Known trap: an agent in a worktree can commit to its own branch, and a session that later
integrates carelessly can end up with worker commits on the main branch. Verify what landed
before merging.

## `maxTurns`

A **deliberate** per-wave cap, not a default backstop. None of the builder, reviewer, or scout
definitions impose a turn limit: each self-regulates by scope and escalates loudly — an oversized
slice for builder/reviewer, an unanswerable or over-broad question for scout — rather than
stalling silently at a clock.

Set `maxTurns` when a specific wave has a reason (a known-small transform where a long run means
something went wrong). An arbitrary cap on open-ended work produces silent partial results, which
is the failure mode the definitions were changed to avoid.

## SendMessage continuation

To steer an agent that is already running, or to extend one that finished, use SendMessage with
its id rather than dispatching a fresh agent with a longer brief. A re-brief discards the
accumulated context that is most of what that agent already cost. This matters most for a `lead`,
whose value is precisely the chain context it has absorbed.

## Agent capabilities and the git policy

- `builder`, `reviewer`, and `lead` have full shell. Briefs should require them to run their own
  verification commands and paste the actual output.
- `scout` has Bash but no `Edit`, `Write`, or `NotebookEdit` — it cannot write a file, and that half
  of its read-only guarantee is structural (the tools are absent). Shell *authority* is not
  structural: scout's default posture is no shell, and a brief must name the exact read-only
  command(s) it grants — no substitutes, no ungranted flags. Granting scout a command is a real
  decision with a real cost; grant reads only, and only what the brief needs answered.
- **Read-only git** (`status`, `diff`, `log`, `show`) is allowed to every full-shell agent
  (`builder`, `reviewer`, `lead`); a brief may grant scout a specific read-only git command the same
  way it grants any other read.
- **Mutating git** (`commit`, `push`, `rebase`, `reset`, `checkout`, `stash`, `tag`) is reserved to
  the session. This is prompt-level policy, not a tool-layer block, so it can be violated. Treat
  any worker git mutation found in a diff as a protocol breach and check what else that agent did.
- **Config is read-only to workers** unless a brief explicitly hands ownership over. Gate, lint,
  typecheck, coverage thresholds, and CI belong to the foreman, because a worker that can edit its
  own acceptance criteria can satisfy any brief. An unsatisfiable gate is an escalation.
