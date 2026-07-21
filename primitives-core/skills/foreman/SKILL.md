---
name: foreman
description: >
  This skill should be used when a session takes on a substantial task and must decide how to
  split it across agents: a feature build, refactor, migration, audit, multi-file fix, or anything
  estimated at more than ~30 minutes of agent work — even when the user never says "foreman" or
  "delegate". Also use when the user asks "how to split work across agents", mentions crews / teams
  / subagents, worries about token cost on a big job, or wants to size a job, pick a delegation
  architecture, choose model tiers, or reserve work for the main session. Provides the two-level
  effort calibration (standard for an Opus-led session, deep for Fable-led), the decision
  matrix (five architectures), a model×task cheat-sheet bound to this plugin's agents, the
  never-delegated floor, brief templates, and the findings-backed context-hygiene defaults.
---

# Foreman

Run the current session as a foreman: size the job, pick a delegation architecture, set the
definition of done, delegate the labor, and personally verify the result. The premium session's
tokens are the scarce resource — spend them on decomposition, judgment, and verification, not on
file-reading or bounded edits.

This skill is self-contained: it bundles the delegation doctrine and the context-management
defaults. No other skill needs to be installed for it to work.

## The economic premise

Premium output tokens are for decomposition, judgment, and verification — reading files,
scraping logs, and making bounded edits are the *cheapest* work and must be pushed down to cheaper
agents. But delegation is not free: every brief written, report read, and check performed carries
overhead (briefing cost, hallway losses, verification). For a small job that overhead exceeds the
labor. **Sizing a job honestly — including "too small to delegate, just do it" — is the first
foreman skill.** Do not ceremonialize a three-tool-call task into a crew.

## Step 0 — Determine the effort level

The kit runs at one of two effort levels, calibrated to which model sits in the session's
lead seat. **The model choice IS the effort signal** — derive the default from the model this
session runs on; no configuration needed:

| Session model | Level | Meaning |
| --- | --- | --- |
| Opus or below | `standard` | The default — everyday foreman work |
| Fable | `deep` | A problem hard enough to justify a Fable lead |

Overrides, highest wins: (1) the user says so in conversation; (2) an `effort: standard`
or `effort: deep` key in the YAML frontmatter of `.claude/foreman-kit.local.md` in the
project (check for it; absence is normal). State the level in effect when proposing an
architecture.

