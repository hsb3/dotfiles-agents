---
id: TASK-12
title: Smoke loadability check
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:30'
labels: []
milestone: m-0
dependencies:
  - TASK-11
references:
  - smoke
  - check-loadability
  - trial
  - subprocess
modified_files:
  - .groma/flows/check-loadability.md
  - .groma/systems/harness/containers/agent-harness-cli/components/commands.md
  - .groma/systems/harness/containers/agent-harness-cli/components/smoke.md
  - src/commands.ts
  - src/smoke.ts
  - src/subprocess.ts
  - test/smoke.test.ts
priority: high
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Before spending a campaign on a candidate the owner needs to know it loads under each harness: --smoke injects it into an empty workspace, sends "Reply with exactly: OK" and prints a smoke block, writing a log but no ledger row (SPEC.md Smoke block). Builds groma component smoke.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Smoke uses the same injection, argv, environment and isolation as a with trial, in a fresh run dir deleted afterwards, and writes <runs-dir>/<harness>-smoke-<candidate>-<YYYYMMDD-HHMMSS>-<32 hex>.log with raw stdout and no header
- [x] #2 The smoke block prints harness, kind, plugins loaded (names, (none) or (not reported)), plugin_error lines, the exit line and the verdict; an unhostable kind prints the skip line and fails
- [x] #3 Exit is 0 when at least one cell ran and every cell that ran passed, else 1
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/smoke.ts: runSmoke(opts, io): load the candidate (exit 2 on error); per cell preflight (stderr, cell not run); unhostable kind -> kind line + skip line, cell fails; else fresh run dir, runAgent with the candidate and 'Reply with exactly: OK' (same injection/argv/env as a with trial), raw-stdout smoke log, smoke block (plugins loaded, plugin_error lines, exit line with the first 400 chars of the error field, verdict), run dir deleted. Exit 0 when at least one cell ran and all that ran passed, else 1.
2. commands.ts: dispatch --smoke.
3. test/smoke.test.ts through the CLI with stubs: A1 (two plugins, exit line, FAILED), A3 plugin_error line, A4 opencode (not reported) OK, opencode plugin skip, codex install failure, log name and content, no ledger written, exit codes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 98 pass, 0 fail (7.3 s). test/smoke.test.ts through src/cli.ts with stubs: A1 block (two plugin names, exit line, FAILED), raw-stdout log name and content, no ledger, run dir removed, smoke prompt/--plugin-dir/model/per-run HOME; A3 plugin_error line; A4 under opencode (not reported) OK with a missing-CLI cell not run; unhostable kind skip line with blank-line-separated blocks; codex install failure as plugin_error; exit 1 when no cell ran, exit 2 on a bad candidate. groma: matched 1; accepted smoke and 4 planned relations; added smoke -> commands, smoke -> grid, smoke -> trial-logs; flow check-loadability added; lint clean.
Bug fixed in subprocess.ts: the 2 s drain grace was a Bun.sleep that kept the process alive after every agent run (each CLI run lingered 2 s before exiting); it is now a cleared timer. Found by timing a smoke run (2.1 s -> 0.1 s); full suite 32 s -> 7 s.
Product calls: blocks are separated by one blank line; a failed codex install prints plugins loaded: (not reported), the plugin_error line and the exit line with the failing step code, and writes no log since no CLI ran; plugin entries without a string name print as compact JSON; smoke accepts and ignores run flags other than --harness/--model/--timeout/--runs-dir.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/smoke.ts (--smoke: per-cell injection into an empty workspace through the trial agent-run step, raw stdout log, smoke block, exit rule) and dispatched it from commands; fixed a lingering 2 s timer in subprocess.ts. Verified by 6 smoke tests through the CLI; flow check-loadability added.
<!-- SECTION:FINAL_SUMMARY:END -->
