---
id: TASK-25
title: 'waves skill: backlog-aware mode for Backlog.md-managed projects'
status: To Do
assignee: []
created_date: '2026-08-04 02:20'
updated_date: '2026-08-06 21:33'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: medium
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The foreman-kit waves skill drives a GH-ISSUE backlog (pinned triage issue, issue-grouped waves) and cannot run on a project whose task system is Backlog.md — including this repo since decision-1. Product change affecting consumers: add a backlog-aware mode (triage / wave-plan / execute against backlog tasks + milestones, with the delivery plan recorded in the backlog rather than a pinned GH issue) or a scoped successor skill, keeping the GH-issue mode for repos that still use issues. Design constraints: the mode must honor decision-7's hand-edit rule (the backlog CLI's write path can rewrite sibling task files) and carry the task-23 structural invariants (open work leads; executed plans collapse into trailing history) into whatever artifact holds the plan.
<!-- SECTION:DESCRIPTION:END -->
