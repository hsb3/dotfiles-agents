# handoff

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

Ships in the atelier bundle (not standalone) — it closes the session that the delegation
skill runs and the waves skill drives across a backlog.
