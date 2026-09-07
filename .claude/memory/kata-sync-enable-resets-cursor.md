---
name: kata-sync-enable-resets-cursor
description: kata sync github enable on an existing binding resets its cursor, and the next sync re-applies GitHub's title/body/status/labels/priority onto every mirrored card; snapshot first, restore by script
metadata:
  type: project
---

`kata sync github enable ...` on a project that already has a binding keeps the binding id but **resets `last_cursor_at` to null**. The next sync (periodic, or `kata sync github once`) then treats every mirrored GitHub issue as changed and overwrites the kata card's title, body, status (reopening cards whose mirror is open), labels, and priority (blanked, GitHub has none). Measured 2026-09-07 while turning `title_prefix` off: 189 of 215 mirrored cards updated, 96 titles and 30 bodies reverted to GitHub wording, 3 closed cards reopened, 27 priorities blanked.

**Why:** the sync is inbound and cursor-based; kata-side edits survive only because the cursor skips unchanged GitHub issues. Any cursor reset is a full re-import in place.

**How to apply:** before any `enable`, `kata list --status all --json > snapshot`; after the first sync, diff every field against it and restore with `kata edit --title/--body/--priority`, `kata label add/rm`, and re-close with the original evidence. Close a card's GitHub mirror when you close the card, or the next cursor reset reopens it. The same overwrite happens per card whenever its GitHub issue changes, which is the open build item on z1xy. Related: [[feedback-tracker-workflow]].
