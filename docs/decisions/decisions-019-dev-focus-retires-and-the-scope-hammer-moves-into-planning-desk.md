---
id: "decision-019"
title: dev-focus retires and the scope hammer moves into planning-desk
date: '2026-09-08'
status: accepted
---
## Context

`dev-focus` shipped two session-discipline moves in one skill: a **focus check** that restated
the original task and named any drift, and a **scope review** — the MUST/DEFER/CUT "scope
hammer" — that sorted a candidate list into what to build now, later, or never. It shipped in
both `code-desk` and `solo-skills`.

Three things were wrong with it, and only the third is about overlap.

- **Nothing it produced was checkable.** Both moves were markdown-heading templates. No gate read
  the output, no artifact survived the session, and no acceptance criterion anywhere named it. A
  skill whose entire contract is "print these five headings" cannot be verified as having run
  correctly, so it cannot be verified as useful either.
- **Its trigger was a broad phrase list.** `"focus check"`, `"are we still on track"`, `"am I
  drifting"`, `"scope this"`, `"what should we cut"` — conversational English, not a task
  vocabulary. A skill that fires on an offhand question competes for attention with the skill
  that actually owns the work in flight.
- **The drift half duplicated skills that already do it with real artifacts.** `planning-desk`
  states the residual against cited source, `delegation` scopes a brief before it is dispatched,
  and `layer-cycle` drives create/evaluate/refine against a contract. Each of those re-anchors a
  session and leaves something behind. Re-anchoring by restating the task from memory is the
  weakest of the four and the only one with nothing to inspect afterward.

The MUST/DEFER/CUT half was the part worth keeping, and it had no home: it is a planning move,
and it was sitting in a session-discipline skill.

## Decision

Owner ruling: retire `dev-focus`. The two halves are not treated the same.

1. **The focus-check template is dropped outright, not migrated.** Its job is already done by
   `planning-desk`, `delegation`, and `layer-cycle`, each with an artifact. Moving a template
   with nothing to inspect into another skill would carry the defect along with the prose.
2. **The MUST/DEFER/CUT scope hammer moves into `planning-desk`** and gains a checkable output on
   the way. It is now a mode in that skill's mode table, and it must produce a **table** — one
   row per candidate, its bucket, and a one-line reason — plus an explicit **done when**: every
   candidate in exactly one bucket with a reason, and every challenge that fired (everything
   landed in MUST, an item with no acceptance criteria, effort past one focused session, a
   dependency on unbuilt infrastructure) answered rather than ignored. The DEFER/CUT default bias
   carries over verbatim: MUST is argued for, never assumed.
3. **No script.** The artifact is a table in the session, inspectable by a reader; a checker for
   it would be a gate over prose the repo does not ship anywhere else.

`planning-desk` was chosen over `task-authoring` because the hammer runs over a *set* of
candidates before any of them is written up, and `task-authoring` owns the body of one already-
decided item.

## Consequences

- **`solo-skills` and `code-desk` both lose a shipped skill.** Anyone who invoked `dev-focus` by
  name loses it; the scope half is reachable through `planning-desk` in `mise-en-place`, the
  focus half is not reachable at all. Both bundles take a minor bump, and `mise-en-place` takes
  one for the capability `planning-desk` gained.
- **The removal is declared in the commit that makes it**, per `scripts/check_removals.py` — the
  gate derives removals from the published tree and demands the unit be named with a removal verb
  in the commit message. There is no removals inventory to update.
- **The scope hammer's trigger phrases move onto `planning-desk`'s description**, which widens
  that skill's trigger surface slightly. Accepted: it is the same phrases attached to a skill
  that now produces something, rather than to one that did not.
- No gate contract changes anywhere. The roster loses one row, two symlink assemblies lose one
  member each, and the catalog counts move with them.
