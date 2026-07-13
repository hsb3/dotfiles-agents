---
title: "Evaluate + replace the _meta/ broad-ignore gitignore policy"
type: spec
status: draft
created: 2026-07-12
purpose: Decide-first plan for the owner directive to evaluate the _meta/ ignore-by-default + negation policy and amend the repo-meta-structure standard with its successor.
notes: Decide-first -- Deliverable A (the ADR) gates B-D. Evidence in the issue body was verified against .gitignore line numbers and git check-ignore on 2026-07-12; re-verify before building, the stanza changes often.
---

# Evaluate + replace the `_meta/` gitignore policy

_Decide-first plan. The issue body carries the evidence and acceptance criteria; this plan carries
the option analysis, the blast radius, and the safe landing order._

## Tracking

#99. Owner directive 2026-07-12. Related: #82 (same standard files), #33
(pilot re-audit), #69/#70 (sibling standard fixes).

## What already exists (verified 2026-07-12)

- The stanza: `.gitignore:16-42` (27 lines, 4 duplicated .DS_Store guards, ordering dependency
  with the Python section at `:44`).
- The standard: `primitives-core/skills/repo-meta-structure/references/checklist.md` IGNORE-01..18
  rows; the scaffold's gitignore template in `primitives-core/skills/mise-en-place-scaffold/`;
  planning-desk setup step 2 documents the `_meta/*`-form requirement and the `__pycache__` trap.
- Current per-subtree reality: plans/ + _archive/ + briefings/ fully tracked; operations/ +
  research/ gitkeep-only; loose `_meta/*` files ignored unless negated (README, HANDOFF,
  mise-en-place.yml negated; NOTE.md not).

## The options (Deliverable A input)

| Option | Shape | Wins | Risks |
| --- | --- | --- | --- |
| 1 status quo | ignore `_meta/*`, negate tracked | no migration; secrets safe by default | every bite in the issue recurs; 18 audit rows police it |
| 2 track-by-default (recommended) | track `_meta/`, ignore `operations/`, caches, litter | deletes negation machinery; new content clone-survivable | secrets discipline shifts to one ignored dir + scan; noisier worktree status |
| 3 relocate secrets | option 2 + move operations/ out of `_meta/` | no secret path under a tracked tree at all | breaks the _meta taxonomy everywhere it is documented; highest migration cost |

## Landing order

1. **A — ADR** (Accepted by owner) — nothing else starts first.
2. **B — this repo's migration** in one PR: rewrite `.gitignore`, secrets scan
   (`git status --porcelain --ignored` diff + grep sweep for DSN/key patterns on everything newly
   tracked), commit-or-rule-local every currently-ignored `_meta/` artifact.
3. **C — standard amendment** in the SAME PR as B where feasible (checklist rows + scaffold
   template + planning-desk setup text + skill regeneration via `make build`), so repo and
   standard never disagree on main.
4. **D — adopter notes** (workbench, fleet-dashboard, dotfiles memory-hygiene stanza) + re-run
   the compliance audit on both repos.

## Parallelism

None worth taking -- decide-first, then B+C are one serialized change (same files, drift-guarded),
D is a fast follow.
