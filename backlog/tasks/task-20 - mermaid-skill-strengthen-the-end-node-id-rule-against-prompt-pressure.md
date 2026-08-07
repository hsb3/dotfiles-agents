---
id: TASK-20
title: 'mermaid skill: strengthen the ''end'' node-id rule against prompt pressure'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-04 00:43'
updated_date: '2026-08-07 00:56'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/173'
priority: low
type: chore
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #173. Harden the house rule so sessions don't regress it under user phrasing pressure.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Rule restated with adversarial examples; verified against the motivating transcript pattern
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The rule at primitives-core/skills/mermaid/SKILL.md:146 was a bare Pitfalls-table row naming two words. It now states the general shape ('end, class, or any other Mermaid keyword') and points to a new subsection at :152-166 that does the actual hardening.

The strengthening targets the real failure mode. The regression was never ignorance of the rule; it was not noticing the rule applied when the user's own vocabulary supplied the reserved word. The new text names that pressure directly — if a stage, entity, or state is genuinely called 'end', the instinct is to use it verbatim as the id, and that instinct is the trap, not an exception — then shows wrong ('load --> end') against right ('load --> fin[end]'), keeping the real stage name visible as the label.

Verified against the existing harness case rather than by assertion. harness/cases/mermaid/avoid-reserved-node-id/case.json is a prompt whose pipeline stage is literally named 'end'. Its check.py flags 'end' only in id position (adjacent to node-shape delimiters or arrow syntax) and explicitly treats 'end' inside a label as fine. Running the checker's own regex patterns against both new example lines (no harness invocation, no billed model calls): the RIGHT example produces zero violations, the WRONG example triggers exactly the violation class the checker exists to catch. So the skill's stated correct form is provably the form the checker accepts.

The AC's literal wording asks for verification against 'the motivating transcript pattern', which the card never links or excerpts — the harness case reproduces that same pattern and was used instead. Noted so the substitution is visible rather than silent.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The mermaid reserved-word rule now survives the case that broke it: a worked wrong-way/right-way example for when the user's own domain term is the reserved word, plus generalization past the two enumerated keywords so an unlisted one is still caught. Confirmed mechanically by running the existing harness checker's regexes against both examples — right passes, wrong trips the intended check.
<!-- SECTION:FINAL_SUMMARY:END -->
