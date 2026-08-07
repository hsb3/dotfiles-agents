# handoff-freshness-guard

Guards the handoff loop's "produce" edge: before compaction proceeds it checks whether
the project's handoff file is fresh. A manual `/compact` blocks with instructions to
run `/handoff` first; an auto-compaction never blocks (it could wedge the session near
a full context window) — it logs and posts non-blocking guidance instead.

## When it fires

Fires before a manual or automatic compaction (`PreCompact`), checking file age against
`_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md` (fresh within 30 minutes),
in that order — unless a project overrides the location (see below).

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_GUARD_FRESHNESS_MINUTES` — default 30.
- `HANDOFF_GUARD_LOG_PATH` — default `<project-root>/logs/handoff-guard.jsonl`.

**Per-project handoff location override.** A project that keeps its handoff somewhere
other than the standard candidate paths can say so with a `handoff:` key in
`.claude/atelier.local.md`:

```markdown
---
handoff: docs/HANDOFF.md
---
```

The activation file is re-read on every call, so an edit takes effect on the next tool
call — no restart needed. When set to a path inside the project root, that path is
authoritative: it wins over any standard candidate, and if it doesn't exist (yet) the
guard treats the handoff as missing rather than falling back to the standard search. An
absent, unparseable, or out-of-project-root value leaves the standard search untouched.
This same key and precedence rule is honored by `session-handoff-surfacer` and documented
by the `handoff` skill — the three must never disagree about where the file lives.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it enforces.
