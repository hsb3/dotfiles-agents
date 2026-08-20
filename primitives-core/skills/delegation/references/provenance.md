# Provenance — which rule came from which measurement

Every rule in this skill carries a tag. This file is the map behind the tags, so a future session
editing the doctrine can tell a finding from a reasoned guess, and knows what to re-measure before
overturning something.

- `[lab]` — measured in the inventory lab: three controlled experiments (rules only → +test-first
  → +frozen toolchain gates) plus a defect-fix layer, each round building three independent
  implementations of one spec from scratch, scored by three-persona anchored-rubric panels (three
  panels in all: rounds 1+2 scored together, round 3 fresh, the fix layer fresh). One variable per
  round by design — with one recorded confound: round 3's frozen rig arrived bundled with new
  boundary-validation and dependency rules, so its deltas are rig-plus-hardening, not the rig
  alone.
- `[cost]` — measured delegation-cost and context-economics findings (token accounting across real
  sessions). These predate the inventory lab and are inherited from the shipped skill; their
  evidence lives in the delegation-cost record, not in lab-01.
- `[field]` — **observed in practice by the repo owner, not yet reproduced under measurement.**
  Real and repeated, but uncontrolled: no arm, no held-constant variable, no ledger. A `[field]`
  rule outranks `[untested]` reasoning and never outranks a `[lab]` or `[cost]` result. Two ways to
  get it wrong, both fatal to this file's purpose: defending one as a measurement, or discarding
  one as a guess. Each row names the experiment that would settle it.
- `[untested]` — reasoning. Never measured. Change these first when evidence arrives.

## `[lab]` rules and their measurements

