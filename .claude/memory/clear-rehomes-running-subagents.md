---
name: clear-rehomes-running-subagents
description: /clear does not kill running subagents; it re-homes them to a new session dir and leaves the sidecar behind
metadata:
  type: project
---

`/clear` does NOT kill a running subagent. The agent keeps working, answers `SendMessage`,
and reports normally — but its files split across two session directories: the OLD
`<projects>/<slug>/<old-session>/subagents/` keeps `agent-<id>.meta.json` (the sidecar) and
the pre-clear transcript, while the NEW session dir gets **only** a fresh transcript and
**no sidecar**. The `agent_id` is stable across the boundary; the session directory is not.

Measured 2026-08-23: a 70-minute `atelier:manager` survived a `/clear` and finished its wave.
An earlier handoff asserted the opposite ("that manager is gone") and was wrong.

**Why:** anything keyed on `<session>/subagents/` breaks asymmetrically — a stop-time lookup
misses the sidecar and silently drops the row for exactly the long-running agents worth
measuring, while the orphaned sidecar in the old dir becomes a permanent phantom "pending".

**How to apply:** resolve subagent state by `agent_id` across sibling session dirs, never by
the live session dir alone. When widening a lookup, widen the *settled* set only — widening
the *started* universe reports every delegation the project ever ran as stalled. That
asymmetry is deliberate in `subagent-telemetry` and pinned by a test; do not "tidy" it.
Related: [[worktree-isolation]], [[probe-harness-hygiene]].
