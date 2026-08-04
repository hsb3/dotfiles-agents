---
id: TASK-25
title: 'waves skill: backlog-aware mode for Backlog.md-managed projects'
status: To Do
assignee: []
created_date: '2026-08-04 02:20'
updated_date: '2026-08-04 02:54'
labels:
  - product
  - foreman-kit
  - waves
dependencies: []
priority: medium
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The foreman-kit waves skill drives a GH-ISSUE backlog (pinned triage issue, issue-grouped waves) and does not work on a project whose task system is Backlog.md (this repo since decision-1). Product change affecting consumers: add a backlog-aware mode (triage/wave-plan/execute against backlog tasks + milestones instead of issues + a pinned triage issue) or a scoped successor skill for backlog-managed projects, keeping the GH-issue mode for repos that still use issues. Related: task-23 (triage-template ordering bug) touches the same skill; coordinate if both are picked up.
<!-- SECTION:DESCRIPTION:END -->
