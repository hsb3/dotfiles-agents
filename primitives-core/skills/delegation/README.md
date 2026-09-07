# delegation

Delegation doctrine for a session that takes on a substantial task. Work runs on three
layers — strategy, management, execution — and this skill defines what each one owns, what
context it must carry, what context it must never be handed, and what it must never do.

Three layers is the default for anything non-trivial. Collapsing one is an exception with
stated conditions, not a tiebreak, because each layer's job and context differ enough that
three focused prompts beat two larger ones. The measured half of that argument is context:
every brief and report in the main session lands in a prefix that is re-read on every
later turn, while a manager absorbs the same traffic into a context that gets thrown away.

## The layers

- **Strategy — `strategist`**, the session itself and never a spawned agent. Decomposition,
  the definition of done, judging high-impact reports, final validation, what the user
  hears, and amending the contract.
- **Management — `manager`**, one agent driving a coupled chain as the session's proxy.
  Sub-briefs, first-pass checking, and a proof package back.
- **Execution — `scout`, `builder`, `reviewer`**, each working from a brief and nothing else.

## Waiting

A separate failure the layer model alone does not prevent: an agent blocking on something
that cannot arrive. Only `manager` carries `SendMessage`, so a message to a live execution
agent can never be answered; a self-adopted stop condition that names no producer can never
be met; and a slow worker is indistinguishable from a dead one without a check.
`references/waiting.md` holds the rules and the liveness check.

## When it triggers

Use it when a session takes on a feature build, refactor, migration, audit, or multi-file
fix estimated at more than ~30 minutes of agent work, even if the user never says
"delegate". Also use it when the user asks how to split work across agents, mentions crews,
teams, managers, or subagents, worries about token cost on a big job, or wants to pick a
model tier or a delegation architecture. It applies especially when the work arrived as a
goal rather than a list of slices, which is the documented case where sessions stop
delegating altogether.

## Per-project enforcement

The doctrine is prose until a project arms it. `references/activation.md` is the one page that
says which keys exist, which hook reads each, and what each one does when it is absent or
malformed — `enforce` and `protected` (config custody over file paths), `isolate` (writing
workers get their own checkout), `protected-branches` (a worker may not commit or push onto a
named branch, and may not `git stash` in a tree it shares with a peer), `handoff`, and `effort`.
It also records which copy of the activation file a hook reads when the worker is running inside
a linked worktree, and the design commitments behind the enforcement layer — fail-open
everywhere, custody scoped to subagents so the strategy layer is never restricted, and each
guard stating its own ceiling instead of implying containment it does not have.

## Reading the evidence

Every rule carries a provenance tag: `[lab]` and `[cost]` were measured, `[field]` was
observed in practice but not reproduced under measurement, and `[untested]` is reasoning.
`references/provenance.md` maps each rule to what backs it. No tag is ever defended as a
stronger one than it carries.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it is the delegation doctrine the
bundle's other skills (layer-cycle, waves) build on.
