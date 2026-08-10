---
id: TASK-046
title: >-
  Measure the three-layer default: does specialization beat fewer layers with
  larger prompts?
status: To Do
assignee: []
created_date: '2026-08-07 01:45'
updated_date: '2026-08-10 02:26'
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
Promotes TASK-045's [field]-tagged three-layer-default claim to a measured result, or refutes it: for non-trivial work, running all three layers (strategist / manager / execution) beats collapsing to two, because each layer's job and context differ enough that three focused prompts outperform two larger ones. The prior guidance said the opposite ("prefer the cheaper architecture") and was itself untested — no run had compared the same job under two architectures. TASK-036 (2026-08-07) fixed the delegation ledger to record each subagent's own type, model, and context tokens rather than the parent session's; pre-fix ledger rows are not comparable.

Run the same moderately-complex job under two arms — with a manager layer, and collapsed to strategist plus execution — holding brief quality and definition of done constant, so the only variable is layer count.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The same non-trivial job runs under both arms (manager layer included vs. collapsed to strategist plus execution), with brief quality and definition of done held constant
- [ ] #2 Per-layer token cost is read only from the post-2026-08-07 delegation ledger; pre-fix rows are excluded
- [ ] #3 Wall-clock, total tokens, and defects found in reconciliation are reported per arm
- [ ] #4 The [field] tag on the three-layer default is promoted to measured or the default is reverted, and the provenance map records which
- [ ] #5 An inconclusive result is recorded as inconclusive rather than resolved toward the prior
<!-- AC:END -->
