# opencode-sandbox

Spins up a disposable, isolated opencode instance and hands it to the session as an MCP
server. Its `/workspace` is a Docker volume rather than a bind mount, so the instance cannot
read or write anything on the host.

## When it triggers

Use it when an agent should work somewhere that cannot touch the real machine: on a copy of
a project, on generated code, or on a long task that deserves its own scratch space. Covers
installing the CLI, seeding project context, custom config and plugins, worktrees inside the
instance, registering it with `claude mcp add`, and destroying it afterward.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
