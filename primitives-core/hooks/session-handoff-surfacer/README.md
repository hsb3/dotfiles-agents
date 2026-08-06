# session-handoff-surfacer

Closes the handoff loop's "consume" edge: on a genuinely cold session start it finds
the project's handoff file and injects a pointer plus a capped head excerpt, so the
session picks up prior work without re-deriving it. Silent on resume or compact starts
(context is already present) and when no handoff file exists.

## When it fires

Fires at session start (`SessionStart`) only on `startup`/`clear` sources — never on
`resume` or `compact`. Looks for `_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md`.

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_SURFACER_HEAD_LINES` — default 15 (lines of the handoff excerpted).
- `HANDOFF_SURFACER_LOG_PATH` — default `<project-root>/logs/handoff-surfacer.jsonl`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it surfaces.
