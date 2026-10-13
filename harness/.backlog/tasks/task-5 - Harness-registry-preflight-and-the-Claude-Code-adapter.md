---
id: TASK-5
title: 'Harness registry, preflight and the Claude Code adapter'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:15'
labels: []
milestone: m-0
dependencies:
  - TASK-3
references:
  - harnesses
  - claude
modified_files:
  - >-
    .backlog/decisions/decision-1 -
    Harness-adapters-behind-one-interface-resolved-at-call-time.md
  - .groma/systems/harness/containers/agent-harness-cli/components/claude.md
  - .groma/systems/harness/containers/agent-harness-cli/components/harnesses.md
  - src/claude.ts
  - src/harnesses.ts
  - test/claude.test.ts
  - test/harnesses.test.ts
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
- [x] #1 Unknown harness names fail with "unknown harness 'x'; valid harnesses: claude, codex, opencode"; harness lists keep order and drop duplicates; default models match the spec table
- [x] #2 Preflight prints "<harness>: CLI not found on PATH" or "<harness>: no credentials — set one of <NAMES>" per the spec rules; --version gives the trimmed stdout, "unknown" when empty, "unavailable" when missing or slower than 30 s
- [x] #3 Claude argv, env scrub (every CLAUDE* var and the four XDG vars), per-run HOME and CLAUDE_CONFIG_DIR and CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 match the spec; --bare is never passed
- [x] #4 Plugin, skill (synthetic eval-<skill> plugin) and agent (--agents JSON) injection match the spec
- [x] #5 Folding fixtures A1, A2 and A3 gives the spec expectations (plugins, plugin_errors, tool_names, skill_used, result, cost, duration, turns, tokens, event error)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/harnesses.ts: Harness names, parseHarnessList (order kept, duplicates dropped, unknown -> UnknownHarness error with the spec message), AUTH_ENV_NAMES and authEnvPresent, scrubEnv (prefix + four XDG vars), preflight messages, cliVersion (30 s, unknown/unavailable), jsonLines stream parser, TrialRecord and emptyRecord, the Adapter interface and adapterFor registry.
2. src/claude.ts: claude adapter: argv (never --bare), per-run HOME/CLAUDE_CONFIG_DIR + betas var (claudeRunEnv shared with the grader), plugin/skill/agent injection, stream-json fold, success = exit 0.
3. Tests: test/harnesses.test.ts (names, defaults, preflight with stub PATH, version, scrub) and test/claude.test.ts (argv, env, injections, folds of A1-A3).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 35 pass, 0 fail. test/harnesses.test.ts: list parsing and the exit-3 message, auth names, scrub (CLAUDE* and four XDG only), childEnv, preflight with a stub PATH, --version trimmed/unknown/unavailable, JSONL parsing. test/claude.test.ts: argv (no --bare, empty --setting-sources), per-run dirs and betas var, plugin/skill/agent injection files and args, folds of A1, A2, A3 per Appendix A. groma: matched 2, accepted harnesses, claude, harnesses -> subprocess, claude -> run-dirs, claude -> candidate-extender; added claude -> harnesses and harnesses -> claude for the derived/registry links; lint clean. Decision-1 records the adapter interface and call-time resolution.
Product calls: empty entries in --harness are ignored; the opencode credentials message joins the six names with ", "; `--version` runs with the scrubbed environment (no per-run home) in the current dir; claude result is null when no result event arrives, and an is_error result with no text gives an empty event error.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/harnesses.ts (harness list parsing/validation, preflight, CLI version, env scrub, auth names, Adapter contract, TrialRecord, JSONL helpers, adapter lookup) and src/claude.ts (claude argv, per-run env shared with the grader, plugin/skill/agent injection, stream-json fold). Verified by 16 new tests incl. fixtures A1-A3; decision-1 records the adapter design.
<!-- SECTION:FINAL_SUMMARY:END -->
