# handoff-freshness-guard

Guards the handoff loop's "produce" edge: before compaction proceeds it checks whether
the project's handoff file is fresh. A manual `/compact` blocks with instructions to
run `/handoff` first; an auto-compaction never blocks (it could wedge the session near
a full context window) — it logs and posts non-blocking guidance instead.

## When it fires

Fires before a manual or automatic compaction (`PreCompact`), checking file age against
`_meta/HANDOFF.md`, `HANDOFF.md`, or `.claude/HANDOFF.md` (fresh within 30 minutes),
in that order — unless a project overrides the location (see below), in which case it
may instead be checking the age of a freshness stamp standing in for a handoff that
lives outside the repo.

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `HANDOFF_GUARD_FRESHNESS_MINUTES` — default 30.
- `HANDOFF_GUARD_LOG_PATH` — default `<project-root>/logs/handoff-guard.jsonl`.

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
guard treats the handoff as missing rather than falling back to the standard search. An
absent, unparseable, or out-of-project-root value leaves the standard search untouched.

External mode — for a handoff that lives on a tracker or board outside the repo, where
there is no file for this guard to age-check:

```markdown
---
handoff:
  mode: external
  stamp: .claude/handoff.stamp
  location: Kaneo board task DFA-233
---
```

`stamp` stands in for the handoff file: freshness is judged by the stamp's mtime, never
by anything read from `location`. A `stamp` that is absent, blank, or resolves outside
the project root leaves the whole key inert (same fail-open posture as an out-of-root
file override), and so does a `mode` that is neither `file` nor `external`. When armed, a
missing or stale stamp on a **manual** `/compact` blocks with a reason naming the stamp
path and, when set, the `location`:

```
No handoff signal found (stamp .claude/handoff.stamp has never been touched; the handoff
lives at: Kaneo board task DFA-233) — update the handoff and touch the stamp, then /compact.
```

(Drops the `location` clause when none is set, and swaps "has never been touched" for
"is stale" when the stamp exists but has aged out.) An **automatic** compaction never
blocks, in either mode — it logs and posts the same non-blocking `systemMessage` guidance
it always has, naming the stamp instead of a file.

This same key and precedence rule is honored by `session-handoff-surfacer` and documented
by the `handoff` skill — the three must never disagree about where the handoff lives.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it enforces.
