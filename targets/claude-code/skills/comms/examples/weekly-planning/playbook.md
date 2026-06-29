_Weekly planning playbook. Shared machinery: `references/comm-package-standard.md`. Worked example: `sample.slides.json` + `sample.sources.md` (the 2026-06-12 Friday briefing & week plan)._

# Weekly planning briefing

Weekly (Friday), audience Henry. **The one job: name the week's single converging objective,
then the parallel lanes and owner-gated decisions that reach it.** A hybrid artifact - it fuses
a status look-back with the forward plan. Toolchain deck-builder (`boardroom`); audio companion
(~3-4 min, "executive brief"). Folder slug `-weekly-plan`.

## The one rule

**Deliverables, acceptance criteria, and parallelism - never timelines.** Owner-set dates (a
demo, a client date) are recorded as the single constraint the week converges on, not as a
day-by-day schedule. The whole deck answers "what is the week's one job, and what either feeds
that chain or waits behind a decision?"

## Deck structure (the endorsed order)

~10-11 slides. Phrases, not sentences; detail to the audio. `sample.slides.json` is the
reference for slide phrasing and the columns/stat block shapes.

| # | Slide | Content |
| --- | --- | --- |
| 1 | Title | "Where we stand, and the week to <objective>" + date (Friday) + the one owner-set constraint |
| 2 | Executive summary | The week's single job in 3-4 bullets; what this week turned a pile into a plan |
| 3 | Since last week / this morning | 3-4 stat columns (milestones, critical-path count, feeders filed, hygiene) |
| 4 | Build state / current standing | Two columns: what's done vs what's gated (owner) |
| 5 | The board, now dated | Milestones with open counts; near-term vs depth backlog |
| 6 | Critical path | The gating chain for the week's objective (acquisition to engine to surface) |
| 7 | The week - parallel lanes | 3 columns: owner decisions / engineering tail / readiness |
| 8 | Definition of done | Concrete acceptance criteria for the week's objective (lifted from the issues) |
| 9 | After this - the next pull | What the gates point at once the objective lands |
| 10 | Hazards & watch-items | What could slip the objective or bite right after - surface now, no surprises |
| 11 | The week in one sentence | Hero callout: the converging objective restated |

Scale to the week's volume; merge 4/5 or 9/10 on a light week.

## Gather

- Handoff file: current standing + delivery story since the last weekly.
- Board, dated: `gh issue list --limit 1000` by milestone with open counts; confirm 0 unmilestoned
  if the plan claims a fully-binned board
  (`gh issue list --state open --limit 1000 --json milestone --jq '[.[]|select(.milestone==null)]|length'`).
  ALWAYS pass `--limit 1000` - the default 30-row cap silently undercounts (see the morning playbook pitfall).
- Gates: per-`gate:<x>` membership (`--limit 1000`) so "definition of done" and "the next pull" cite real ids.
- `git log --since="<last weekly date>"` for the week's merge story.
- The one owner-set date (demo / client / deadline) - state it as the constraint.

## Voice deltas (beyond the baseline)

- Frame the week as parallel lanes converging on the one date; no durations per slide.
- Name the gating chain end-to-end with ids so the critical path is traceable.
- Honest fallback lines for at-risk deliverables ("if X isn't acquired by the date, demo Y and
  label X model-pending - never silently zero").
