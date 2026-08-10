---
id: TASK-033
title: >-
  opencode laydown ships a silent subset: hooks and skills excluded, exclusions
  record deleted before the user sees it
status: To Do
assignee: []
created_date: '2026-08-06 19:17'
updated_date: '2026-08-10 02:47'
labels:
  - distribution
milestone: m-1
dependencies: []
references:
  - scripts/install_opencode.sh
  - scripts/gen_opencode.py
  - translation.yaml
priority: low
type: bug
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Running the documented opencode install (`scripts/install_opencode.sh --global`) reports success but silently ships a subset: 25 of 34 skills, 4 agents, 0 hooks — missing `foreman`, `waves`, `rubric-panel`, `layer-cycle`, `claude-code-config`, `claude-code-expertise`, `project-memory`, `tech-eval-research`, `dev-focus`, and all four hooks. Four catalogued plugins are unavailable there.

`gen_opencode.py` already writes an honest exclusions table ("## Not in this lane (and why)") into the lane README, but the user never sees it: `scripts/install_opencode.sh` builds into a `mktemp -d` deleted by `trap ... EXIT`, and the generated `install.sh` copies only `skills/` and `agents/` — the README is gone before it can be read.

Fix: make the laydown self-describing at its destination — copy the lane README (or a trimmed exclusions note) alongside `skills/`/`agents/`, and print a closing summary naming what was laid down and that hooks do not travel. Reconcile TASK-031 README disclosure sentence with whatever the installer now reports.

Constraints: `gen_opencode.py` stays deterministic (stable ordering, no clocks/randomness) and nothing generated is tracked. Do not widen the published surface on `main` — the installer runs from a `dev` clone.

Whether hooks can be translated to opencode at all is a separate, already-split-out question (TASK-044).

## Field report 2026-08-08 — the subset is not only undisclosed, it is incoherent (#289)

An opencode session in `hsb3/mcp-agent-bus` ran `/handoff` and dead-ended at step 1: `skill("handoff")` returned "Skill not found". The command travelled to opencode, the skill it names did not, and the command own text forbids re-deriving the procedure — so the agent was formally unable to comply and fell back to fetching SKILL.md over the API, which is exactly the drift the "skill tool is the source of truth" contract exists to prevent.

This raises the stakes of the card from disclosure to coherence. A laydown that omits a skill is a documented subset; a laydown that ships a command whose named skill is missing is broken on arrival, and no amount of disclosure fixes it. The class is general — any command that names a plugin skill by name has the same exposure — so the check belongs on the pairing, not on the handoff command.

Two candidate resolutions from the report, both acceptable: mirror the skill wherever its command is laid down, or give such commands a documented fallback (read the SKILL.md at a named path) so they degrade instead of contradicting themselves.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The installed opencode tree contains a readable record of what was laid down and what was excluded, with reasons
- [ ] #2 install_opencode.sh no longer deletes that record before the user can read it
- [ ] #3 The installer prints a closing summary naming the counts laid down and that hooks do not travel
- [ ] #4 Whether hooks can be translated to opencode at all is decided and the answer recorded in the repo, not left implied
- [ ] #5 gen_opencode.py stays deterministic and nothing generated is tracked
- [ ] #6 TASK-031's README disclosure sentence is reconciled with what the installer reports, so the two cannot disagree
- [ ] #7 No command is laid down into opencode while a skill it names by name is absent from that same laydown — either the skill travels with it, or the command carries a documented fallback
- [ ] #8 The pairing check covers every command that names a plugin skill, not just /handoff
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Sequencing set by the owner 2026-08-06: **Claude Code first, opencode after that surface is stable.** Priority dropped to Low for that reason, not because the bug is small — a user who follows the documented opencode install still gets a silent subset. Re-rank when the Claude Code side settles.

TASK-031 ships the one-sentence README disclosure as the interim mitigation, and its wording is deliberately brief so the opencode path does not get more prominence than the Claude Code path.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:09
---
Owner ruling 2026-08-07: SPLIT THE CARD.

Half one, do now: fix the silent subset. The installer's cleanup trap deletes the exclusions manifest that gen_opencode.py writes, so a user is told 'success' while silently receiving 25 of 34 skills and no hooks. A user knowing what they did not get is worth having regardless of the larger question, and the fix is mechanical.

Half two, separate card, still sequenced behind Claude Code: whether hooks can be translated to opencode AT ALL. That is an investigation with a real answer, and it is the part AC#4 was blocked on. Today the answer is only implied by their absence, which is not a recorded decision.

This unblocks the mechanical work without forcing the open question to be answered first.
---
<!-- COMMENTS:END -->