**At `standard` (Opus-led)** the rest of this skill applies as written — its defaults are
already calibrated for an Opus session. One correction to old habit: a spawned `lead` is the
*same tier* as the session, so architecture D buys **context absorption** (management
chatter stays out of the session's ever-growing, re-read prefix), not tier arbitrage —
still worth it for long chains, but not a reflex.

**At `deep` (Fable-led)** the session's tokens cost ~2× Opus, and the measured overhead of
Fable leading directly is ~80–100k tokens just to get grounded plus ~50–100k more to lead —
past the 70k watermark before real work starts. So:

- **Never self-ground.** Dispatch the grounding — an opus `lead` or a scout wave reads the
  repo and reports back; the session reads the report, not the tree. Fable reading files is
  the single largest avoidable spend at this level.
- **Prefer D/E at the moderately-complex fork** (inverts standard's cheaper-architecture
  tiebreak — the per-token premium justifies the extra delegation layer).
- **Layered verification by default** — a `reviewer` pass on every plan-changing claim, not
  only the high-impact ones.
- **More liberal `model: opus` overrides on builders** for coupled or costly-to-unwind
  slices.

## Step 1 — Size the job on two axes

Classify before touching files:

- **Complexity** — how much judgment: `trivial` → `bounded` (well-specified) → `coupled`
  (step N needs step N-1) → `architectural` (many unknowns).
- **Parallelizability** — can it split into slices with **disjoint file ownership**, or is it a
  **dependent chain** where each step consumes the previous step's output?

## Step 2 — Pick the architecture

| Task shape | Architecture | Session's share |
| --- | --- | --- |
| Trivial / conversational | **A. Direct** — just do it | All of it (overhead > labor) |
| Simple but token-heavy (searches, inventories, log reduction) | **B. Scouts** — parallel read-only agents | Ask, judge answers |
| Moderately complex, **parallelizable** | **C. Flat fan-out** — brief N scoped workers directly | Plan, DoD, slice, reconcile, validate |
| Moderately complex, **coupled** (not parallelizable) | **D. Lead-driven team** — one `lead` drives the chain as proxy | Brief, escalations, final validation |
| Highly complex / architectural | **E. Phased crews** — audit → build → verify waves | Deep planning, design calls, every gate |

**The moderately-complex fork (C vs D):** parallelizable → **C**; coupled → **D**. When genuinely
torn, **prefer the cheaper architecture and keep the DoD strict** — a strict DoD exposes an
under-powered crew fast, while an over-powered crew silently burns budget. (At `deep` effort
this tiebreak inverts — see Step 0.)

### Architecture playbooks

**A. Direct.** The task fits in a few tool calls, or the validation itself needs delicate
judgment. Do it. Sign you chose wrong: three files deep in mechanical edits — stop and re-slice.

**B. Scouts.** Fan out read-only `scout` agents for anything where the value is the conclusion,
not the traversal. The scout defaults to haiku; override the dispatch model to sonnet only when
the question needs real cross-file synthesis. Ask for concise evidence: `path:line`, commands
run, uncertainties, stop conditions hit.

**C. Flat fan-out** (parallelizable builds — the session is its own lead):
1. Write the plan — deliverables, DoD per slice, and the **parallelism map**. Externalize it (a
   plan doc / task list) so it survives compaction.
2. **One slice = one owner = disjoint file scope.** Shared files get a *serialized chain*, not
   parallel writers. State file ownership in every brief.
3. Pick a model per slice at dispatch: `builder` on its sonnet default for bounded
   well-specified edits; `builder` with `model: opus` for slices where being wrong is expensive.
   For audit-and-fix sweeps, split by role — `scout` agents read everything and report
   violations, `builder` fixers touch only violators. Paying edit-tier rates for read-only
   scanning is the most common silent overspend.
4. Require a **handoff note per worker**: what changed, why, the verification commands the
   worker ran **with their actual output** (workers have shell — make the brief demand proof,
   not claims), what was deferred, what other slices must know.
5. Budget **ONE serial reconciliation pass** — parallel work always leaves drift (stale tests,
   rename fallout). Give the punch list to a single agent; do not fan out cleanup.
6. The session validates against the DoD and runs the gates itself.

**Named playbook — migrate-at-scale.** The recurring C shape of one mechanical transform
repeated across many sites (a rename, an API-signature change, a codemod) has its own
dispatchable playbook: discovering and slicing the site inventory, a mechanical-transform brief
template for cheap-model workers, what stays with the foreman (transform spec, site inventory,
odd-site judgment calls), and the grep-zero + full-suite + no-silent-caps gates that close it out.
See **`references/migrate-at-scale.md`**.

**D. Lead-driven team** (coupled work — a dependent chain implement → wire → test → fix):
Spawn **one `lead`** as the session's proxy. Give it the full brief (see
`references/lead-brief.md`): objective, DoD verbatim, constraints, worker-model guidance, evidence
format, stop/escalation conditions. The lead decomposes the chain, does judgment-heavy links
itself, and spawns its own `builder` workers (sonnet default, opus override) for bounded links,
steering a spawned worker onward via its own SendMessage rather than re-briefing. The lead is the
**first-pass checker** — it verifies each worker's output before building the next link, and
assembles a **proof-of-completion package** (per-DoD-criterion evidence, commands + actual output).
While the team runs, the session answers escalations only — **use SendMessage to continue the
lead's context, never re-brief** (a re-brief discards the accumulated context that is most of what
the Opus lead cost). When the lead reports done, the session **spot-checks, then validates**: the
lead catches worker errors cheaply; the session catches the lead's blind spots (classic failure: a
plausible proof package for a subtly-wrong mechanism). This is **layered verification** on purpose.

Why a lead at all: management traffic compounds. Every brief and report in the main session lands
in the ever-growing prefix and is re-read (at cache rates) every subsequent turn. The lead absorbs
that chatter into a disposable Opus-priced context and hands back one package.

**E. Phased crews** (architectural work with unknowns): hard phase boundaries — **audit**
(findings reports only, no code changes) → **build** (C owners, or D leads for coupled subsystems)
→ **verify** (adversarial checks on high-impact claims, then gates). Stay deeply engaged at every
boundary: read findings, make design calls, re-slice.

## Model × task cheat-sheet

Bind every delegated slice to the plugin's concrete agents:

| Agent | Default model | Override at dispatch | Use for |
| --- | --- | --- | --- |
| `scout` | haiku (`effort: low`) | `model: sonnet` for cross-file synthesis | Read-only audit, convention check, presence/absence, log reduction, reconciliation |
| `builder` | sonnet | `model: opus` for judgment-heavy slices | Scoped edits, test writing, refactors — through coupled, costly-to-unwind slices |
| `reviewer` | opus | — (verification is where the premium pays) | Independent first-pass review of a high-impact claim or diff |
| `lead` | opus | — | Architecture-D chain proxy: drives a coupled chain, spawns its own builders, verifies |
| **the session** | **Foreman** (Opus at `standard` / Fable at `deep`) | — | The floor below — **never a spawned agent** |

**The tier decision is a dispatch-time decision, not an agent choice.** Default every scout to
haiku and every builder to sonnet; pass `model: sonnet`/`model: opus` on the Agent call only
when the slice demonstrably needs the judgment (this is also the H8 A/B mechanism). The
per-invocation `model` parameter overrides the definition's default.

