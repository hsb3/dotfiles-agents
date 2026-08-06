# handoff-freshness-guard

Guards the handoff loop's "produce" edge: before compaction proceeds it checks whether
the project's handoff file is fresh. A manual `/compact` blocks with instructions to
run `/handoff` first; an auto-compaction never blocks (it could wedge the session near
a full context window) — it logs and posts non-blocking guidance instead.

## When it fires

Fires before a manual or automatic compaction (`PreCompact`), checking file age against
`_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md` (fresh within 30 minutes).

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_GUARD_FRESHNESS_MINUTES` — default 30.
- `HANDOFF_GUARD_LOG_PATH` — default `<project-root>/logs/handoff-guard.jsonl`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it enforces.
