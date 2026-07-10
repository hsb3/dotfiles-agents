---
name: fable-foreman
description: >
  Run a Fable session as a foreman: pick a delegation architecture by task complexity and
  parallelizability, reserve Fable for planning / definition-of-done / final validation, and push
  execution down to cheaper agents (including an Opus-led team for coupled work). Use this whenever
  a Fable session takes on a substantial task — a feature build, refactor, migration, audit,
  multi-file fix, or anything estimated at more than ~30 minutes of agent work — even if the user
  doesn't say "foreman" or "delegate". Also use when the user asks how to split work across agents,
  mentions crews/teams/subagents, or worries about Fable token cost on a big job.
---

# Fable Foreman

Fable output tokens cost roughly 2x Opus and 5x Sonnet. Spending them on file reading, log
scraping, or bounded edits is waste; spending them on decomposition, judgment, and verification is
the point. This skill is the operating doctrine for that split: Fable is the foreman — it sizes the
job, picks the architecture, sets the definition of done, and personally verifies the result. The
crew does the labor.

The inverse also matters: delegation has overhead (briefing, hallway losses, verification). For
small jobs the overhead exceeds the labor. Sizing the job honestly — including "too small to
delegate" — is the first foreman skill.

## Step 1 — Size the job on two axes

Before touching files, classify the task:

- **Complexity**: how much judgment does it need? (trivial edit → bounded implementation →
  coupled multi-step work → architectural / many unknowns)
- **Parallelizability**: can it split into slices with disjoint file ownership, or is it a
  dependent chain where step N needs step N-1's output?

Then pick the architecture:

| Task shape | Architecture | Fable's share of the work |
| ---------- | ------------ | ------------------------- |
| Trivial or conversational | **A. Direct** — just do it | All of it (delegation overhead > labor) |
| Simple but token-heavy (searches, inventories, log reduction) | **B. Scouts** — parallel cheap read-only agents | Ask the questions, judge the answers |
| Moderately complex, parallelizable | **C. Flat fan-out** — Fable briefs N scoped workers directly | Plan, DoD, slice, reconcile, validate |
| Moderately complex, NOT parallelizable | **D. Opus-led team** — one Opus lead drives the chain as Fable's proxy | Brief, escalations, final validation |
| Highly complex / architectural | **E. Phased crews** — audit → build → verify waves, Fable runs the phase boundaries | Deep planning, design decisions, every gate |

When in doubt between two rows, prefer the cheaper architecture and keep the DoD strict — a strict
DoD catches an under-powered crew quickly, while an over-powered crew silently burns budget.

## The Fable floor — never delegated

Whatever the architecture, these stay with Fable, because they are exactly where its judgment
premium pays and because expectations and results-checking responsibility ultimately land on the
main session:

1. **Decomposition and architecture choice** — the slicing IS the plan; a bad slice can't be
   fixed downstream.
2. **Definition of done** — written BEFORE any delegation, as independently verifiable criteria
   (commands that pass, greps that return zero, artifacts that exist), never "works well".
3. **Judging conflicting or high-impact reports** — subagent findings are hypotheses; anything
   that changes the plan gets re-derived from the cited source.
4. **Final validation** — Fable runs the hard gates itself (test suite, lint, end-to-end proof)
   before telling the user it's done. A lead agent's proof package is evidence, not verdict.
5. **User-facing synthesis** — the user hears one coherent account from the session they hired.

## Architecture playbooks

### A. Direct

The task fits in a few tool calls or the validation itself needs delicate judgment. Do it; don't
ceremonialize. Signs you chose wrong: you're three files deep in mechanical edits — stop and
re-slice.

### B. Scouts

Fan out read-only Explore / general-purpose agents on cheaper models for anything where the value
is the conclusion, not the traversal. Default scouts to `haiku` — a read-only pass against a
written convention or a bounded question rarely needs more, and at 1/2 sonnet rates the scan
phase becomes nearly free; reserve `sonnet` scouts for questions needing real synthesis. Ask for
concise evidence: files, line refs, commands run, uncertainties, stop conditions hit. This is the
`efficient-fable` pattern — that skill's delegation and handoff-packet guidance applies verbatim.

### C. Flat fan-out

For parallelizable builds Fable acts as its own lead:

1. Write the plan: deliverables, DoD per slice, and the parallelism map. Externalize it (a plan
   doc or task list) so it survives compaction.
2. One slice = one owner = disjoint file scope. Shared files get a serialized chain, not parallel
   writers. State the file ownership in every brief.
