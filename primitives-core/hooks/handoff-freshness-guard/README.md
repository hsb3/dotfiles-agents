# handoff-freshness-guard

Opt-in external `handoff.scope: session` also runs on every `PreToolUse`: the native hook
binds launch and session identity to the current transaction and invalidates only its certificate.
Codex manual compaction requires the latest completed native tool in the runtime transcript,
then consumes certification. Failed invalidation cannot reuse an older transcript epoch.
Errors refuse manual compaction in session mode; auto remains advisory. See the
[handoff workflow](../../skills/handoff/SKILL.md#opt-in-concurrent-sessions) for supported identities.

Activation location follows the [shared selection rules](../../skills/activation/SKILL.md):
fresh Codex projects use `.codex/atelier.local.md`; Claude Code and Codex legacy fallback
use `.claude/atelier.local.md`. Explicit overrides win; policies are never merged.

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
- `HANDOFF_GUARD_LOG_PATH` — default `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/handoff-guard.jsonl`.

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
guard treats the handoff as missing rather than falling back to the standard search. An
absent, unparseable, or out-of-project-root value leaves the standard search untouched.

External mode — for a handoff that lives on a tracker or board outside the repo, where
there is no file for this guard to age-check:

```markdown
---
handoff:
  mode: external
  stamp: .claude/handoff.stamp
  location: kata board issue abcd
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
lives at: kata board issue abcd) — update the handoff and touch the stamp, then /compact.
```

or, once the stamp exists but has aged out:

```
Handoff signal is stale (stamp .claude/handoff.stamp; the handoff lives at: kata board
issue abcd) — update the handoff and touch the stamp, then /compact.
```

(Both drop the `; the handoff lives at: ...` clause when no `location` is set.) An
**automatic** compaction never blocks, in either mode: on a stale/missing stamp it instead
posts a non-blocking `systemMessage` pointing at the stamp and telling the session to update
the handoff and touch the stamp soon — the file-mode equivalent of "run /handoff soon."

This same key and precedence rule is honored by `session-handoff-surfacer` and documented
by the `handoff` skill — the three must never disagree about where the handoff lives.

## In a linked worktree

Both halves of the configuration follow the main checkout: the activation file, and the
stamp or handoff file it names. Neither travels into a linked worktree — the activation
file and the stamp are gitignored, and a handoff file may simply be untracked — so before
this resolution a session running in a worktree fell all the way back to the standard
candidate search, found nothing, and blocked every manual `/compact` it ever attempted.

When no file sits at the direct path, the hook asks `git rev-parse --git-common-dir`
whether the project dir is a linked worktree and, if it is, looks for the same relative
path under the **main checkout**. The lookup is lazy — one `git` subprocess only on the
miss — so a file the worktree does have still wins, which means a **tracked** activation
file or handoff file is read there at the version committed on the worktree's branch.
`ATELIER_ACTIVATION_FILE` wins outright and is never re-resolved. With no `git` on `PATH`,
or a project dir that is not a linked worktree, behaviour is exactly what it was.

One visible consequence: a stamp resolved this way is named relative to the worktree, so
the block message reads `../../handoff.stamp` rather than `.claude/handoff.stamp`. That is
deliberate — it is the path that actually resolves from where the session is standing, and
it says out loud that the signal lives outside this checkout.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it enforces.

## Codex

Codex PreCompact uses only `continue: false`, `stopReason`, and `systemMessage` to interrupt manual compaction; its strict schema rejects Claude decision/reason fields. Trusted CLI 0.153.4 app-server probes verified missing and stale external stamps interrupt before PostCompact, while a fresh stamp permits compaction. Automatic compaction remains nonblocking.
