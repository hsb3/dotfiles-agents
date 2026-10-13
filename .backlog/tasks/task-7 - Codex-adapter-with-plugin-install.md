---
id: TASK-7
title: Codex adapter with plugin install
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-5
  - TASK-1
references:
  - codex
priority: high
type: feature
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Codex is the third harness: exec --json argv, per-run HOME and CODEX_HOME, CODEX_API_KEY from OPENAI_API_KEY, skill/agent/plugin injection where a plugin is installed through a local marketplace and two codex plugin commands whose failure becomes an injection-failure row, and its item-event fold (SPEC.md codex). Builds groma component codex.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 argv and environment match the spec, never passing --ignore-user-config
- [ ] #2 Skill injection copies to codex-home/skills/<name>/; agent injection writes codex-home/agents/<name>.toml with exactly name, description and developer_instructions as JSON string literals
- [ ] #3 Plugin injection builds codex-market/ with the spec marketplace.json and runs marketplace add then plugin add with a 60 s timeout; a failing step yields "codex plugin install failed: <error text>" and that step's exit code
- [ ] #4 Folding fixtures A7, A8 and A9 gives the spec expectations, and success needs exit 0 and a non-empty result
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