3. Pick models per slice: `sonnet` for bounded, well-specified edits; `opus` for slices needing
   real judgment. Omit the override (inherit Fable) only for slices you'd otherwise keep yourself.
   For audit-and-fix sweeps, split the phases by tier: `haiku` scouts read everything and report
   violations; `sonnet` fixers touch only the violators. Paying edit-tier rates for read-only
   scanning is the most common silent overspend in a fan-out.
4. Require a handoff note per worker: what changed, why, what was deferred, what other slices
   must know.
5. Budget a reconciliation pass — parallel work always leaves drift (stale tests, rename fallout).
   Collect the punch list and give it to ONE serial agent.
6. Fable validates against the DoD and runs the gates.

### D. Opus-led team (the coupled-work pattern)

For moderately complex work that CANNOT parallelize — a dependent chain of implement → wire →
test → fix — don't keep Fable in the loop for every link, and don't fan out what can't fan out.
Spawn **one general-purpose lead agent on `model: opus`** and make it Fable's proxy:

- The lead receives a complete brief (see `references/lead-brief.md` for the template): objective,
  the DoD verbatim, constraints, worker-model guidance, evidence format, stop/escalation
  conditions.
- The lead decomposes the chain, does judgment-heavy links itself, and spawns its own `opus` or
  `sonnet` workers for bounded links (general-purpose agents can spawn sub-agents; Explore agents
  cannot).
- The lead is the **first-pass checker**: it verifies each worker's output before building on it,
  and it assembles a **proof-of-completion package** — per-DoD-criterion evidence with commands
  run and their actual output — before reporting back.
- Fable's role while the team runs: answer escalations (use SendMessage to continue the lead's
  context rather than re-briefing), and nothing else. No shadowing, no duplicate work.
- When the lead reports done, Fable **spot-checks, then validates**: re-run at least the gates and
  one or two DoD criteria independently. The lead checking the workers and Fable checking the lead
  are different layers on purpose — the lead catches worker errors cheaply; Fable catches the
  lead's blind spots (the classic failure is a plausible proof package for a subtly wrong
  mechanism).

Why an Opus lead and not Sonnet: the lead's job is mostly verification and judgment — the same
reasons those stay expensive at the Fable layer make them worth Opus at the proxy layer. Workers
doing bounded edits are where Sonnet earns its keep.

Why a lead at all, when Fable could brief the same cheap workers directly: management traffic
compounds. Every brief written, report read, and check performed in the main session lands in
Fable's ever-growing context and is re-read (at Fable cache rates) on every subsequent turn — in
long sessions, cache reads dominate the bill. The lead absorbs that chatter into a disposable
Opus-priced context and hands Fable one proof package. The per-worker model mix matters less than
where the management conversation lives.

### E. Phased crews

For architectural work with unknowns, run phases with hard boundaries: **audit** (findings
reports only, no code changes) → **build** (scoped owners per C, or leads per D for coupled
subsystems) → **verify** (adversarial checks on high-impact claims, then gates). Fable stays
deeply engaged at every phase boundary — reading findings, making design calls, re-slicing. If
the fan-out is deterministic (same operation over a known work-list), a Workflow beats hand-spawned
agents; use it only under the user's multi-agent opt-in rules.

## Briefs are handoff packets

Every delegated prompt — worker or lead — is written for an agent with zero chat context: repo
path, exact objective, in/out of scope with file ownership, the evidence format to return, the
verification commands to run, and stop conditions ("if the code doesn't match this brief, or a
command fails after a reasonable retry, stop and report — don't improvise"). Ambiguity in a brief
is Fable silently delegating a decision it was supposed to make.

## Proof of completion, not reports of completion

The job is done when the repo's own gates pass under Fable's hands — not when an agent says done.
Rank evidence: a gate that can fail loudly > an independently re-derived check > a lead's proof
package > a worker's self-report. If any wave bounded its coverage (top-N, sampling, skipped
cases), that fact goes to the user and the backlog — silent caps read as full coverage.

## Cost cheat-sheet

| Layer | Model | Use for |
| ----- | ----- | ------- |
| Foreman | Fable (the session) | plan, DoD, judge, final validation, synthesis |
| Lead / proxy | `opus` | driving coupled chains, first-pass verification of workers |
| Judgment worker | `opus` | slices where being wrong is expensive |
| Bounded worker | `sonnet` | well-specified edits, tests |
| Scanner | `haiku` | read-only audits, convention checks, log reduction, summarization |