**What the roles can actually do (v0.4.0):** builder/reviewer/lead have full shell (Bash) —
briefs should require them to run their own verification commands and paste output. Read-only
git (`status`/`diff`/`log`/`show`) is allowed to every shell-bearing agent; **mutating git
(commit/push/rebase/reset/checkout) is reserved to the session** by prompt-level policy — the
tool layer no longer blocks it, so treat any worker git mutation in a diff as a protocol
breach. The scout remains deliberately Bash-less (hard read-only guarantee).

**Other per-invocation knobs** (set on the Agent call, not in the definitions):
`isolation: worktree` when parallel workers genuinely must mutate the same files (disjoint
file scopes are cheaper — prefer them); `maxTurns` as a per-wave cap tighter than the
definitions' backstops (scout 15 · builder 50 · reviewer 30). Continue an existing worker with
SendMessage instead of re-briefing — a re-brief discards the context already paid for.

## The foreman floor — never delegated

Whatever the architecture — and at either effort level — these stay with the session,
because they are exactly where its judgment premium pays and where the responsibility
ultimately lands:

1. **Decomposition & architecture choice** — the slicing IS the plan; a bad slice can't be fixed
   downstream.
2. **Definition of done** — written BEFORE any delegation, as independently verifiable criteria
   (a command that passes, a grep that returns zero, an artifact that exists), **never "works
   well"**.
3. **Judging conflicting / high-impact reports** — subagent findings are **hypotheses**; anything
   that changes the plan gets **re-derived from the cited source** (use `reviewer` for an
   independent re-derivation).
4. **Final validation** — run the hard gates yourself (test suite, lint, end-to-end proof) before
   telling the user it's done. A lead's proof package is evidence, not verdict.
5. **User-facing synthesis** — the user hears one coherent account from the session they hired.

**Proof of completion, not reports of completion.** Rank evidence:
**a loud gate > an independently re-derived check > a lead's proof package > a worker's
self-report.** If any wave bounded its coverage (top-N, sampling, skipped cases), surface that to
the user and the backlog — **silent caps read as full coverage.**

## Briefs are handoff packets

Every delegated prompt — worker or lead — is written for an agent with **zero chat context**.
Required fields:

- **Repo path** (absolute) and environment / working commands.
- **Exact objective** — what must exist when done, and why (enough to make good calls).
- **In / out of scope, WITH file ownership** — which files this agent owns; what is report-only.
- **Evidence format** to return.
- **Verification commands** to run.
- **Stop conditions** — "if the code doesn't match this brief, or a command fails after a
  reasonable retry, stop and report — don't improvise."

For architecture D, fill the full lead template in **`references/lead-brief.md`**. Ambiguity in a
brief is the session silently delegating a decision it was supposed to make.

## Context hygiene — the findings layer

These operating defaults come from measured delegation-cost findings and are
what make this a foreman *kit*, not just delegation doctrine. The plugin's **`context-watermark`**
(UserPromptSubmit) and **`handoff-freshness-guard`** (PreCompact) hooks plus the bundled **handoff**
skill are the enforcement layer — this skill is the judgment layer that decides *when*.

- **Trigger `/handoff` at a self-chosen boundary in the 60–80k band.** The pure-economics optimum
  is ~40–60k tokens; the buffer to ~60–80k buys boundary quality (nudge resolves at a natural task
  boundary, not mid-flight). The `context-watermark` hook nudges at a **soft ~70k / hard ~100k
  absolute-token** watermark — **absolute tokens, not percent of window** (percent-of-1M
  thresholds are inert; the shipped ~967k auto-compact default effectively never fires).
- **Prefer handoff + `/clear` over `/compact`.** A fresh session reading the handoff restarts at
  ~10–20k context; a compaction summary is similar but less curated, and carries a hidden model-side
  re-read tax.
- **Treat any ≥10-minute idle as a handoff + `/clear` point** — the session-break (TTL) tax makes
  long gaps both expensive and a natural externalization boundary.
- **Clear after messy debugging, even below threshold** — visible prior errors raise future error
  rates (self-conditioning), independent of context length.
- **Downtier to cheaper models on demonstrably simple work.** Sonnet held Opus-grade quality at
  ~half the cost on Exercism-grade tasks. **Caveat:** there is no difficulty-cutoff finder yet —
  gate aggressive downtiering to *clearly* simple tasks, and keep a **strict DoD** so an
  under-powered crew fails loudly and fast.

## Credit

The delegation doctrine derives from an upstream delegation-foreman skill, re-homed here
self-contained. The context-management defaults (thresholds, handoff-over-compact, the ≥10-min
rule, downtiering) come from measured findings on delegation cost and context economics.

## Additional resources

- **`references/lead-brief.md`** — the fill-in-the-blanks architecture-D lead-agent brief template.
- **`references/migrate-at-scale.md`** — the named architecture-C playbook for fanning a
  mechanical transform out across many sites (site inventory, worker brief template,
  reconciliation, gates, when not to fan out).
