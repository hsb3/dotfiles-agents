---
name: foreman
description: >
  This skill should be used when a session takes on a substantial task and must decide how to
  split it across agents: a feature build, refactor, migration, audit, multi-file fix, or anything
  past ~30 minutes of agent work — even when the user never says "foreman" or
  "delegate", and even when the work arrived as a goal ("clean this up", "get it published")
  rather than as a list of slices. Also use when the user asks "how to split work across agents",
  mentions crews / teams / subagents, worries about token cost on a big job, or wants to size a
  job, pick a delegation architecture, choose model tiers, or reserve work for the main session —
  and when a session notices it has been reading, editing, and running commands itself for a
  long stretch without delegating. Provides the effort calibration, the five
  architectures, the pre-dispatch preconditions, the model cheat-sheet, the never-delegated floor
  and its ceiling, the brief rules, and the context-hygiene defaults.
---

# Foreman

Run the session as a foreman: size the job, pick an architecture, set the definition of done,
delegate the labor, verify the result personally. Premium session tokens buy decomposition,
judgment, and verification. They do not buy file-reading or bounded edits.

Self-contained: usable without any other skill; `rubric-panel`, `layer-cycle`, and `handoff`
extend it where named below.

**Provenance tags.** `[lab]` was measured in the inventory lab (three controlled experiments ×
three languages, anchored-rubric panels). `[cost]` comes from measured delegation-cost and
context-economics findings. `[untested]` is reasoning that has never been measured — change those
first when evidence arrives, and never defend one as if it were a finding. The map from rule to
measurement is `references/provenance.md`.

## The economic premise

Reading files, scraping logs, and making bounded edits are the cheapest work and belong on cheaper
agents. But delegation is not free: every brief written, report read, and check performed costs
briefing overhead, hallway losses, and verification. For a small job that overhead exceeds the
labor. **Sizing a job honestly, including "too small to delegate, just do it", is the first
foreman skill.** Never ceremonialize a three-tool-call task into a crew.

## Step 0 — Determine the effort level

The model in the session's lead seat IS the effort signal.

| Session model | Level | Meaning |
| --- | --- | --- |
| Opus or below | `standard` | The default — everyday foreman work |
| Fable | `deep` | A problem hard enough to justify a Fable lead |

Overrides, highest wins: the user says so; or an `effort:` key in the frontmatter of
`.claude/atelier.local.md` (check for it; absence is normal). State the level in effect when
proposing an architecture.

At **`deep`**, the session's tokens cost ~2× Opus and Fable measures at ~80–100k tokens just to get
grounded plus ~50–100k to lead — past the context watermark before real work starts `[cost]`. So:
**never self-ground** (dispatch it, read the report, not the tree); **prefer D/E at the
moderately-complex fork**, inverting standard's tiebreak; **verify in layers by default**, a
`reviewer` on every plan-changing claim; **override builders to opus** more liberally.

## Step 1 — Size the job on three axes

- **Complexity** — `trivial` → `bounded` (well-specified) → `coupled` (step N needs step N-1) →
  `architectural` (many unknowns).
- **Parallelizability** — disjoint file ownership, or a dependent chain?
- **Work-list** — do the slices already exist, or must they be discovered?

The third axis is the one sessions skip, and skipping it is the documented way a foreman ends up
doing the work itself. Work that arrives pre-sliced ("build this in three languages", "fix these
five issues") can be briefed immediately. Work that arrives as a goal ("restructure the repo",
"get this published") has no slices at t=0, so the default path is to discover them by hand — and
that is where the retained labor lands. In the lab's own record, every session whose work arrived
pre-sliced delegated heavily; every session whose work arrived as a goal delegated **nothing**
across 11+ hours and 278 self-performed tool calls `[lab]`.

**When the work-list does not exist yet, discovery is the first delegation.** Dispatch scouts
(architecture B), then size and slice from their report. Do not fix while inventorying: a defect
found during recon goes on the punch list, not into the working tree `[untested]`.

## Step 2 — Pick the architecture

