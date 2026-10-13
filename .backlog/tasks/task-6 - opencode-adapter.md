---
id: TASK-6
title: opencode adapter
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - opencode
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode is the second harness: argv with --standalone (mandatory, or a background service outlives the trial), per-run HOME and OPENCODE_CONFIG_DIR, skill and agent injection with the agent translation rules, and its JSON-event fold (SPEC.md opencode). Plugins are unsupported. Builds groma component opencode.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 argv is opencode run <prompt> --format json --auto --standalone -m <provider/model>, prefixing anthropic/ when the model has no /
- [ ] #2 Env scrubs OPENCODE* and XDG vars and sets HOME and OPENCODE_CONFIG_DIR inside the run dir, for both configs
- [ ] #3 Skill injection copies to oc-config/skills/<name>/ with the permission opencode.json; an invalid skill name or a plugin is unsupported
- [ ] #4 Agent translation produces the spec output for the scout example, including model and permission rules
- [ ] #5 Folding fixtures A4, A5 and A6 gives the spec expectations
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
