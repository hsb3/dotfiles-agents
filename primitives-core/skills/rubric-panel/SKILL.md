---
name: rubric-panel
description: Score one or more code artifacts against an anchored rubric using a persona-diverse judge panel; produces dimension scores plus findings classified as defect, noise, spec-hole, or undeclared-commitment. Use when asked to "score this implementation", "judge these two solutions", "rate this module against a rubric", or compare competing implementations of the same spec, and when invoked by layer-cycle. For choosing between technologies, frameworks, or vendors, use tech-eval-research instead.
---

# Rubric panel

<!-- harness:claude-code -->
In Codex, first read [Codex distribution](../delegation/references/dispatch-knobs.md#codex-distribution)
for installed role setup, native dispatch, isolation prerequisites, and completion routing.
That section supplies the Codex procedures wherever this workflow names Claude Code tools.
<!-- /harness -->

Judge the artifact, not the process. Score absolutely against anchors,
never on a curve.

## Inputs (ask only for what's missing)

- **targets** — artifact path(s), implementation + tests per unit.
- **rubric** — anchored 1–5 dimensions with weights. None → offer a
  default (cold readability 20; idiomatic fit, signal-to-noise,
  architecture 15 each; type leverage, error-path robustness, test
  quality 10 each; extensibility 5).
- **contract** — the behavioral spec; defines "externally observable"
  for finding classification.
- Optional: panel size (default 3), personas (default: long-term
  maintainer, language purist, QA skeptic), effort level.

## Preconditions

Run each target's gate first — never score broken code; report the gate
failure instead. Judges are read-only.

## Process

1. Dispatch N parallel judge agents, one persona each — one dispatch per
   judge, all in a single turn so they run in parallel. Each is a
   read-only reviewer subagent with its persona carried in the prompt.
   **Every judge scores the whole field** — one judge across all targets
   keeps calibration consistent; N judges average out persona bias. Judge
   briefs contain: rubric, contract, targets, persona — nothing about
   other judges' scores, prior rounds, or expected outcomes.
2. Each score must cite concrete code. Process artifacts (TDD logs,
   commit history) earn no credit.
3. Aggregate: per-dimension mean, weighted total. A judge spread
   > 1.5 points on any dimension is **contested** — flag it, don't
   silently average.
4. Classify every finding: `defect` (behavior wrong vs contract) |
   `noise` (fails the deletion test) | `spec-hole` (behavior the
   contract doesn't pin) | `undeclared-commitment` (line serves a
   purpose nobody wrote down).
5. Write the report: score table, contested flags, findings ranked by
   severity, each with a citation. If targets form before/after pairs,
   include deltas — but note that cross-panel deltas are weak signal;
   within-panel ranking is the strong signal.

## Output

A markdown evaluation report committed alongside the code, plus a
structured findings list consumable as briefs by layer-cycle.

## Guardrails

- Judges never edit anything.
- No finding without a concrete citation (file:line or quoted code).
- Verdicts are about the artifact, never the author or the process.
