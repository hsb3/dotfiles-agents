---
name: board-reporting
description: >-
  This skill should be used when the user asks for a "board status", "project status
  update", "standup from the board", "weekly board digest", "what changed on the
  board", or wants a summary/rollup of a GitHub Project (v2) — counts by
  status/priority/workstream, what's in progress or blocked, target slippage, and what
  reached done. Produces a written digest from a snapshot, and can optionally post the
  project's native status-update banner.
version: 0.1.0
---

# board-reporting — status & digests from a snapshot

Turn a GitHub Project (v2) snapshot into a readable status update, standup, or weekly digest.
Read-first: it reports what the board says; it does not change the board (except the optional
status-update banner, and only when explicitly asked).

Build on the `github-project-board` skill for the field model and the export toolkit. This skill
consumes the same snapshot the triage loop produces — one read, many uses.

## Procedure

1. **Snapshot.** `python3 "${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts/board-export.py"
   -o <owner> -n <number> --out board-snapshot.json` (the toolkit ships with the sibling
   `github-project-board` skill). For a delta digest, keep the prior snapshot and diff.
2. **Rollups.** From the snapshot compute:
   - counts by **Status**, **Priority**, **Workstream** (the shape of the backlog);
   - **In Progress** + **Blocked** lists (what's active / stuck, with the blocker for each);
   - **slippage** — open items past their `Target`;
   - **landed** — items that reached `Done` since the prior snapshot (delta mode).
3. **Write it plainly.** Lead with the bottom line (what's moving, what's at risk), then the
   rollups. Match the owner's presentation norms — plain language, no hype, skimmable. Default
   output is a markdown digest; hand off to a deck/audio brief if the user wants one.
4. **Optional banner (write — ask first).** Only on explicit request, post the project's native
   status update:
   ```bash
   gh api graphql -f query='mutation($p:ID!,$b:String!){ createProjectV2StatusUpdate(input:{
     projectId:$p, body:$b, status:ON_TRACK }){ statusUpdate{ id } } }' -f p="<PROJECT_NODE_ID>" -f b="<markdown>"
   ```
   `status` ∈ `INACTIVE ON_TRACK AT_RISK OFF_TRACK COMPLETE`. This is a board write — confirm before sending.

## Output shapes
- **Standup** — yesterday/today/blockers from the In Progress + recently-Done sets.
- **Weekly digest** — rollups + landed + slippage + the P0/P1 focus list.
- **Exec status** — one bottom-line paragraph + a risk list; feeds a briefing deck.

## Notes
- Reporting is derivation, not judgment — don't re-rank here; if the board looks wrong, that's a
  `board-triage` pass, not a reporting fix.
- Counts come straight from the snapshot grid, so a digest is only as current as the export —
  always export fresh before reporting.