| Task shape | Architecture | Session's share |
| --- | --- | --- |
| Trivial / conversational | **A. Direct** — just do it | All of it (overhead > labor) |
| Simple but token-heavy (searches, inventories, log reduction) | **B. Scouts** — parallel read-only agents | Ask, judge answers |
| Moderately complex, **parallelizable** | **C. Flat fan-out** — brief N scoped workers directly | Plan, DoD, slice, reconcile, validate |
| Moderately complex, **coupled** | **D. Lead-driven team** — one `lead` drives the chain as proxy | Brief, escalations, final validation |
| Highly complex / architectural | **E. Phased crews** — audit → fold-back → build → verify | Deep planning, design calls, every gate |

Full playbooks, including what choosing wrong looks like in each: **`references/architectures.md`**.

**B is not only a destination.** When Step 1 says the slices are unknown, B is the mandatory first
phase of C, D, and E, not an alternative to them.

**The C-vs-D fork:** parallelizable → C; coupled → D. When genuinely torn, prefer the cheaper
architecture and keep the DoD strict — a strict DoD exposes an under-powered crew fast, while an
over-powered crew silently burns budget. (At `deep` effort this inverts.) `[untested]`

## Step 3 — Satisfy three preconditions before the first dispatch

All three are cheap to write and expensive to retrofit `[lab]`.

1. **A definition of done, as independently verifiable criteria** — a command that passes, a grep
   that returns zero, an artifact that exists. Never "works well". **Include the error paths and
   the empty case**: unspecified edge cases are exactly where independent implementations diverge,
   and every divergence the lab's cross-implementation diffing surfaced traced to a case the
   contract never named.
2. **A gate that exists and has been proved red.** The DoD's command must actually fail when the
   work is wrong. A gate that cannot fail is decoration. Break something deliberately once, watch
   it fail, restore, then dispatch against it.
3. **An ownership map separating owned source from read-only config.** The gate belongs to the
   foreman. A worker that can edit the coverage threshold, the lint config, or the test that
   defines its own acceptance criteria can satisfy any brief. Workers are told: an unsatisfiable
   gate is an escalation, never a config edit. Where the project has activation on, make the map
   machine-readable — list the read-only config under `protected:` in `.claude/atelier.local.md`,
   and the `config-custody` hook enforces it (`references/activation.md`) `[untested]`.

## Model × task cheat-sheet

| Agent | Default model | Override at dispatch | Use for |
| --- | --- | --- | --- |
| `scout` | haiku (`effort: low`) | `model: sonnet` for cross-file synthesis | Read-only audit, convention check, presence/absence, log reduction, reconciliation |
| `builder` | sonnet | `model: opus` for judgment-heavy slices | Scoped edits, test writing, refactors — through coupled, costly-to-unwind slices |
| `reviewer` | opus | — (verification is where the premium pays) | Independent re-derivation of a high-impact claim or diff |
| `lead` | opus | — | Architecture-D chain proxy: drives a coupled chain, spawns builders, verifies |
| **the session** | Foreman (Opus at `standard`, Fable at `deep`) | — | The floor below — **never a spawned agent** |

**Tier is a dispatch-time decision, not an agent choice.** Default every scout to haiku and every
builder to sonnet; pass `model:` on the Agent call only when the slice demonstrably needs the
judgment. **These defaults are `[untested]`** — the lab that produced this kit dispatched opus for
every model-bearing call and never exercised the cheaper tiers, so the cutoff between "sonnet is
fine" and "needs opus" has never been measured. `references/tier-cutoff.md` is the protocol for
measuring it; run it before defending the defaults.

Per-invocation knobs (`isolation: worktree`, `maxTurns`, SendMessage continuation), agent shell
capabilities, and the git policy are in **`references/dispatch-knobs.md`**.

## The foreman floor — never delegated

1. **Decomposition and architecture choice** — the slicing IS the plan; a bad slice cannot be
   fixed downstream.
2. **Definition of done** — written before any delegation (Step 3).
3. **Judging conflicting or high-impact reports** — subagent findings are **hypotheses**. Anything
   that changes the plan gets re-derived from the cited source; dispatch a `reviewer` to do the
   re-derivation, and judge what it returns here.
4. **Final validation** — run the hard gates personally before telling the user it is done. A
   lead's proof package is evidence, not verdict.
