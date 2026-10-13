---
id: TASK-5
title: 'Harness registry, preflight and the Claude Code adapter'
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - harnesses
  - claude
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The grid needs to know the three harnesses (names, default models, preflight, CLI version, auth env names, scrubbed environment) and an adapter per harness that builds argv, environment and injection and folds stdout into the trial record. Claude Code is the default harness and the reference adapter (SPEC.md Grid, Agent CLIs: common rules and claude). Builds groma components harnesses and claude.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Unknown harness names fail with "unknown harness 'x'; valid harnesses: claude, codex, opencode"; harness lists keep order and drop duplicates; default models match the spec table
- [ ] #2 Preflight prints "<harness>: CLI not found on PATH" or "<harness>: no credentials — set one of <NAMES>" per the spec rules; --version gives the trimmed stdout, "unknown" when empty, "unavailable" when missing or slower than 30 s
- [ ] #3 Claude argv, env scrub (every CLAUDE* var and the four XDG vars), per-run HOME and CLAUDE_CONFIG_DIR and CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 match the spec; --bare is never passed
- [ ] #4 Plugin, skill (synthetic eval-<skill> plugin) and agent (--agents JSON) injection match the spec
- [ ] #5 Folding fixtures A1, A2 and A3 gives the spec expectations (plugins, plugin_errors, tool_names, skill_used, result, cost, duration, turns, tokens, event error)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
