---
name: backlog-md-task-management
description: Henry runs task management on Backlog.md; GitHub issues are bug intake only (ruled for dotfiles-agents 2026-08-03)
metadata: 
  node_type: memory
  type: user
  originSessionId: 23a9b877-fc10-47ea-aeee-9b1b693a43c7
---

Henry uses Backlog.md (`backlog` CLI) for task management across projects (first
learn-pocketbase, then dotfiles-agents by explicit ruling on 2026-08-03 — recorded there as
backlog decision-1). In repos that adopted it, GitHub issues are reserved for bug reports;
plan work as backlog tasks (`backlog task create`), park owner-held items as drafts, record
rulings with `backlog decision create`. He also works in both Claude Code and opencode, so
extender tooling he authors must serve both runtimes (see [[one-repo-dual-target-ruling]]).

**Why:** he committed to this split explicitly; proposing GH-issue-based planning in a
Backlog.md repo works against his conventions.

**How to apply:** before filing or triaging work items, check for a `backlog/` tree; use its
conventions when present.
