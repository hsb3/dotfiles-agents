---
name: kata-sync-enable-resets-cursor
description: Preserve kata card fields when re-enabling the GitHub sync
metadata:
  type: project
---

Re-enabling `kata sync github enable` resets its cursor and the first import can reapply GitHub
state. Before enabling, snapshot every card field. After the first sync, diff every field and
restore the exact prior values. Close a GitHub mirror when its card closes to avoid reopening it
on a later re-import.

The import-only sync and manual mirror-closure policy are governed by [AGENTS.md](../../AGENTS.md).
