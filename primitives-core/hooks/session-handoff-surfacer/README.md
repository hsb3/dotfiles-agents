# session-handoff-surfacer

In opt-in external `scope: session`, startup and resume surface the lead bridge, writer key
and native binding path. The handoff skill reads own/predecessor and relevant peer cards;
the surfacer never rewrites or merges their bodies. Missing identity reports unsupported mode.
Legacy project-scope source filtering remains unchanged.

Activation location follows the [shared selection rules](../../skills/activation/SKILL.md):
fresh Codex projects use `.codex/atelier.local.md`; Claude Code and Codex legacy fallback
use `.claude/atelier.local.md`. Explicit overrides win; policies are never merged.

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

Env-overridable; shipped wiring leaves these at hook.py's built-in defaults:
- `HANDOFF_SURFACER_HEAD_LINES` — default 15 (lines of the handoff excerpted).
- `HANDOFF_SURFACER_LOG_PATH` — default `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/handoff-surfacer.jsonl`.
- `ATELIER_ACTIVATION_FILE` — default harness-selected project policy (see above) (activation file location).
- `CLAUDE_PROJECT_DIR` — set by Claude Code; anchors the activation file lookup and the ledger's `project` field, falling back to the payload `cwd` when unset.

**Per-project handoff location override.** A project that keeps its handoff somewhere
other than the standard candidate paths can say so with a `handoff:` key in
the selected `atelier.local.md`. Two forms.

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

## In a linked worktree

Both halves of the configuration follow the main checkout: the activation file, and the
stamp or handoff file it names. Neither travels into a linked worktree — the activation
file and the stamp are gitignored, and a handoff file may simply be untracked — so before
this resolution a session started inside a worktree was told there was no handoff at all,
which is the one thing this hook exists to prevent.

When no file sits at the direct path, the hook asks `git rev-parse --git-common-dir`
whether the project dir is a linked worktree and, if it is, looks for the same relative
path under the **main checkout**. The lookup is lazy — one `git` subprocess only on the
miss — so a file the worktree does have still wins, which means a **tracked** handoff file
or activation file is read there at the version committed on the worktree's branch.
`ATELIER_ACTIVATION_FILE` wins outright and is never re-resolved. With no `git` on `PATH`,
or a project dir that is not a linked worktree, behaviour is exactly what it was. The stamp
is still only ever stat'ed, never opened.

One visible consequence: a path resolved this way is named relative to the worktree, so the
surfaced pointer reads `../../handoff.stamp` rather than `.claude/handoff.stamp`. That is
deliberate — it is the path that actually resolves from where the session is standing, and
it says out loud that the handoff lives outside this checkout.

## Ledger

One row per `SessionStart` call, appended to the `handoff-surfacer` stream:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/handoff-surfacer.jsonl
```

Each row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`, `project`)
plus `session_id`, `source`, `handoff_path`, `handoff_mode`, `surfaced` (bool), and `reason`
when not surfaced (`"source not eligible for surfacing"` or `"no handoff file found"`). A row
written from the fail-open error path carries `error` and a truncated `traceback` instead.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it surfaces.

## Codex

Codex SessionStart receives the same file excerpt or external pointer in `hookSpecificOutput.additionalContext`. Activation uses `.codex/atelier.local.md` with the documented legacy fallback; Codex payload cwd is authoritative even if a Claude environment variable is inherited.
