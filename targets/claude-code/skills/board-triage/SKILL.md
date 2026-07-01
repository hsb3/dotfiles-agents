---
name: board-triage
description: >-
  This skill should be used when the user asks to "run board triage", "triage the
  backlog", "prioritize the issues", "rank the unranked issues", "fill in
  Impact/Effort/Priority", "do the weekly triage", or wants to classify GitHub
  Project (v2) items so the prioritization/now/roadmap views become useful. It runs
  the export -> analyze -> apply loop: pull a snapshot, find the un-ranked/blank/stale
  items, set Workstream/Impact/Effort/Priority by the rubric, and apply only the diffs.
version: 0.1.0
---

# board-triage — the weekly prioritization routine

Operationalizes the §8 cadence of the `github-project-board` skill: turn a board full of
captured-but-unranked items into a ranked, workable backlog, as a fast repeatable pass. Built on
the **export → analyze → apply** loop so auth stays local and every change is a reviewable diff.

Read the `github-project-board` skill first for the field model, the Impact×Effort rubric, the
changeset contract, and the three scripts — this skill is the routine that drives them; it does
not redefine them.

## When to run
The weekly (or per-sprint) pass, or any time the **Prioritization / Now / Roadmap** views look
thin because items lack `Priority`. The board is the source of truth; this keeps it honest.

## Procedure

1. **Snapshot.** Run the toolkit (scripts live at the plugin root `scripts/`):
   ```bash
   scripts/board-fields.py -o <owner> -n <number>            # confirm valid option values
   scripts/board-export.py -o <owner> -n <number> --out board-snapshot.json
   ```
2. **Find the work.** From the snapshot, list items where `fields.Priority` is null (untriaged),
   plus anything whose ranking looks stale (e.g. a `P0` no longer on a dated path, or a `Blocked`
   item whose blocker has closed). The export grid makes blanks explicit.
3. **Judge — don't guess.** For each item, pull context from the **repo's** plan/spec/issue body
   (not the board), then apply the Impact×Effort rubric (core skill §3) to set **Priority**, and
   set **Workstream / Impact / Effort**. Skip epics (containers) and owner-gated/non-buildable
   issues. Where there's no local context to judge from, leave it and flag it rather than guess.
4. **Emit a changeset.** Write a diff-only TSV — one row per cell you're changing:
   ```
   issue   field      value
   671     priority   P1
   671     impact     High
   503     iteration  Sprint 2
   ```
   Keyed on issue number; single-select values are option NAMES (see `board-fields.py`).
5. **Preview, then apply.**
   ```bash
   scripts/board-apply.py -o <owner> -n <number> --changeset changeset.tsv            # dry-run
   scripts/board-apply.py -o <owner> -n <number> --changeset changeset.tsv --apply
   ```
   Apply is idempotent and writes only cells that differ — re-runs are free.
6. **Promote.** Move ready `P0/P1` items to Status `Up Next` and assign the current `Iteration`
   (same changeset mechanism: `status` / `iteration` rows).

## Discipline
- Every triaged item gets a **Workstream** and a **Priority** — that's the pass's definition of done.
- A **dated critical path forces P0** regardless of effort (rubric override).
- Don't invent Impact/Effort for items you can't see; an honest blank beats a fabricated rank —
  the next pass (or the owner) fills it.
- Triage is meant to be cheap and frequent; resist adding new required fields (core skill §4).

## Hand-off variant
When the analyst can't read the board (a chat/agent harness where listing items overflows),
split the loop: the local side runs `board-export`, the **`board-analyst`** agent (this plugin)
produces the changeset from the snapshot + repo plans, and the local side runs `board-apply`.
