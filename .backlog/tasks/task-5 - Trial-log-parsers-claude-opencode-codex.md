---
id: TASK-5
title: 'Trial log parsers: claude, opencode, codex'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - logs
priority: high
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
load-runs normalizes each trial log into run meta, run events, tool calls, excised artifacts and a rollup; the three harness formats differ and the exact vectors of Appendix C.3 are mandatory. Builds the logs component.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The claude log vector yields exactly the C.3 run meta, event rows, seq 4 and seq 6 payloads, tool calls and two deduplicated artifacts
- [ ] #2 The opencode log vector yields exactly the C.3 run meta, rollup, event rows, seq 1 payload and tool calls
- [ ] #3 Codex logs yield event types, roles, text, token fields, tool calls from their last event with no_result for unfinished items, session_id from thread.started, null timestamps and the rollup the spec states
- [ ] #4 Lines split as Python str.splitlines() does, seq counts blank and non-object lines, and claude ISO timestamps convert as the spec formula states
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
