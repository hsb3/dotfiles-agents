---
id: TASK-29
title: Promote lab-setup from the EVALS workbench into the collection
status: To Do
assignee: []
created_date: '2026-08-06'
updated_date: '2026-08-10 02:25'
labels:
  - assembly
milestone: m-2
dependencies: []
priority: medium
type: feature
ordinal: 2900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The inventory lab (`~/Developer/EVALS/lab-01-package-inventory`) produced four generalized artifacts. Three shipped through atelier already: `rubric-panel`, `deletion-pass`, `layer-cycle`. The fourth, `lab-setup`, never did — it's the cross-lab methodology for standing up and running an EVALS lab (subject choice, RULES.md and rubric authoring, toolchain freezing, builder briefs, judging, closeout), and exists only as a skill at `~/Developer/EVALS/.claude/skills/lab-setup/`: no primitives-core source, no roster entry, no translation.yaml disposition.

Owner ruling 2026-08-07: bundle home is standalone — not atelier, not code-desk.

BLOCKED until the owner settles one more thing: that ruling also spawned TASK-043 (an aggregate plugin for standalone skills), and whether lab-setup gets its own plugin or joins that aggregate is an open, competing reading — see comment #1 on this card. Don't start the move until that's resolved.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `primitives-core/skills/lab-setup/SKILL.md` exists with its references, and `primitives-core.yaml` has a roster entry carrying origin, disposition, and targets (verify via `rg -n 'lab-setup' primitives-core.yaml`)
- [ ] #2 Bundle home (standalone, per the 2026-08-07 owner ruling) is wired — the skill resolves through a plugin's `skills/` symlink — and `make ci` is green
- [ ] #3 Lane disposition recorded — if claude-code-only, `translation.yaml` carries a `lab-setup` exclusion with a stated reason (the `rubric-panel`/`layer-cycle` precedent); otherwise the opencode lane generates it
- [ ] #4 No duplicate source — the EVALS copy at `~/Developer/EVALS/.claude/skills/lab-setup/` is removed in favor of the distributed one, or a note on this card records why the workbench keeps its own
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
Not started.

Correction to this card's first note (2026-08-06): it claimed foreman-kit's skills
do not load and cited issue #244 as a blocker on AC#2's verification. That was
wrong and #244 is closed as invalid. The probes behind it ran from project paths
with no install record; `claude plugin list` aggregates records from *other*
paths and reported "enabled" anyway. Re-probed from `~/Developer/dotfiles-agents`,
which does have the record: all six foreman-kit skills and all four tiered agents
(scout, builder, reviewer, lead) load. See
`.claude/memory/plugin-enablement-needs-per-project-install.md`.

The practical consequence for step 3: verifying `lab-setup` loads "from a fresh
session in an unrelated project" means installing the host plugin for that
project path first (`claude plugin install <id>@dotfiles-agents --scope local`)
and starting a new session — an `enabledPlugins` flag alone proves nothing.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:10
---
Owner ruling 2026-08-07 on the bundle-home question: STANDALONE, not atelier and not code-desk. This resolves the card's open sub-question and its Implementation Plan step 1.

The owner's note carried a second instruction that goes beyond this card: 'create a plugin that distributes all skills that can stand on their own.' Filed separately as TASK-043, because it is a marketplace-shape change rather than a placement decision for one skill.

FLAGGED AS AMBIGUOUS, not resolved here: those two instructions can be read as either compatible or competing. Reading A — lab-setup ships as its own one-skill plugin, and TASK-043 additionally builds an aggregate convenience plugin alongside the existing standalones. Reading B — TASK-043 replaces the pattern of one-plugin-per-standalone-skill, and lab-setup simply joins that aggregate rather than getting a plugin of its own. The readings imply materially different work (one new plugin versus restructuring 17 existing marketplace entries), so this needs the owner's word before either is built. Do not start TASK-043 or the lab-setup move until that is settled.
---
<!-- COMMENTS:END -->
