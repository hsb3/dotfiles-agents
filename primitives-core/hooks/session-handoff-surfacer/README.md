# session-handoff-surfacer

Closes the handoff loop's "consume" edge: on a genuinely cold session start it finds
the project's handoff file and injects a pointer plus a capped head excerpt, so the
session picks up prior work without re-deriving it. Silent on resume or compact starts
(context is already present) and when no handoff file exists.

## When it fires

Fires at session start (`SessionStart`) only on `startup`/`clear` sources — never on
`resume` or `compact`. Looks for `_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md`,
in that order — unless a project overrides the location (see below), in which case it may
instead surface a pointer to a handoff that lives outside the repo altogether.

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_SURFACER_HEAD_LINES` — default 15 (lines of the handoff excerpted).
- `HANDOFF_SURFACER_LOG_PATH` — default `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/handoff-surfacer.jsonl`.

**Per-project handoff location override.** A project that keeps its handoff somewhere
other than the standard candidate paths can say so with a `handoff:` key in
`.claude/atelier.local.md`. Two forms.

File mode — a bare scalar, or `{mode: file, path: ...}`:

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

External mode — for a handoff that lives on a tracker or board outside the repo:

```markdown
---
handoff:
  mode: external
  stamp: .claude/handoff.stamp
  location: Kaneo board task DFA-233
---
```

`stamp` is only a freshness signal for `handoff-freshness-guard`; this hook never reads
it. A `stamp` that is absent, blank, or resolves outside the project root leaves the
whole key inert (standard search runs), and so does a `mode` that is neither `file` nor
`external`. When armed, this hook surfaces a POINTER on a cold session — never file
contents, and never the excerpt logic above — **regardless of whether the stamp file
exists yet**: the stamp is a freshness gauge, not the handoff itself, so silence at cold
start would be exactly the bug this mode exists to fix:

```
This project's handoff lives outside the repo: Kaneo board task DFA-233. Read it before
starting. Its freshness stamp is .claude/handoff.stamp.
```

(Drops the `location` clause — swapping in "but this project set no location. Ask the
user where the handoff lives" — when none is set.) This same key and precedence rule is
honored by `handoff-freshness-guard` and documented by the `handoff` skill — the three
must never disagree about where the handoff lives.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it surfaces.
