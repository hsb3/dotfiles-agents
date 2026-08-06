---
name: backlog-cli-is-the-write-path
description: "Owner ruling 2026-08-06 — backlog task writes go through the backlog CLI/MCP tools; the 2026-08-04 sibling-rewrite was a concurrent-session race, and decision-7 was deleted outright"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6df93923-85f2-432a-902f-9af5901954a0
  modified: 2026-08-06T13:54:12.054Z
---

Use the `backlog` CLI (or its MCP tools) for backlog task writes in this repo — do not
hand-edit task files. The 2026-08-04 "CLI silently rewrote sibling task files" incident
that motivated the old hand-edit-only rule was a concurrent-session race, not a CLI defect.

**Why:** two sessions writing the backlog at once invalidated the CLI's index; the CLI
itself is sound. The owner reversed the ruling on 2026-08-06 and had decision-7 deleted
outright — no erratum or supersession trail wanted.

**How to apply:** task lifecycle edits go through `backlog task edit` / the backlog MCP
tools; avoid two concurrent sessions writing the backlog simultaneously. When the owner
reverses a ruling, delete the artifact rather than layering correction callouts, unless
told otherwise. Related: [[feedback-verify-state-before-staging-decisions]].
