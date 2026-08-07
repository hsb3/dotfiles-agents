---
id: TASK-14
title: 'atelier: codify concurrent-session coordination (coord branch protocol)'
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-07 00:47'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/219'
priority: medium
type: feature
ordinal: 400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #219. Field-proven 2026-07-27 (two /waves sessions, one checkout): coord/<date> branch of empty commits carrying WHO / ACTIVE SUBAGENTS / CLAIMS+MERGE QUEUE / SURFACES / REPLY. Codify as a session-coord skill and/or SessionStart hook that surfaces the latest coord message. Open design points (branch naming, pruning, waves Phase-0 check) in the GH record.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Protocol shipped as skill and/or hook in foreman-kit
- [ ] #2 Waves Phase 0 checks for a live coord branch
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 00:47
---
Re-scoped 2026-08-07: the card targeted 'foreman-kit', which no longer exists — that plugin was renamed to 'atelier' in PR #260. The target for the skill/hook is plugins/atelier/ and primitives-core/. The card's premise is otherwise intact; only the plugin name was stale.

Fresh motivating evidence from this session, which is exactly the failure the card describes: a session began work at dev tip 03cfd0e, ran a fetch, and dispatched agents. Minutes later a CONCURRENT session merged PR #265 into dev, moving the tip to 0a432f6 underneath the running session. Nothing warned either side. The first session only noticed because 'git worktree list' happened to print a HEAD that disagreed with a rev-parse taken moments earlier.

That is the concrete cost this card exists to prevent, and it argues for the SessionStart-hook half of the design over the skill-only half: a skill has to be invoked to help, whereas a hook can announce 'another session is active on this branch' at cold start, before any work is planned.
---
<!-- COMMENTS:END -->
