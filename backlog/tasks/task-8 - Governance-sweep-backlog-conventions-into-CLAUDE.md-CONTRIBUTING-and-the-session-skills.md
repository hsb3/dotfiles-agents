---
id: TASK-8
title: >-
  Governance sweep: backlog conventions into CLAUDE.md, CONTRIBUTING, and the
  session skills
status: Done
assignee: []
created_date: '2026-08-04 00:42'
updated_date: '2026-08-06 21:31'
labels:
  - governance
dependencies: []
priority: medium
type: docs
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Encode the 2026-08-03 ruling (Backlog.md = task management, GitHub issues = bug reports only) across CLAUDE.md, .github/CONTRIBUTING.md, issue templates (bug-report only), and this repo's session conventions. Note: foreman-kit's waves skill assumes a GH-issue backlog — needs a backlog-aware mode or a scoped successor for backlog-managed projects (product change, affects consumers).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 CLAUDE.md + CONTRIBUTING state the split
- [x] #2 Issue templates reduced to bug report
- [x] #3 waves-skill backlog-mode gap tracked as its own product task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Executed on chore/task-7-8-governance: CLAUDE.md 'Task system' section + CONTRIBUTING 'Where work is tracked' section state the split (incl. the hand-close-after-dev-merge gotcha and auto_commit:false convention); issue templates reduced to bug.yml (epic/feature removed, blank issues disabled with an explanatory config.yml comment); waves backlog-mode gap filed as task-25. The 'session conventions' leg (backlog-aware session skills) is carried by task-25 + the handoff refresh.
<!-- SECTION:NOTES:END -->
