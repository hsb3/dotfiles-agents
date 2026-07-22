# update-config

Configure the Claude Code harness through its settings files, safely and idiomatically.
Routes every change to the correct file by precedence (managed policy vs user vs project
vs machine-local), applies narrowest-scope allow/deny/ask permission rules, implements
automated behaviors as directory-based hooks (config plus script file — never inline
shell strings in settings), sets env vars, and registers MCP servers.

## When it triggers

Use it for any request to add or move a permission rule, set up a hook, automate
something "always / every time / whenever" (those require hooks — the harness executes
hooks; instructions and memory cannot fulfill them), change a setting, add an env var,
register an MCP server, or debug why a setting is not taking effect. Every edit ends
with a verification step: JSON validity plus a take-effect check, including when a fresh
session is required.

## Install

```
claude plugin install update-config@dotfiles-agents
```

Standalone-only — it does not ship inside any bundle. Ships copy-pasteable JSON examples
and a self-contained example hook template (stdlib-only).
