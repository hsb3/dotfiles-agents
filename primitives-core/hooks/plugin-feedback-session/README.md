# plugin-feedback-session

Tells the primary session that a defect it hits in a plugin **from this marketplace** is
reportable, and points at the reporter that files it to a fixed template. The primary
session may file either kind: a bug or a feature request. A plugin cannot ship a line into
a consumer's CLAUDE.md, so the reminder arrives as injected context instead.

The offer stops at this marketplace's own plugins because that is where the reporter files
(it reads the reporting plugin's manifest for the target). A defect in a plugin from
somewhere else belongs in that project's own tracker.

Carries the reporter, `report_issue.py`, which the companion hook
(`plugin-feedback-worker`) points at too.

## When it fires

Session start (`SessionStart`) on `startup`/`clear` only — never on `resume` or `compact`,
where the session already carries its context and a second nudge is noise.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PLUGIN_FEEDBACK_DISABLED` | unset | Any non-empty value stands the reminder down |
| `CLAUDE_PLUGIN_ROOT` | set by Claude Code | Anchor for the reporter path; falls back to this file's own directory |

The reporter's own variables (`PLUGIN_FEEDBACK_REPO`, the per-kind label overrides) are
documented in the plugin README.

Stateless: no ledger, no state file, writes nothing anywhere, and fails open on every
error path.

## Install

```
claude plugin install plugin-feedback@dotfiles-agents
```
