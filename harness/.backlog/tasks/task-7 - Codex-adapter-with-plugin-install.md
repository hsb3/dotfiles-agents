---
id: TASK-7
title: Codex adapter with plugin install
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:17'
labels: []
milestone: m-0
dependencies:
  - TASK-5
  - TASK-1
references:
  - codex
  - harnesses
  - codex-cli
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/codex.md
  - .groma/systems/harness/containers/agent-harness-cli/components/harnesses.md
  - src/codex.ts
  - src/harnesses.ts
  - test/codex.test.ts
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
- [x] #1 argv and environment match the spec, never passing --ignore-user-config
- [x] #2 Skill injection copies to codex-home/skills/<name>/; agent injection writes codex-home/agents/<name>.toml with exactly name, description and developer_instructions as JSON string literals
- [x] #3 Plugin injection builds codex-market/ with the spec marketplace.json and runs marketplace add then plugin add with a 60 s timeout; a failing step yields "codex plugin install failed: <error text>" and that step's exit code
- [x] #4 Folding fixtures A7, A8 and A9 gives the spec expectations, and success needs exit 0 and a non-empty result
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/codex.ts: codex adapter: exec --json argv (never --ignore-user-config), per-run HOME + CODEX_HOME, CODEX_API_KEY from OPENAI_API_KEY (CODEX_ scrub via prefix), skill copy, agent .toml (name, description, developer_instructions as JSON string literals), plugin install via local marketplace + two codex plugin commands through runProcess (60 s, trial env, cwd ws) mapping failures to 'codex plugin install failed: <error text>' and the step's exit code; item-event fold; success = exit 0 and non-empty result; wall-clock duration.
2. Register in adapterFor.
3. test/codex.test.ts: argv, env, injections (incl. stubbed install success and failure), folds A7-A9.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 57 pass, 0 fail. test/codex.test.ts: registration/default model/preflight, exact argv, env scrub and CODEX_API_KEY, skill copy, agent TOML (JSON string literals), plugin install with stubbed A10 outputs checking marketplace.json, argv, cwd = ws and env of both steps, the spec failure case (stderr "plugin not found", exit 1 -> "codex plugin install failed: plugin not found"), missing executable, folds of A7, A8, A9 and the top-level error rule. groma: matched 1; accepted codex and codex -> run-dirs, candidate-extender, subprocess, codex-cli; added codex <-> harnesses rows; lint clean.
Product calls: a failing install step error text is its trimmed stderr, else trimmed stdout, else "exit <code>"; timeout gives "timeout after 60s" and a missing codex "executable not found: codex", both with exit -1; result is "" when no agent_message arrives; CODEX_API_KEY is set only when OPENAI_API_KEY is present.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/codex.ts (exec --json argv, per-run HOME/CODEX_HOME with CODEX_API_KEY, skill/agent TOML/plugin-marketplace injection with install failure mapping, item-event fold, success needs a non-empty result) and registered it. Verified by 12 tests incl. fixtures A7-A10.
<!-- SECTION:FINAL_SUMMARY:END -->
