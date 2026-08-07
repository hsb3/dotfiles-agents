# waves

Drives a repo's open-issue backlog to closed through triage, wave planning, and isolated
agent crews — refresh a pinned triage issue, group buildable issues into branch-sized waves,
launch worktree-isolated teams, verify and merge each PR in order, reconcile, externalize.

## When it triggers

Use it when the user says "work through the waves", "launch isolated teams to resolve/close
the issues", "run the backlog", "triage and execute", points at the pinned triage issue, or
asks to plan development branches around open issues. Use `/waves init` to create the pinned
triage issue in a repo that lacks one. Requires a GitHub repo with issues.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the atelier bundle (not standalone) — composes the delegation skill for each
wave's delegation architecture and the handoff skill to close the session.
