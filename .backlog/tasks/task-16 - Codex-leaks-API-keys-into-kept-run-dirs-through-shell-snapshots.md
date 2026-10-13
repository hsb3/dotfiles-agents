---
id: TASK-16
title: Codex leaks API keys into kept run dirs through shell snapshots
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:42'
updated_date: '2026-10-13 03:47'
labels: []
milestone: m-1
dependencies: []
references:
  - codex
  - harnesses
  - trial
modified_files:
  - >-
    .backlog/decisions/decision-1 -
    Harness-adapters-behind-one-interface-resolved-at-call-time.md
  - .groma/systems/harness/containers/agent-harness-cli/components/codex.md
  - .groma/systems/harness/containers/agent-harness-cli/components/harnesses.md
  - SOP-FEEDBACK.md
  - SPEC.md
  - src/claude.ts
  - src/codex.ts
  - src/harnesses.ts
  - src/opencode.ts
  - test/codex.test.ts
  - test/trial.test.ts
priority: high
type: bug
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the coordinator's live check (2026-10-12, codex-cli 0.162.1): a timed-out codex trial kept its run dir (as failed trials do). codex-home/shell_snapshots/*.sh in that dir held the literal values of ANTHROPIC_API_KEY and OPENAI_API_KEY, because codex snapshots the shell environment by default (feature shell_snapshot, stable, on). The harness also passes every provider key to codex, though codex only needs CODEX_API_KEY.

Requirement (amends SPEC.md, codex section): pass `--disable shell_snapshot` to codex exec and to the plugin-install commands. The codex child environment carries CODEX_API_KEY and none of ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_GENERATIVE_AI_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY or GROQ_API_KEY. "Nothing the harness writes contains a credential" now also covers the files a CLI writes into a kept run dir.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex argv (exec and both plugin-install commands) includes --disable shell_snapshot
- [x] #2 The codex child env has CODEX_API_KEY and none of the six provider key names
- [x] #3 A test keeps a failed codex run dir (stub writes its env into codex-home/shell_snapshots unless --disable shell_snapshot is passed) and finds no credential value anywhere in it
- [x] #4 SPEC.md codex section states both rules
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. harnesses.ts: Adapter gains withheldEnv (names removed from the child env after the per-run values are built); childEnv applies it. claude and opencode withhold nothing; codex withholds the six provider key names (CODEX_API_KEY is still derived from OPENAI_API_KEY first).
2. codex.ts: --disable shell_snapshot on codex exec and on both plugin-install commands.
3. Tests: argv of exec and both install commands; child env has CODEX_API_KEY and none of the six names; a failed codex trial (stub dumps its env into codex-home/shell_snapshots unless --disable shell_snapshot is passed) keeps its run dir and no credential value appears in any file in it.
4. SPEC.md codex section (argv, environment, plugin install) and the credential rule.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 114 pass, 0 fail. test/codex.test.ts: exec argv and both install commands carry `--disable shell_snapshot`; childEnv for codex has CODEX_API_KEY and none of the six provider names; install calls see no OPENAI_API_KEY. test/trial.test.ts: a stub codex that, like 0.162.1, dumps its environment into $CODEX_HOME/shell_snapshots unless `shell_snapshot` is disabled; a failed plugin trial keeps its run dir and no file in it contains any of the six key values (CODEX_API_KEY included). Mutation checks: without --disable the leak test fails; with nothing withheld the env, install and leak tests fail. SPEC.md codex section (argv block and rationale, withheld keys, plugin-install commands) and the common credential rule amended. groma: no planned component (draft v1-1 tags codex and harnesses); scan created 0, lint clean; overviews updated; decision-1 Consequences extended.
Product calls: --disable shell_snapshot goes after --dangerously-bypass-hook-trust in exec and after --json in the install commands (placement to confirm in the next live check); OPENAI_API_KEY itself is withheld from codex too (only CODEX_API_KEY carries it); withheldEnv is a new Adapter field, empty for claude and opencode.
First attempt crashed every CLI start: codex read AUTH_ENV_NAMES at module load through the registry import cycle (TDZ); now a getter, recorded in decision-1.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
codex now runs exec and both plugin-install commands with --disable shell_snapshot and gets CODEX_API_KEY but none of the six provider keys (new Adapter.withheldEnv applied by childEnv), so a kept run dir holds no credential. SPEC.md amended; verified by updated codex tests and a kept-run-dir scan test, all mutation-checked.
<!-- SECTION:FINAL_SUMMARY:END -->
