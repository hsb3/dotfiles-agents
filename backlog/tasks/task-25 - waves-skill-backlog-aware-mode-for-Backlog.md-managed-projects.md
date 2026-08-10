---
id: TASK-25
title: 'waves skill: backlog-aware mode for Backlog.md-managed projects'
status: To Do
assignee: []
created_date: '2026-08-04 02:20'
updated_date: '2026-08-10 02:25'
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
The foreman-kit waves skill drives a GH-issue backlog (pinned triage issue, issue-grouped waves) and can't run on a project whose task system is Backlog.md — including this repo, since decision-1. Add a backlog-aware mode (triage / wave-plan / execute against backlog tasks and milestones, with the delivery plan recorded in the backlog rather than a pinned GH issue), or a scoped successor skill — keep the GH-issue mode for repos that still use issues. Must honor decision-7's hand-edit rule (the backlog CLI's write path can rewrite sibling task files) and carry TASK-23's structural invariants (open work leads; executed plans collapse into trailing history) into whatever artifact holds the plan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The skill states which of the two shapes it is — a mode inside waves, or a separate successor skill — justified in one sentence rather than left open
- [ ] #2 Given a Backlog.md-managed repo, the skill plans waves from backlog tasks and milestones instead of requiring a pinned GitHub issue
- [ ] #3 All backlog reads and writes go through the backlog CLI, never by editing task markdown directly, per decision-7
- [ ] #4 The skill detects which mode applies from the repo itself (presence of a backlog/ directory and config) rather than requiring the dispatcher to say so
- [ ] #5 The GitHub-issue path is unchanged for repos without Backlog.md — verified by running the existing path against a repo that has no backlog/
- [ ] #6 The structural invariants from TASK-23 hold: open work leads, executed work does not bury it
- [ ] #7 make ci is green
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:10
---
Owner ruling 2026-08-07: SCOPE IT — the session drafts acceptance criteria for the owner's review rather than dropping the card.

The card had no acceptance-criteria section at all, named no files, and described itself as 'a backlog-aware mode OR a scoped successor skill', which are different projects. It was unstartable as written; these criteria are the draft for review, not a settled contract.

Two things shaped them. First, the card referenced decision-7 and TASK-23 as design constraints in prose while its frontmatter declared no dependencies — those constraints are now criteria rather than background reading. Second, and more usefully: this session drove this repo's entire backlog through triage, wave planning, delegation, and closeout BY HAND, without the skill. That run is the best available evidence for what the skill should do, and the criteria above reflect what actually mattered in practice — auto-detecting the mode from the repo rather than being told, and routing every write through the CLI.

The first criterion deliberately forces the mode-versus-successor-skill question to be answered rather than carried forward, since that ambiguity is what made the card unstartable.
---
<!-- COMMENTS:END -->
