---
id: TASK-29
title: Promote the lab-setup skill from the EVALS workbench into the collection
status: To Do
assignee: []
created_date: '2026-08-06'
updated_date: '2026-08-06'
labels:
  - skills
  - bundles
dependencies: []
priority: medium
type: feature
ordinal: 2900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The inventory lab (`~/Developer/EVALS/lab-01-package-inventory`) produced four
generalized artifacts. Three landed here: `rubric-panel`, `deletion-pass`, and
`layer-cycle` are primitives-core sources shipped through foreman-kit (PR #235,
kit 0.7.0; currently published in 0.7.1). The fourth never did.

That fourth is `lab-setup` — the cross-lab methodology, promoted out of the lab
on 2026-08-05 and packaged as a skill at `~/Developer/EVALS/.claude/skills/lab-setup/`
(the lab's LAB-GUIDE.md became its SKILL.md; the lab's RUNBOOK.md became a
reference). It has zero presence in this repo: no `primitives-core/skills/` source,
no roster entry in `primitives-core.yaml`, no `translation.yaml` disposition, no
card until this one.

What it covers: standing up and running an EVALS lab — a controlled experiment
where agents build a program (the instrument) to produce process knowledge (the
product). Subject choice, contract/RULES.md authoring, rubric authoring, toolchain
rig freezing, builder briefs, judging, and lab closeout.

Why now: the skill is explicitly framework-not-instance and self-describes as a
living skill that every lab updates. Left in a single workbench repo, the next lab
either hand-copies it or diverges from it, and the review trio it pairs with is
already distributed — the recipe ships without the kitchen. decision-5 deferred
extracting EVALS to its own repo (dev is the workbench); that defers the *repo*,
not this skill's distribution.

Open sub-questions for whoever takes it:
- **Bundle home** — foreman-kit alongside the review trio it composes with, a
  standalone one-skill plugin, or code-desk. Ruled against the bundle-composition
  principle from task-9.
- **Target lane** — it drives judge panels through Claude Code dispatch the same
  way `rubric-panel` and `layer-cycle` do, both of which are excluded from the
  opencode lane in `translation.yaml`. Expect the same disposition unless an
  adaptation pass is in scope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `primitives-core/skills/lab-setup/SKILL.md` exists with its references, and `rg -n 'lab-setup' primitives-core.yaml` returns a roster entry carrying origin, disposition, and targets
- [ ] #2 Bundle home is decided and wired — the skill resolves through at least one plugin's `skills/` symlink, and `make ci` is green
- [ ] #3 Lane disposition recorded — if claude-code-only, `translation.yaml` carries a `lab-setup` exclusion with a stated reason (the `rubric-panel` / `layer-cycle` precedent); otherwise the opencode lane generates it
- [ ] #4 No duplicate source — the EVALS copy at `~/Developer/EVALS/.claude/skills/lab-setup/` is removed in favour of the distributed one, or a note in this card records why the workbench keeps its own
- [ ] #5 No subject-specific instrument rides along — `rg -i 'package-inventory|inventory\.csv|lab-01' primitives-core/skills/lab-setup` returns zero matches
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Rule the bundle home against task-9's bundle-composition principle.
2. Copy the skill + its references into `primitives-core/skills/lab-setup/`, register it in `primitives-core.yaml`, symlink it into the chosen plugin, record the `translation.yaml` disposition.
3. Bump the host plugin's version, run `make ci`, publish, and verify the skill loads from a fresh session in an unrelated project.
4. Retire the EVALS copy (or record the exception) and cross-link this card from the lab's REPORT.md deliverables list.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Not started. Prerequisite worth knowing before step 3's verification: as of
2026-08-06 no foreman-kit skill loads into a session even though the plugin is
enabled and its hooks run — a fresh `claude -p` in two separate projects reports
`foreman`, `waves`, `handoff`, `rubric-panel`, `deletion-pass`, and `layer-cycle`
all unavailable, while `dataviz` from the same marketplace is available. Reported
as a bug per decision-1. Whatever homes `lab-setup` inherits that problem, so
AC#2's "wired" is only demonstrable once the loading defect is understood.
<!-- SECTION:NOTES:END -->
