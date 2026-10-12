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
land a wave and close its items. Bindings ship under `references/` for GitHub issues, kata,
Backlog.md and the file tracker — one Markdown file per item under `.tasks/`, whose format is
specified in `references/file-tracker-format.md`. A project pins its tracker with a `tracker:` key in
`.claude/tracker.local.md`. Untold and unpinned, the skill detects the tracker in that
order (kata binding, GitHub issues in use, a Backlog.md board, `.tasks/`) and, finding none, falls back
to the file tracker and says so rather than refusing. `scripts/file_tracker.py` does the
detecting and parses the item files, reporting a broken one by path instead of skipping it. A
tracker without a binding is usable by naming those three operations up front.

The file tracker and Backlog.md keep the triage view in an ignored file beside the items, so it
stays off commit history but exists only in the checkout that wrote it. Neither is a forge, so
a repo with no remote lands a wave by a local `--no-ff` merge gated by its own checks.

Under the kata binding, note that its GitHub sync is import-only: an imported mirror is an epic to
decompose, never a card to rewrite. That binding also states the core label vocabulary a wave
plans against — one type label, one area label, plus the container and behaviour names — since
the grouping has to be queryable rather than living in a title prefix.

Tracker and code forge are separate everywhere except GitHub, so closing an item and landing
its code are two steps unless the tracker is GitHub itself.

## Findings the run turns up

A finding outside a wave's scope folds before it is filed: a sibling site of what the wave
already fixed is fixed in the same wave, a finding that belongs to an open item becomes a
comment on it, one with no home rides the wave's hardening list, and only what none of those
hold is filed, never as a draft. Triage intake runs the same order, so a finding a previous run
left on a hardening list is re-routed rather than filed on sight. Each landing records what the
wave closed against what it filed, so the run's totals show whether a wave shrank the backlog or
grew it.

A run on a project with no handoff names the triage view in its stop report and writes none; a view created in that run
supplies the default scope, and an empty ready set is a stop, not an empty plan. The view's
Decision gaps section is the one home for the owner queue, including session questions that
never touched the tracker. A first run skips prior-run fold sources and folds duplicate intake.

## Concurrent campaigns

Phase 0 checks for a live coordination signal before anything is planned: another session
moving the trunk under a running campaign is a known failure mode, so the tip the plan is
built on gets recorded, and a branch someone else is already on gets a landing order agreed
before a crew launches. On Claude Code the detecting is done by the `branch-activity-surfacer`
hook in the same bundle.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — composes the delegation skill for each
wave's delegation architecture and the handoff skill to close the session.

## Codex

Uses the same workflow with generated project roles and native worker routing. See the
[Codex distribution procedures](../delegation/references/dispatch-knobs.md#codex-distribution)
for setup, ownership-safe refresh, role names, and completion handling.
