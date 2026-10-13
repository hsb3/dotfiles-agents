---
id: TASK-16
title: Codex leaks API keys into kept run dirs through shell snapshots
status: To Do
assignee: []
created_date: '2026-10-13 03:42'
labels: []
milestone: m-1
dependencies: []
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
- [ ] #1 codex argv (exec and both plugin-install commands) includes --disable shell_snapshot
- [ ] #2 The codex child env has CODEX_API_KEY and none of the six provider key names
- [ ] #3 A test keeps a failed codex run dir (stub writes its env into codex-home/shell_snapshots unless --disable shell_snapshot is passed) and finds no credential value anywhere in it
- [ ] #4 SPEC.md codex section states both rules
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
