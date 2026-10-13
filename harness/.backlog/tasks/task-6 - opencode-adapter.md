---
id: TASK-6
title: opencode adapter
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:16'
labels: []
milestone: m-0
dependencies:
  - TASK-5
references:
  - opencode
  - harnesses
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/harnesses.md
  - .groma/systems/harness/containers/agent-harness-cli/components/opencode.md
  - src/harnesses.ts
  - src/opencode.ts
  - test/opencode.test.ts
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
- [x] #1 argv is opencode run <prompt> --format json --auto --standalone -m <provider/model>, prefixing anthropic/ when the model has no /
- [x] #2 Env scrubs OPENCODE* and XDG vars and sets HOME and OPENCODE_CONFIG_DIR inside the run dir, for both configs
- [x] #3 Skill injection copies to oc-config/skills/<name>/ with the permission opencode.json; an invalid skill name or a plugin is unsupported
- [x] #4 Agent translation produces the spec output for the scout example, including model and permission rules
- [x] #5 Folding fixtures A4, A5 and A6 gives the spec expectations
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/opencode.ts: opencode adapter: argv with --standalone and provider/model, per-run HOME + OPENCODE_CONFIG_DIR (OPENCODE* scrub via prefix), canHost (no plugins; skill names must match the opencode pattern, 1-64 chars), skill injection with permission opencode.json, agent translation (description JSON literal, mode subagent, model rule, permission rule), JSONL fold, wall-clock duration.
2. Register it in adapterFor.
3. test/opencode.test.ts: argv/model prefix, env, canHost, skill and agent injection (scout example), folds A4-A6.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 45 pass, 0 fail. test/opencode.test.ts: registration/default model/preflight credentials, argv and model prefix, per-run dirs, canHost (plugin, invalid and 65-char skill names), skill and agent injection files incl. the exact scout translation from the spec, model and permission rules, folds of A4, A5 (cost 0.014100000000000001), A6 and every error-field fallback. groma: matched 1, accepted opencode, opencode -> run-dirs, opencode -> candidate-extender; added opencode <-> harnesses rows; lint clean.
Product calls: result is the empty string when no text event arrives; a tools field with no mappable tool still emits `permission:` with edit and bash denied; the agent file ends with a newline after the body.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/opencode.ts (argv with --standalone and provider/model, per-run HOME and OPENCODE_CONFIG_DIR, skill and translated-agent injection, unsupported plugins and invalid skill names, JSON-event fold with wall-clock duration) and registered it. Verified by 10 tests incl. fixtures A4-A6 and the spec scout translation.
<!-- SECTION:FINAL_SUMMARY:END -->
