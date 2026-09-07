# Mode: plan — author a deep, source-grounded build plan

You are writing a **proper build plan** — the deep, source-grounded detail a builder (human or agent
crew) executes from. It lands at `_meta/plans/<slug>/plan.md`. The tracker holds STATE and the
item's contract; this plan holds the build DETAIL.

Read `_meta/plans/_config.md` first for this project's gate menu, tracker binding, and canonical
docs. Study an existing `_meta/plans/*/plan.md` for the house pattern if any exist; otherwise apply
the schema below literally.

## What "proper" means — the plan shape

- **Title** = the tracked item's title, then an _italic one-paragraph scope summary_ — especially the
  **RESIDUAL** if part already shipped (don't re-plan built code).
- **Status header:** `Status: draft` and `Date: <today>` (pass today's date in — don't invent one).
- **## Tracking** — the tracker ref, origin (who asked / which audit), relation to epics, and
  contract impact (does it touch an API / DB / codegen / other source-of-truth surface?). Put the
  tracking item's ref FIRST; epics and relations after (the reconcile script keys on the first ref
  the tracker snapshot knows).
- **## The problem (grounded in source)** — what EXISTS today vs what's MISSING, every claim cited
  to `path:line`. This is the load-bearing section: no guesses.
- **## Deliverables** — units **A / B / C**, each with its own `Acceptance:` sub-criteria that are
  independently verifiable (grep returns zero hits / test passes / gate fails on drift).
- **## Gate & contract hygiene** — a table of which repo gates fire and why (from `_config.md`'s
  menu). Be explicit about gates that do NOT fire.
- **## Parallelism + landing order** — a table: what parallelizes (disjoint file scopes), what
  serializes (shared files get a serialized chain, not parallel writers), the safe order to land.
  **NEVER timelines or week-by-week plans.**
- **## Open questions / owner decisions** — numbered, each with a **default / recommendation** so the
  owner can confirm fast; keep real decisions OPEN.

## Procedure

1. **Resolve the target + read the source.**
   - **a tracker ref** → resolve it through the desk's adapter (`references/adapters/`) and read
     the item's title, body, labels, and links from the snapshot.
   - **a desk slug** → read `_meta/plans/<slug>/plan.md`; its `## Tracking` section's first known
     ref is the tracked item, and the snapshot carries that item's live state.
   - **a description** → nothing is tracked yet; plan from scratch, and file the item first (its
     body is written with the `task-authoring` skill) so the plan has something to track against.

2. **Ground everything in source — this is the bulk of the work.** Establish what already exists (the
   seams, call sites, shapes), what's missing, and the exact files a builder will touch. Cite
   `path:line` throughout. For breadth, dispatch **parallel `Explore` agents** (one per subsystem /
   candidate file set) and synthesize — but treat their findings as **hypotheses and verify the
   load-bearing ones against the actual source** before they drive the plan.

3. **Scope the residual, not the whole feature.** If a seam/endpoint already shipped, say so (cite
   it) and plan only what's left. Distinguish SHIPPED vs RESIDUAL explicitly.

4. **Write the deliverables as disjoint, ownable units** with file-scope and per-unit acceptance, so
   they can be handed to parallel agents. Spell out the landing order and what must serialize.

5. **Reconcile gates** against the change surface, using the menu in `_config.md`. State which fire
   and which explicitly don't, with the reason.

6. **Surface owner decisions** as numbered open questions, each with a recommended default.

7. **Write** `_meta/plans/<slug>/plan.md` (create the folder if new). Add a row to the README's
   ACTIVE table. Then keep the tracker in sync: if the tracked item's scope or acceptance drifts
   from this plan, offer to rewrite its body with the `task-authoring` skill so the tracker and the
   plan agree.

## The review rubric (for the loop, and as a self-check)

When a plan is reviewed (see `references/loop.md`), it's scored 1-5 per dimension. Use these as a
self-check even on a single plan — A through E are the general bar, F-H catch the failures that hurt
most:

| # | Dimension | A high score means |
| - | --------- | ------------------ |
| A | Source fidelity & citation durability | Cited `path:line` checks out AND is anchored to symbol names, not just fragile line numbers; "verified" means verified |
| B | Diagnosis & scope | Right problem and root cause (not a symptom); right-sized to the actual need |
| C | Completeness | All implied deliverables + the codebase-specific concerns: security/tenancy/PII, edge cases, failure modes |
| D | Build-readiness | Concrete file targets, testable acceptance, parallelism + a safe landing order — no rediscovery needed |
| E | Risk honesty & calibration | Surfaces real risks and owner decisions; certainty is calibrated; never asserts an unverified claim as fact |
| F | Protocol conformance | Status header, deliverables/criteria/parallelism NOT timelines, ASCII-only table cells, cites canonical docs, concise |
| G | Gate & contract hygiene | Explicitly accounts for the repo's gates (codegen + same-PR contract amend, migration cost, drift guards, the pre-commit gate) |
| H | Feasibility of the recommended path | The recommended approach is implementable under the platform's constraints; any blocker is named with the work to clear it |

**Trust the findings; treat the numbers as directional.** The real rigor is claim-level source
verification — re-opening a cited `path:line` and confirming the assertion as a binary yes/no — not
the score. A perfect sweep is a red flag (a rubber-stamp), not a triumph; put a second reviewer on
any plan that lands a 5. Add a dimension when a blind spot recurs; don't pad the list.

## Report

Summarize the residual, the A/B/C deliverables + their acceptance, the gates that fire, the
parallelism, and the OPEN owner decisions. Note anything you could NOT verify against source (carry
it as a flagged assumption, not silent confidence). Do not start building — this mode plans.
