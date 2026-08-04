# owner-signoff

Present a batch of decisions, approvals, or questions to the project owner as a local HTML
form in their browser instead of a wall of chat questions. The owner answers inline at
their own pace — every recommendation preselected, so agreeing with everything is one
click — and the answers land in a JSON file the session picks up the moment they submit.

## When it triggers

Use it when multiple items need the owner's input at once (sign-offs, dispositions,
priorities, open questions), when the owner asks "what do you need from me", or when they
want a summary/quiz they can react to. The skill ships the HTML form template and a
one-shot localhost server (binds 127.0.0.1 only, accepts exactly one submit, then exits),
plus a download fallback for much-later submits.

## Install

```
claude plugin install owner-signoff@dotfiles-agents
```

Standalone-only — it does not ship inside any bundle. Needs only `python3` (stdlib).
