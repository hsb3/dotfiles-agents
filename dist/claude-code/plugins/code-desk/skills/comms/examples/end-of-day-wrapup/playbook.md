_End-of-day wrap-up playbook. Shared machinery: `references/comm-package-standard.md`. No worked sample yet - drafted from first principles._

# End-of-day wrap-up

Daily PM, audience the owner. **The one job: close today and tee up tomorrow's first move.** It is
the spoken/visual companion to the HANDOFF refresh - the wrap-up is the readout, the `/handoff`
skill writes the file. Toolchain deck-builder (`boardroom`), lighter than the morning brief
(4-5 slides); audio optional (~1-2 min). Folder slug `-eod-wrapup`.

> Assumptions to confirm with the owner: daily PM cadence; deck-builder; audio optional. No prior
> instance exists - this playbook ships without a `sample.*` artifact; create one on first run.

## The one rule

**Retrospective, then one forward pointer.** Say plainly what got done, what is still open, and
the single first thing tomorrow. The wrap-up does not re-plan the week (that is the weekly
briefing) and does not recommend the day's decision (that is the morning brief) - it reconciles
the day against what was intended and hands off cleanly.

## Relationship to HANDOFF (do not duplicate)

The wrap-up and the project's `HANDOFF.md` carry the same load-bearing state. Run the `/handoff`
externalization pass FIRST so the file is current, then build the wrap-up FROM the refreshed
handoff. The deck/audio is the human-facing readout; the handoff is the canonical record.
Anything load-bearing that surfaces while writing the wrap-up goes back into the handoff (or a
gh issue) - the deck is not a place state lives.

## Deck structure

~4-5 slides. Blunter and shorter than the morning brief.

| # | Slide | Content |
| --- | --- | --- |
| 1 | Title | "Day closed - <date>" + one-line state delta (this morning to now) |
| 2 | Shipped today | Merged PRs / commits / decisions, concise. Name ids. What actually changed. |
| 3 | Still open / in-flight | Mid-arc work with its next action; what was started but not finished, stated plainly |
| 4 | First thing tomorrow | The single pickup, plus any owner decision that blocks it |
| 5 | Watch-items (optional) | Risks or surprises surfaced today that aren't yet tracked - file them as issues, list here only as a pointer |

Drop slide 5 on a quiet day; some days the wrap-up is three slides.

## Gather

- Run `/handoff` first; the refreshed handoff is the primary source.
- Today's merges: `git log --since="<today> 00:00"`;
  `gh pr list --state merged --limit 1000 --json mergedAt --jq '[.[]|select(.mergedAt>="<today>T00:00:00Z")]|length'`
  (always `--limit 1000` - the default 30-row cap undercounts; see the morning playbook pitfall).
- Open/in-flight: the handoff's in-flight section + any running agents or half-reconciled work.
- Reconcile against the morning brief's "recommended today" - did the day's plan hold? Say so.

## Voice deltas (beyond the baseline)

- Blunt and self-addressed; "didn't finish X, blocked on Y" is the honest line, not "made
  progress on X".
- Short audio is a spoken close, not a performance - skip it on a thin day and ship the deck.
