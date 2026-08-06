---
id: TASK-037
title: 'atelier reviewer: agent-memory write lands in the target project''s tree'
status: To Do
assignee: []
created_date: '2026-08-06 23:49'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/254'
priority: low
type: bug
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #254: a reviewer dispatched with the standard report-only brief ('you never edit files', 'no scratch files') finished its verification and then wrote .claude/agent-memory/foreman-kit-reviewer/ inside the target project's working tree, and self-reported the write as if it were compliant. In this repo .claude/agent-memory/ happens to be gitignored, so no harm; in a repo without that ignore line the write dirties git status mid-review and risks being swept into a later commit. Checked #260 (foreman-kit -> atelier rename + doctrine rewrite, config-custody + worker-context hooks): grepped worker-context, config-custody, and every agent body for 'agent-memory' -- zero hits, so this is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reviewer's agent-memory writes are pointed at a session/scratch location outside the target repo, or are opt-in per dispatch rather than automatic
- [ ] #2 If project-tree memory is kept intentionally, the plugin ships .claude/agent-memory/ gitignore guidance and the reviewer's self-description explicitly carves the memory write out of its 'report-only' contract
- [ ] #3 Reviewer's stated contract and its actual filesystem behavior agree -- no undisclosed writes
<!-- AC:END -->
