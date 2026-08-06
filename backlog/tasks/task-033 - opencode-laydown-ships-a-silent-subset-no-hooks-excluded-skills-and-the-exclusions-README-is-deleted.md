---
id: TASK-033
title: >-
  opencode laydown ships a silent subset: no hooks, excluded skills, and the
  exclusions README is deleted
status: To Do
assignee: []
created_date: '2026-08-06 19:17'
updated_date: '2026-08-06 19:20'
labels:
  - opencode
  - install
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
## Problem

A user follows the README's opencode instructions, sees a success message, and receives materially less than the marketplace advertises — with no warning and no artifact explaining the gap.

Found 2026-08-06 during a TASK-031 review, by running the documented block verbatim rather than reading it:

```sh
git clone --branch dev https://github.com/hsb3/dotfiles-agents && cd dotfiles-agents
scripts/install_opencode.sh --global
```

Result: `opencode laydown complete -> .../.opencode (skills/ + agents/)` carrying **25 skills, 4 agents, and 0 hooks**. Absent: `foreman`, `waves`, `rubric-panel`, `layer-cycle`, `claude-code-config`, `claude-code-expertise`, `project-memory`, `tech-eval-research`, `dev-focus`, and all four hooks. Four catalogued plugins are wholly unavailable on that runtime.

The generator is not at fault for the exclusions themselves — `gen_opencode.py` deliberately writes an exclusions table into the lane's README ("## Not in this lane (and why)"), which is the honest design. The defect is that **the user never sees it**: `scripts/install_opencode.sh` builds into `TMP="$(mktemp -d)"` under `trap 'rm -rf "$TMP"' EXIT`, and the generated `install.sh` copies only `skills/` and `agents/`. The explanation is deleted before it can be read.

The reviewer recovered the table only by building the lane by hand.

## Why it matters

The front door's first chooser row sends a visitor to `foreman-kit`, and the opencode path documented three lines above delivers neither the `foreman` skill nor any hook. This is the one place where following the page's own instructions produces a success message and a materially different outcome from what was promised.

TASK-031 adds a one-sentence disclosure to the README as a stopgap. That is a label on the problem, not a fix.

## Scope

Make the laydown self-describing at its destination. The likely fix is for the generated `install.sh` to copy the lane README (or a trimmed exclusions note) alongside `skills/` and `agents/`, so the installed tree carries its own manifest of what did and did not travel. A closing summary line naming the counts and the omissions would also help.

Whether hooks *can* travel to opencode at all is a separate question from disclosing that they do not — decide it explicitly and record the answer rather than leaving it implied by the generator's behavior.

## Constraints

- `gen_opencode.py` must stay deterministic (stable ordering, no clocks or randomness) — it runs at install time and nothing generated is tracked.
- Do not widen the published surface on `main` to fix this; the installer runs from a `dev` clone.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The installed opencode tree contains a readable record of what was laid down and what was excluded, with reasons
- [ ] #2 install_opencode.sh no longer deletes the only copy of that record before the user can read it
- [ ] #3 The installer prints a closing summary naming the counts laid down and the fact that hooks do not travel
- [ ] #4 Whether hooks can be translated to opencode at all is decided and the answer is recorded in the repo, not left implied
- [ ] #5 gen_opencode.py remains deterministic and nothing generated is tracked
- [ ] #6 The README's disclosure sentence added by TASK-031 is reconciled with whatever the installer now reports, so the two cannot disagree
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Sequencing set by the owner 2026-08-06: **Claude Code first, opencode after that surface is stable.** Priority dropped to Low for that reason, not because the bug is small — a user who follows the documented opencode install still gets a silent subset. Re-rank when the Claude Code side settles.

TASK-031 ships the one-sentence README disclosure as the interim mitigation, and its wording is deliberately brief so the opencode path does not get more prominence than the Claude Code path.
<!-- SECTION:NOTES:END -->
