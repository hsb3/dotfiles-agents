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
  Sub-briefs, first-pass checking, and a proof package back. A chain is sized twice before
  it is dispatched — how wide it may be, and whether one manager context can pay for it to
  the end. A brief too long for one manager is pre-split, or told to hand its remainder to
  a successor; it is never compacted mid-chain. Inside the chain, the expensive and least
  reversible proof runs before any further polish on a green link, and each link is
  committed as it lands.
- **Execution — `scout`, `builder`, `reviewer`**, each working from a curated zero-history brief:
  only the minimum relevant project facts, references, and tools. The brief is decomposed to a
  simple leaf and uses the least costly capable tier; frontier belongs only to the root strategist.
  Measure inherited startup context rather than inferring it from a short prompt. Context warnings,
  where a harness emits them, remain advisory checkpoints with no automatic worktree mutation.

## Sizing a brief

A job is sized on four axes, and the fourth is the brief itself: how much material its
owned-file list actually is. `scripts/scope.py` totals that list — files, bytes, lines, and how
many are binary — before anything is dispatched, and folds in nothing it cannot measure: a glob,
a directory, a missing or unreadable path is named with its reason and turns the exit code red,
so the number reads as a floor rather than a total. `SKILL.md` carries the threshold above which
a brief is split, and the one answer each unresolved entry gets.

Preconditions are checked the same way, at dispatch time rather than at authoring time: a gate
has to be shown red on a break inside the very files the worker will change, since a gate with
no subjects and a gate with fifty report the same green, and every factual premise a brief rests
on is re-derived against the tree as it stands when the brief goes out.

## Findings outside a brief's scope

A finding a worker or a manager turns up outside its own file scope folds before it is filed. A
sibling site of the same defect is fixed in the same landing; a finding that belongs to an open
item is commented onto that item; a finding with no home goes on the wave's hardening list; and
only what survives all three is filed as one new item, never in draft. `SKILL.md`,
`references/manager-brief.md`, and the `manager` and `reviewer` agent contracts state that order
in the same words, so the four cannot drift apart.

## Waiting

A separate failure the layer model alone does not prevent: an agent blocking on something
that cannot arrive. Only `manager` may send messages, enforced by tool availability or a guard, so a message
to a live execution agent can never receive an intermediate reply; a self-adopted stop condition that names no producer can never
be met; and a slow worker is indistinguishable from a dead one without a check. It also runs
the other way: completion routing depends on the harness. Keep the dispatcher mid-turn through
fan-in; a report that lands above instead gets relayed back down verbatim rather than absorbed. `references/waiting.md` holds the rules, the
completion routing, and the liveness check.

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
named branch, and may not `git stash` in a tree it shares with a peer), `handoff`, `watermark`
(per-project context thresholds for the `/handoff` nudge, each sub-key falling back to the value
the hook computes from the model's own window), and `effort`.
It also records which copy of the activation file a hook reads when the worker is running inside
a linked worktree — including that the same fallback covers what the file *names*, so a
`handoff:` path and its freshness stamp resolve through the main checkout too, and that the
worktree's own committed copy currently steers `config-custody` alone — and the design
commitments behind the enforcement layer: fail-open everywhere, custody scoped to subagents so
the strategy layer is never restricted, and each guard stating its own ceiling instead of
implying containment it does not have.

## Reading the evidence

Every rule carries a provenance tag: `[lab]` and `[cost]` were measured, `[measured]` was
reproduced under controlled measurement outside the lab rig, `[field]` was observed in practice
but not reproduced under measurement, and `[untested]` is reasoning. `references/provenance.md`
maps each rule to what backs it. The ranking is part of the doctrine: `[field]` outranks
`[untested]`; `[measured]` outranks `[field]` but lacks the cross-round comparability `[lab]`
carries; and no tag is ever defended as a stronger one than it carries. A run that measured
something but did not settle the rule it aimed at is recorded there as inconclusive, keeping its
old tag — an experiment is not an upgrade.

The change-scope split threshold is the standing worked example of a rule whose evidence and
whose prescription carry different weight. Both halves of its boundary are measured — a bimodal
file-count distribution across merged history, and a worker-context median that runs out around
the same place — while the rule drawn across them is not, because nothing has compared a split
brief against an unsplit one. The two datasets cannot even be joined: the delegation ledger
records no owned-file list, so brief scope and worker context share no key. Adding that field is
what would upgrade the tag, and until it exists the rule stays `[untested]` however often it is
applied. The figures themselves are recorded in `references/provenance.md` with their n and the
date they were read, never in the doctrine prose: both corpora are still growing, one of them is
appended to live, and independent derivations of the same figure have already disagreed.

## Shared with the opencode port

These references are one text with two copies (`docs/atelier-parity.md`); the peer lives in
`dotfiles-agents-oc`. A passage that is true of only one harness belongs in a
`<!-- harness:claude-code -->` block, never in the neutral prose the parity gate compares — that
includes anything naming `protected-branches:`, `worker-git-scope-guard`, or how this harness
resolves a worker's relative paths, none of which have an opencode counterpart.

Choose the tier a task needs independently of its role; each harness defines how that
tier is configured.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it is the delegation doctrine the
bundle's other skills (layer-cycle, waves) build on.

## Codex

Activation uses the sole configured native agent directory or `.agents` for multiple
agents. The activation skill defines safe migration, overrides and worktree precedence.

Uses the same workflow with generated project roles and native worker routing. See the
[Codex distribution procedures](references/dispatch-knobs.md#codex-distribution)
for setup, ownership-safe refresh, role names, and completion handling.

Codex managers may assemble verified child commits on their own worktree branch; final
project integration remains with the strategist. Native role setup enables the required nesting.

Atelier policy selection follows configured agent directories, using `.agents` for
multiple agents; setup migrates identical policies safely and runtime reads stay read-only.

Codex dispatch setup uses activation `codex-setup` followed by `check --harness codex`.
Current managed global roles avoid redundant local profiles; explicitly refresh stale globals
with `codex-setup --refresh-global`, so profile currency and policy placement stay consistent.
