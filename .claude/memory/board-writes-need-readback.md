---
name: board-writes-need-readback
description: Kaneo bulk writes get silently reverted seconds later; single-field PUT sticks, and only a delayed read-back proves either
metadata:
  type: feedback
---

A board write is not done when the call returns. Verified 2026-08-22 on the DFA board:
`PATCH /task/bulk` (what `board-triage`'s `kaneo_board.py apply` uses) reported `applied N
cell(s)`, and every agent-attributed `status_changed` was undone 1–5s later by an
unattributed (`userId: null`) write. `PUT /task/status/{id}` on the same task and lane
persisted. `kaneo_status_drift.py` did not flag any of it.

**Why:** the apply step reports on *issuing* the call, never on reading the value back, so a
reverted write is indistinguishable from a successful one — a triage pass can report a lane
it did not actually fill. Same family as [[no-unguarded-counts-in-prose]] and
[[make-ci-refusal-line-is-a-passing-test]]: judge by the observed end state, not by the
tool's own success message.

**How to apply:** move lanes one task at a time through the single-field endpoint, then
re-read after ~15s before reporting. Treat `applied N cells` as a claim. Related:
`list_tasks` paginates at 100 and ignores a larger `limit`, so a lane can read as empty
while holding tasks — use the board-triage export for anything board-wide. Live cards:
DFA-263 (the defect), DFA-234 (the API traps). See also [[reproduce-before-fixing-a-card]].
