---
id: TASK-046
title: >-
  Measure the three-layer default: does specialization beat fewer layers with
  larger prompts?
status: To Do
assignee: []
created_date: '2026-08-07 01:45'
labels:
  - evals
milestone: m-3
dependencies: []
priority: medium
type: spike
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Promotes the [field] tag on TASK-045's three-layer default to a measured result, or refutes it.

The claim, from the owner 2026-08-07: for anything except trivial work, running all three layers (strategist / manager / execution) beats collapsing to two, because each layer's job and context differ enough that three focused prompts outperform two larger ones. The owner has field evidence and asked that it be proven in harness/eval runs rather than asserted.

This matters more than a normal doctrine question because of what it replaces. The old guidance said the opposite — 'when genuinely torn, prefer the cheaper architecture' — and carried [untested], with the provenance map recording 'Never A/B'd; no run has compared the same job under two architectures.' So the repo has now flipped a default without measuring either side. That is defensible (a [field] observation outranks an admitted guess) but it is not settled, and the skill's own rule is that a tag must never be defended as if it were a finding.

What makes this newly possible: the delegation ledger was fixed 2026-08-07 (TASK-036) and now records each subagent's own agent type, model, and context tokens rather than the parent session's. Before that fix no honest per-layer cost measurement existed. Note the ledger's pre-fix history is not comparable and must be excluded.

The experiment the old provenance map already specifies: run one moderately-complex job under two architectures and compare wall-clock, tokens, and defects found in reconciliation. Extend it to the layer question — the same job with a manager layer and without.

Confounder to control for, or the result will be meaningless: the three-layer run must not simply get better briefs. Hold brief quality and the definition of done constant across arms, so the variable is the layer count and not the care taken writing prompts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The same non-trivial job runs under both arms (with a manager layer, and collapsed to strategist plus execution) with brief quality and definition of done held constant
- [ ] #2 Per-layer token cost is read from the post-2026-08-07 delegation ledger only, with pre-fix rows excluded
- [ ] #3 Wall-clock, total tokens, and defects found in reconciliation are reported per arm
- [ ] #4 The [field] tag on the three-layer default is either promoted to a measured tag or the default is reverted, and the provenance map records which
- [ ] #5 If the result is inconclusive, that is recorded as such rather than resolved toward the prior
<!-- AC:END -->
