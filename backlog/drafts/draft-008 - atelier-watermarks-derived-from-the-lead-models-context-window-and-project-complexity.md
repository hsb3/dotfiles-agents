---
id: DRAFT-008
title: >-
  atelier: watermarks derived from the lead model's context window and project
  complexity
status: Draft
assignee: []
created_date: '2026-08-08 15:59'
labels:
  - primitives
  - decision
dependencies:
  - DRAFT-007
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Context watermarks are currently two absolute constants — soft 70k, hard 100k — against an owner target of keeping agents under ~200k. Absolutes are wrong on two axes at once.

**Lead model.** A threshold that is prudent for a 200k window is either paranoid or useless at 1M. Tiers should be a FRACTION of the active model's context window, so they scale automatically instead of needing a re-tune per model. This depends on the model-tier mapping task, which exposes per-model window size — sequence that first.

**Project complexity.** A small repo and a sprawling monorepo do not hit degradation at the same absolute count, because the cost of a single grounding read differs by an order of magnitude. Needs a defined complexity proxy with a named default — candidates: repo file count, the token cost of a typical read set, or the number of concurrently active agents. Pick one measurable signal; do not build a scoring model.

**Overrides must be easy.** Owner requirement. Precedence needs to be explicit and documented: env var beats per-project setting beats computed default. There is a natural home for the per-project value — `.opencode/atelier.local.md` already exists as this bundle's per-project activation file, so this should extend that schema rather than introduce a second config surface.

Folds in a known gap: `context-watermark` currently gates to the MAIN session only. Telemetry measures subagents but nothing nudges them, so a worker can run hot to exhaustion unobserved. Subagent watermarks belong in this change.

Owner rulings needed: the soft/hard fractions; which complexity proxy; and whether a subagent's tier differs from the main session's.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Soft and hard tiers computed as a fraction of the lead model's context window, not as absolutes
- [ ] #2 One measurable complexity proxy chosen, with a documented default and its rationale
- [ ] #3 Override precedence documented and enforced: env > per-project activation file > computed default
- [ ] #4 Per-project override extends .opencode/atelier.local.md; no second config surface introduced
- [ ] #5 Subagent sessions get watermarks, not just the main session
- [ ] #6 Documented, non-crashing fallback when the lead model or its window size is unknown
- [ ] #7 Gate check pins the precedence chain and the unknown-model fallback
<!-- AC:END -->
