# waves

Drives a project's open backlog to closed through triage, wave planning, and isolated
agent crews — refresh the triage view, group buildable items into branch-sized waves,
launch worktree-isolated teams, verify and land each wave in order, reconcile, externalize.

## When it triggers

Use it when the user says "work through the waves", "launch isolated teams to resolve/close
the issues", "run the backlog", "triage and execute", points at the triage view, or asks to
plan development branches around open items. Use `/waves init` to create the triage view in
a project that lacks one.

## Trackers

The campaign loop is tracker-agnostic. It needs three operations from whatever holds the
backlog — an inventory, a rewritable triage view that lives off commit history, and a way to
land a wave and close its items. Bindings ship for GitHub issues, kata, and Kaneo under
`references/`; a tracker without one is usable by naming those three operations up front.

Under the kata binding, note that its GitHub sync is import-only: an imported mirror is an epic to
decompose, never a card to rewrite.

Tracker and code forge are separate everywhere except GitHub, so closing an item and landing
its code are two steps unless the tracker is GitHub itself.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — composes the delegation skill for each
wave's delegation architecture and the handoff skill to close the session.
