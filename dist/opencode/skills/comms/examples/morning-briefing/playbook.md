_Morning briefing playbook. Shared machinery: `references/comm-package-standard.md`. Worked example: `sample.slides.json`._

# Morning briefing

Daily AM, audience the owner. **The one job: the decision he has to make today, in the first 30
seconds.** Toolchain deck-builder (`boardroom`); audio companion (~2-3 min). Folder slug
`-morning-status`.

## The one rule

**Lead with what he needs to know; bury the detail.** The deck opens with the recommendation,
then the horizon, then concise summaries of completed work - in that order. Do not open with an
exec summary that recaps everything.

## Deck structure (the endorsed order)

~7 slides. Phrases, not sentences - if a bullet runs past ~12 words, cut it or move detail to
the audio. See `sample.slides.json` for a real instance of this structure.

| # | Slide | Content |
| --- | --- | --- |
| 1 | Title | "What to do today" + date + one-line framing |
| 2 | Recommended today | The 1-3 actions/decisions, each with a one-line why. Tag verbs: BUILD / DECIDE / PARALLEL. This is the slide that matters. |
| 3 | On the horizon | The active gate + what's next. Two columns: blockers vs what-comes-after. |
| 4 | Since last briefing, at a glance | 3 stat columns + 3 one-liner takeaways |
| 5 | What shipped - 1 | The headline arc, concise (4 bullets max) |
| 6 | What shipped - 2 | Secondary arcs grouped, concise |
| 7 | The line for today | Hero callout: the ask, restated in one sentence |

Slides 5-6 are skippable by design - that's where the detail goes so slides 2-3 stay clean.
Scale 5-6 up or down to fit the day's volume; some days "what shipped" is one slide.

## Gather (accuracy is the whole job)

- Handoff file: newest delivery sections + the gate / what's-next model.
- Live counts: `gh issue list --state open --limit 1000 --json number --jq 'length'`;
  `gh pr list --state merged --limit 1000 --json mergedAt --jq '[.[]|select(.mergedAt>="<DATE>T00:00:00Z")]|length'`;
  per-gate `gh issue list --label gate:<x> --limit 1000` if the repo uses gate labels.
- `git log --since="<last briefing date>"` to confirm the merge story.
- **Pitfall (bites every time):** `gh issue list` / `gh pr list` default to a **30-row limit**, so
  both `| grep -c` AND `--jq 'length'` silently undercount once a repo passes 30 open items.
  ALWAYS pass `--limit 1000` (or use `gh search issues`). If the board uses milestones, report
  unmilestoned vs total separately (`--jq '[.[]|select(.milestone==null)]|length'`).

## Voice deltas (beyond the baseline)

- Recommendation slide uses imperative verbs and names the issue/PR (e.g. `#NNN`), not prose.
- Audio is spoken: spell acronyms and ids for TTS (read `ESRD` as `E.S.R.D.`, say "issue 128"
  not "#NNN"). Build the spell-out list from the day's own domain terms.
