# plugin-feedback-session

Tells the primary session that a defect it hits in a plugin **from this marketplace** is
reportable, and points at the reporter that files it to a fixed template. The primary
session may file either kind: a bug or a feature request. A plugin cannot ship a line into
a consumer's CLAUDE.md, so the reminder arrives as injected context instead.

The offer stops at this marketplace's own plugins because that is where the reporter files
(it reads the reporting plugin's manifest for the target). A defect in a plugin from
somewhere else belongs in that project's own tracker, and the reporter enforces that: a
`--plugin` id this marketplace's own `marketplace.json` does not list is refused, drafts
included, unless you pass `--allow-unlisted`.

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
documented in the plugin README. One more is test-only: `PLUGIN_FEEDBACK_LIVE_TESTS=1`
opts this repo's suite into the single check that reaches the network (the reporter's
default labels still exist in the target repo). Unset, it skips, which is what keeps the
suite runnable offline.

Stateless: no ledger, no state file, writes nothing anywhere, and fails open on every
error path.

## Install

```
claude plugin install plugin-feedback@dotfiles-agents
```

## Codex

The same lifecycle event injects additionalContext with ATELIER_HARNESS=codex.
Codex reminders default to --draft and require explicit user authorization before
filing. The reporter accepts CODEX_PLUGIN_ROOT, preserves repository attribution from
the reporting package, and can read Claude, Codex or root plugin manifests. Existing
Claude reminders and the worker feature-request tier rule remain unchanged. Tests
use local manifests/mocked transport; they create no GitHub issues.