| Rule | Measurement |
|---|---|
| Test-first default; RED as evidence (`briefs.md`) | Adding strict test-first as the only changed variable: +0.21 / +0.33 / +0.42 weighted per language, driven by the test dimension (3.17→5.00, 3.17→5.00, 2.67→4.50) with a type-story spillover (+1.00 on one language). The only declines anywhere were −0.50 (one language's extensibility) and −0.16 (another's readability); every weighted total rose. One implementation got shorter (537→516 lines) |
| Gate proved red before dispatch; config read-only below the strategy layer (Step 3) | The frozen-rig round produced the corpus's best idiom score (5.0 unanimous) and its own field's best type story (4.83; the corpus type best, 5.00, came from the test-first round). The rig was built first, proved red, and read-only to builders, with "if a gate seems unsatisfiable, report, don't loosen" standing. Attribution carries the rig-plus-hardening confound above |
| Gates cannot invent a missing clause; contract amendment belongs to the strategy layer (the floor's contract-amendment item) | Error-path quality stayed low in every round (round means 3.89 / 4.11 / 4.06 — the rubric floor outright in round 2, tied exactly for it in round 3). It moved only after six judged spec holes plus three defect-derived clauses were folded into a contract revision; every solution then posted its best or tied-best on that dimension (4.50–4.67) |
| Error paths and the empty case are first-class DoD content (Step 3) | Round 2's one behavioral deviation lived in a case the spec never named (behavior on zero results). Every divergence the cross-implementation diff surfaced traced to an unwritten clause; the fix-layer panel later found further divergences against written clauses — panels see what diffs cannot |
| Every constraint gets a budget, a stop condition, or a machine check (`briefs.md`) | An unbounded "constants first" rule produced a ~90-line constants wall; a usage census found 43 of 57 constants single-use, and a deletion probe (9 representative constants inlined; gate green, golden output identical) judged the class behavior-inert. It cost that solution its worst dimension, unanimously, on its round's panel |
| The differential (`verification.md`) | Cross-implementation output diffing caught two spec holes that three green gates missed: environment-dependent result sets, and a sort divergence from nanosecond-vs-millisecond timestamp precision. Full convergence (829 identical rows, identical order, under the pinned environment) came only after the contract named the precision |
| Panel protocol: persona diversity, whole-field scoring, contested flags (`verification.md`) | The lab's judging protocol across its three panels. Within-round rankings were stable and interpretable; cross-round levels were not, because later panels dug measurably deeper |
| Negative list: no cycle budgets, scores, or sibling work in worker briefs — the execution layer's context boundary (`briefs.md`) | Held across every round. Workers stayed honest and scoped; field-level issues were caught by the layers above (gates, output diffs, judge panels), never by a worker self-report, which was structurally unable to see them |
| Evidence ranking, including a manager's proof package below an independently re-derived check (`verification.md`) | Same record: a producer that also assembled the evidence catches worker errors and not its own blind spots. Renamed from "a lead's proof package" with the rename to `manager`; the ranking itself is unchanged |
| Verification aimed where the stack is weak (`verification.md`) | Recurring language signatures in the corpus — tendencies, not laws (Python's idiom lead disappeared under the frozen rig; TypeScript's type ceiling emerged only after round 1): Python weakest or tied-weakest unforced error paths in every round; Go compiler-forced robustness with an extensibility tax; TypeScript the highest variance |
| The work-list axis (Step 1) | Session-transcript reconstruction of the lab's own record: sessions whose work arrived pre-sliced made 27 dispatches against 354 own non-dispatch tool calls; sessions whose work arrived as a goal made **0** dispatches against 278 own tool calls over 11+ hours |
| The delegable-call streak figures in the ceiling | Same transcript reconstruction: actively-delegating sessions measured ~7–19 delegable calls per dispatch, 12.5:1 overall; mid-fan-out solo runs clustered around 10–25 calls, longer stretches (36–69) were grounding or closing work done by hand, zero-delegation sessions ran 80–103 without a dispatch. The ~25 line drawn from these clusters is `[untested]`, below |

## `[cost]` rules

| Rule | Measurement |
|---|---|
| Handoff in the 60–80k band; absolute-token watermarks | Economics optimum ~40–60k, buffered to 60–80k for boundary quality. Percent-of-window thresholds are inert against the ~967k auto-compact default |
| Handoff + `/clear` over `/compact` | Fresh session restarts at ~10–20k; compaction summaries are similar in size, less curated, and carry a model-side re-read tax |
| ≥10-minute idle is a handoff point | Session-break (TTL) tax |
| Clear after messy debugging | Visible prior errors raise subsequent error rates independent of context length |
| **A `manager` absorbs management chatter** — the mechanical case for the management layer | Every brief and report in the main session lands in the re-read prefix and is paid for at cache rates on every subsequent turn. At `standard` effort the manager is the same model tier as the session, so the layer buys context absorption, not tier arbitrage |
| Fable-driven grounding costs ~80–100k before work starts | The `deep` effort calibration |

The management-chatter row moved in this revision from a footnote inside the architecture-D
playbook to a pillar of the layer model in `SKILL.md` ("Why three layers pay"). Its wording and its
`[cost]` tag are unchanged; only its prominence and the agent's name changed. It is the one
*measured* reason the management layer pays for itself, and it should be quoted as such rather than
merged with the `[field]` specialization claim below.

## `[field]` rules

| Rule | The observation | What would settle it |
|---|---|---|
| **Three layers is the default for anything non-trivial**; collapsing management is the exception (`SKILL.md`, "The three layers") | The repo owner's own practice: for anything except trivial tasks there is good reason to run all three layers, because each layer's job and context differ enough that specialization beats fewer layers with larger prompts. Stated by the owner as empirical, explicitly not as a measurement, with proof deferred to harness and eval runs | Run one non-trivial job under two arms: with a manager layer, and collapsed to strategist plus execution. Hold brief quality and the definition of done constant across arms, or the result measures prompt care rather than layer count. Report wall-clock, total tokens, and defects found in reconciliation per arm. Take per-layer token cost only from a delegation ledger that records each subagent's own agent type, model, and context tokens rather than the parent session's. A backlog card is open for exactly this |
| **When genuinely torn between C and D, take D** (`SKILL.md`, Step 2) | The tiebreak the default above implies, and the direct inversion of the retired guidance | The same experiment; an inconclusive result leaves the default standing and is recorded as inconclusive rather than resolved toward either prior |

## `[untested]` rules — change these first

| Rule | Why it is unmeasured | What would settle it |
|---|---|---|
| Cheat-sheet model-tier defaults (scout=haiku, builder=sonnet) | The lab dispatched opus for every model-bearing call and never exercised cheaper tiers | `tier-cutoff.md` |
| The architecture matrix (A–E) | Never A/B'd; no run has compared the same job under two architectures | Run one moderately-complex job as C and as D, compare wall-clock, tokens, and defects found in reconciliation. This is the same experiment the `[field]` rows name, seen from the architecture side |
| The collapse conditions (work-list final, slices independent in outcome, returns are notes not material, reconciliation mechanical) | Reasoning that operationalizes the `[field]` default. The conditions were derived from the `[cost]` context mechanism, not observed as a set | Record which condition was violated on each job that had to be promoted from C to D mid-flight; a condition that never predicts a promotion is not earning its place |
| The ceiling list ("delegate these anyway"), including the punch-list discipline | Derived from the lab's transcript record, not from a controlled comparison | Track solo-run length across ten real jobs with the watermark hook; see whether the ~25 line predicts anything a human would call a miss |
| The ~25-call solo-run threshold | Calibrated, not measured. Observed on real transcripts: delegating sessions' solo runs measured 6–69 (median ~18, mean ~24 across 14 runs; the 36, 47, and 69 stretches were pre-dispatch grounding or closing work done by hand); zero-delegation sessions ran 80, 93, and 103. 25 sits above the typical mid-fan-out run and below every zero-delegation session — it will fire on the long retained-labor stretches inside delegating sessions, which the doctrine reads as correct fires. A defensible starting line and nothing more | Collect the streak distribution the hook logs across a month of real work and move the line to where the clusters actually separate |
| "Discovery is the first delegation" | Follows from the work-list finding but has not been run as a treatment | Take two comparable emergent-work jobs; scout-first on one, hands-on recon on the other |
| The custody enforcement model (`activation.md`: worker covenant injection, advisory/strict path custody) | Mechanism proven by fixtures and an adversarial matrix; no real project has run under it, so its effect on worker behavior is unmeasured | Run one project under `advisory` for a month; count would-deny rows and false positives in the `config-custody` stream; graduate to `strict` and watch whether escalations replace route-arounds |

## What the layer model replaced, and on what evidence

Recorded because a default was inverted, and the inversion must not read as a finding.

| Retired rule | Tag it carried | Replacement | Tag |
|---|---|---|---|
| "When genuinely torn, prefer the cheaper architecture and keep the DoD strict" | `[untested]`, with this file recording "Never A/B'd; no run has compared the same job under two architectures" | Three layers is the default; collapse management only when every collapse condition holds; when torn, take D | `[field]` for the default and the tiebreak; `[untested]` for the conditions |
| The management layer presented as one architecture among several | untagged framing, no evidence claim | The management layer presented as standing, with A/B/C described as collapsing it | as above |
| "At `deep` effort, prefer D/E, inverting standard's tiebreak" | `[cost]`-derived calibration | At `deep`, read the collapse conditions strictly; nothing inverts because D is already the default | unchanged calibration, restated |

**Nothing measured was overturned.** The replaced tiebreak was self-labelled unmeasured reasoning,
and the replacement is an uncontrolled field observation. A `[field]` default beating an
`[untested]` guess is the honest reading of the evidence and is not a result. Every `[lab]` and
`[cost]` row above survived the rewrite; the only `[cost]` row that changed at all is the
management-chatter row, which changed in prominence and agent name, not in content.

## Origin

The delegation doctrine derives from an upstream delegation skill, re-homed here self-contained;
the context defaults from the measured delegation-cost findings; the preconditions, the work-list
axis, the differential, the contract amendment, and the bounded-constraint rule from the inventory
lab. The three-layer model and its vocabulary come from the repo owner.

## Maintaining this file

When a rule changes, change its row. When a rule is added, add a row with an honest tag — an
untagged rule reads as measured, which is the specific failure this file exists to prevent.

Tags move in one direction only, and only on evidence: `[untested]` or `[field]` becomes `[lab]` or
`[cost]` when an experiment named in its "what would settle it" column has actually been run, and
the row then records what was run. A tag never drifts upward because a rule has been in the file a
long time or because a session found it persuasive.
