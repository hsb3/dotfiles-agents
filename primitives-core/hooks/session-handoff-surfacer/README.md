# session-handoff-surfacer

Closes the handoff loop's "consume" edge: on a genuinely cold session start it finds
the project's handoff file and injects a pointer plus a capped head excerpt, so the
session picks up prior work without re-deriving it. Silent on resume or compact starts
(context is already present) and when no handoff file exists.

## When it fires

Fires at session start (`SessionStart`) only on `startup`/`clear` sources — never on
`resume` or `compact`. Looks for `_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md`,
in that order — unless a project overrides the location (see below).

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_SURFACER_HEAD_LINES` — default 15 (lines of the handoff excerpted).
- `HANDOFF_SURFACER_LOG_PATH` — default `<project-root>/logs/handoff-surfacer.jsonl`.

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
hook treats the handoff as absent rather than falling back to the standard search. An
absent, unparseable, or out-of-project-root value leaves the standard search untouched.
This same key and precedence rule is honored by `handoff-freshness-guard` and documented
by the `handoff` skill — the three must never disagree about where the file lives.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it surfaces.
