# exec-desk

The executive-desk overhead for running a portfolio of work end-to-end: plan it under a
source-grounded planning desk, keep a GitHub Project board's prioritization fields groomed,
report out through recurring status comms, and build the decks those comms ship as.

## What you get

| Skill | What it does |
|---|---|
| `planning-desk` | Stands up a source-grounded planning desk under `_meta/plans/` — write conformant issue bodies and deep build plans, driven through a draft → review → fix → reconcile loop. |
| `board-triage` | The weekly routine that fills in Impact/Effort/Priority on a GitHub Project (v2) board so its prioritization and roadmap views stay useful instead of drifting into noise. |
| `comms` | Produces recurring status deliverables — a morning briefing, end-of-day wrap-up, weekly planning briefing, board readout, or product overview — as a deck, to one consistent standard. |
| `pptx-themes` | Builds the decks `comms` ships as, with a curated theme layer — semantic theme tokens, approved color palettes, monospaced typography, and a visual-QA workflow — composed over Anthropic's vendored pptx base skill. |

## A worked example

```
You: "plan this out"
→ planning-desk writes a conformant issue body or a deep build plan under _meta/plans/,
  grounded in cited source, stated as deliverables/criteria/parallelism — never a timeline.

Later: "run board triage"
→ board-triage exports the board snapshot, finds the un-ranked/blank/stale items, sets
  Workstream/Impact/Effort/Priority by the standing rubric, and applies only the diffs.

End of week: "produce the weekly planning briefing"
→ comms assembles the deck from the same sources the planning desk and board already
  track, to the standard's format — no one-off slide deck from scratch.
→ pptx-themes renders it: the approved palette, monospaced type, and a visual-QA pass
  before it ships, instead of the generic pptx skill's defaults.
```

## Honest scope

This bundle assumes a repo, a planning-desk `_meta/plans/` tree, and (for `board-triage`) a
GitHub Project (v2) board already stood up — it operates on those directly rather than
replacing them. `pptx-themes` is a themed layer over Anthropic's vendored `pptx` base skill,
not a full authoring replacement for it.