5. **User-facing synthesis** — the user hears one coherent account from the session they hired.
6. **Contract amendment** — when a finding shows the DoD itself was incomplete, only this level
   edits it `[lab]`. Evaluation is a layer in the loop, not a verdict on it: in the lab, error-path
   quality stayed low in every round — the rubric floor under +test-first, tied for it under the
   rig — and moved only once judged findings were folded back into the spec. Gates enforce what they
   measure; they cannot invent a missing clause. Expect each amendment to surface the next layer
   of ambiguity — a contract is never finished, only converged-for-now.

## The ceiling — delegate these even though they feel like judgment

A floor with no ceiling is not a constraint; every item above stretches to cover almost any inline
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
because the foreman's own gate runs are floor work: the lab's actively-delegating sessions
measured ~7–19 delegable calls per dispatch (12.5:1 overall). What separates them from the
sessions that delegated nothing is the unbroken run: mid-fan-out solo runs clustered around 10–25
calls, the longer stretches (36–69) were grounding or closing work done by hand, and the
zero-delegation sessions ran 80–103 without a single dispatch `[lab]`. **A run of ~25 delegable
calls with no delegation is the line** — calibrated between the clusters, not measured
`[untested]`. Past it on a C/D/E job, stop and either dispatch the remaining work-list or name
which floor item this stretch is. The `delegation-watermark` hook counts the run and says so
without being asked.

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

## Verification

Rank evidence: **a loud gate > an output differential across independent producers > an
independently re-derived check > a lead's proof package > a worker's self-report** `[lab]`. If any
wave bounded its coverage (top-N, sampling, skipped cases), surface that to the user and the
backlog — **silent caps read as full coverage.**

Two techniques carry most of the weight, both in **`references/verification.md`**: the
**differential** (where two agents produce artifacts that should agree observably, the
reconciliation is a diff of their outputs, and a disagreement is usually a contract defect rather
than an implementation defect) and the **panel escalation** (a judgment-shaped claim needs three
personas scoring against written anchors with disagreement surfaced rather than averaged — the
`rubric-panel` skill implements it; `layer-cycle` drives the create → evaluate → refine loop it
feeds).

## Context hygiene

Operating defaults from measured findings `[cost]`. The `context-watermark` (UserPromptSubmit),
`delegation-watermark` (PostToolUse), and `handoff-freshness-guard` (PreCompact) hooks plus the
`handoff` skill are the enforcement layer; this skill decides when.

- **Trigger `/handoff` at a self-chosen boundary in the 60–80k band.** The economics optimum is
  ~40–60k; the buffer buys boundary quality. `context-watermark` nudges on **absolute tokens**
  (~70k soft, ~100k hard) because percent-of-window thresholds are inert against the ~967k
  auto-compact default.
- **Prefer handoff + `/clear` over `/compact`** — a fresh session reading the handoff restarts at
  ~10–20k; a compaction summary is similar in size, less curated, and carries a re-read tax.
- **Treat any ≥10-minute idle as a handoff point** — the session-break tax makes long gaps both
  expensive and a natural externalization boundary.
- **Clear after messy debugging, even below threshold** — visible prior errors raise future error
  rates independent of context length.
- **Downtier on demonstrably simple work**, gated to clearly simple tasks and paired with a strict
  DoD so an under-powered crew fails loudly and fast. The cutoff itself is unmeasured; see
  `references/tier-cutoff.md`.

## Additional resources

- **`references/architectures.md`** — the five playbooks in full.
- **`references/briefs.md`** — required fields, the worker template, the three brief rules.
- **`references/verification.md`** — evidence ranking, the differential, the panel escalation,
  aiming verification where the stack is weak.
- **`references/lead-brief.md`** — the fill-in-the-blanks architecture-D lead brief.
- **`references/migrate-at-scale.md`** — one mechanical transform across many sites.
- **`references/tier-cutoff.md`** — the protocol for measuring where cheap tiers stop being enough.
- **`references/dispatch-knobs.md`** — `isolation`, `maxTurns`, SendMessage, the git policy.
- **`references/activation.md`** — per-project enforcement: `.claude/atelier.local.md`, the
  `enforce` modes, the `protected:` map, and the worker covenant.
- **`references/provenance.md`** — which rule came from which measurement, and which are untested.
