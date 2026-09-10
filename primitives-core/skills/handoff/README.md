# handoff

Opt-in external `scope: session` gives each dedicated running writer a native handoff card and
a consumed certificate. The [skill](SKILL.md#opt-in-concurrent-sessions) documents launch identity,
complete discovery, the persistence helper, and runtime limits. Every tool invalidates session
freshness; use the helper last and stop compaction on any failure. Project scope is unchanged.
The helper verifies native predecessor labels, repository/work metadata and body readback;
its immutable call binding prevents a delayed helper from borrowing a newer transaction.
Session certification ships for Codex only; Claude and OpenCode session support is unavailable.
POSIX advisory locks serialize each writer's helpers through backend readback and publication;
ordinary hooks stay lock-free. Unsupported platforms fail clearly rather than persist unlocked.

Maintains the project's session-handoff file so a brand-new session can pick up work cold —
externalizes current state, in-flight work, decisions made and pending, and gotchas into one
file readable in under ~10k tokens.

## When it triggers

Use it at session boundaries when the user says "wrap up", "update the handoff", "prepare to
clear/compact", "write the handoff", or runs `/handoff`; use `/handoff init` to create the
file in a project that lacks one. It updates `_meta/HANDOFF.md` (or `HANDOFF.md` /
`.claude/HANDOFF.md`, whichever the project already uses, or a project-relative path the
project's `handoff:` key names). A project whose handoff lives outside the repo entirely
(a tracker or board) sets that key to external mode instead — the skill updates the handoff
there and touches a freshness stamp, no HANDOFF.md involved.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it closes the session that the delegation
skill runs and the waves skill drives across a backlog.

## Codex

Activation uses the sole configured native agent directory or `.agents` for multiple
agents. The activation skill defines safe migration, overrides and worktree precedence.

The same activation routing, external-update-before-stamp ordering, and cold-start pointer apply. Trusted native PreCompact hooks interrupt manual compaction for stale or absent signals; automatic compaction warns.

Codex lifecycle guidance shares the file/external handoff contract while the separate OpenCode port retains its own lifecycle integration.
