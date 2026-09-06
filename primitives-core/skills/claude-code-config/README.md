# claude-code-config

The Claude Code configuration skill — settings and their precedence, permissions, hooks
as directories, environment variables, and MCP servers, with a verification step baked in.
Changing a single setting is one facet of it, not the whole job.

## When it triggers

Use it for any request to add or move a permission rule, set up a hook, automate
something "always / every time / whenever" (those require hooks — the harness executes
hooks; instructions and memory cannot fulfill them), change a setting, add an env var,
register an MCP server, or debug why a setting is not taking effect. Every edit ends
with a verification step: JSON validity plus a take-effect check, including when a fresh
session is required. Routes every change to the correct file by precedence (managed
policy vs user vs project vs machine-local), applies narrowest-scope allow/deny/ask
permission rules, and implements automated behaviors as directory-based hooks (config
plus script file — never inline shell strings in settings).

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle. Ships copy-pasteable JSON examples
and a self-contained example hook template (stdlib-only).
