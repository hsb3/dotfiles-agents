---
id: TASK-039
title: 'layer-cycle: proportionality rule for the evaluate step on small diffs'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-06 23:49'
updated_date: '2026-08-07 00:56'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/256'
priority: low
type: docs
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #256: layer-cycle's process mandates a full persona-diverse rubric-panel as the evaluate step every cycle. Running a bug-fix wave of five backlog bugs (diffs from one line to ~50 lines), a full panel per cycle would have cost more than the builds. What actually worked and converged in <=2 cycles per task: a one-line diff got a foreman spot-check with no agent (observed-red evidence made the assertion non-vacuous); 20-50-line diffs got a single adversarial reviewer (re-derive + re-run + attack), which caught a real residual defect; module-scale artifacts would earn the panel's cost (did not arise in that run). The current text reads as panel-always, which either burns budget on trivial cycles or trains users to skip the evaluate step entirely. Checked #260: only layer-cycle/README.md's foreman-kit -> atelier rename touched this skill, so the sizing gap is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 layer-cycle (and/or the foreman skill's cheat-sheet) states a sizing rule for the evaluate step: spot-check vs single reviewer vs rubric-panel, chosen by diff size / coupling / stakes
- [x] #2 The panel is explicitly framed as reserved for module-scale or contested artifacts, not the default for every cycle
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The evaluate step at primitives-core/skills/layer-cycle/SKILL.md:25-37 now selects depth by diff size rather than mandating a panel every cycle. Three tiers, each with a trigger a session can evaluate about its own diff: Trivial (~10 changed lines or fewer, one file, no interface change) → self spot-check against the contract, no dispatch; Bounded (up to ~50 changed lines, or a few files with no new public interface) → one adversarial reviewer; Module-scale or contested (a new module, a public interface/contract change, or a prior cycle's judge spread > 1.5) → rubric-panel, explicitly framed as the panel's reserved case.

The card supplied 1-line, 20-50-line, and module-scale anchors but no cutoff between 1 and 20; a ~10-line boundary was chosen to fill that gap rather than inventing new evidence, and is recorded here as a judgment call, not a finding.

Three places elsewhere in the skill assumed an unconditional panel and were part of the fix: SKILL.md:50-51 ('record the cycle's scores and diff' presumes a score exists every cycle) now reads 'the cycle's outcome (rubric scores, when a panel ran)'; the frontmatter description at SKILL.md:5 and README.md:4 both said 'translating panel findings' and now say 'translating findings'; README.md:9-13 described dispatching each evaluation as a worker brief, which contradicts the new trivial tier, and now states the evaluate step scales by tier. SKILL.md:57-58 was deliberately left alone — 'if scores drop' is a conditional guardrail, not a mandate to compute scores.

Out of scope by design: the foreman skill's cheat-sheet, named in the card as an optional second home for this rule. A sibling worker owned adjacent files during this wave.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
layer-cycle no longer overcosts small diffs. The evaluate step picks its depth from the diff's size, coupling, and stakes, and the full rubric-panel is now the reserved case for module-scale or contested work instead of the every-cycle default. Verified by reading the skill for residual unconditional-panel language after the edit; make ci green.
<!-- SECTION:FINAL_SUMMARY:END -->
