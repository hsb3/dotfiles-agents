---
id: TASK-5
title: 'Trial log parsers: claude, opencode, codex'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:09'
updated_date: '2026-10-13 03:37'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - logs
modified_files:
  - .groma/systems/evals/containers/evals-cli/components/logs.md
  - SOP-FEEDBACK.md
  - src/logs.ts
  - test/logs.test.ts
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
- [x] #1 The claude log vector yields exactly the C.3 run meta, event rows, seq 4 and seq 6 payloads, tool calls and two deduplicated artifacts
- [x] #2 The opencode log vector yields exactly the C.3 run meta, rollup, event rows, seq 1 payload and tool calls
- [x] #3 Codex logs yield event types, roles, text, token fields, tool calls from their last event with no_result for unfinished items, session_id from thread.started, null timestamps and the rollup the spec states
- [x] #4 Lines split as Python str.splitlines() does, seq counts blank and non-object lines, and claude ISO timestamps convert as the spec formula states
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Write src/logs.ts: shared helpers (Python splitlines/strip, JSON-object line iteration with seq, UTF-8 decode with replacement, code-point head, artifact registry with sha256 and excision markers), then the claude, opencode and codex parsers behind parseLog.
2. Write test/logs.test.ts: C.3 claude and opencode vectors exactly (events, payloads, tool calls, artifacts, meta, rollup), codex tests from the spec's captured log and tool-item shapes, splitlines and timestamp tests.
3. Run the gate: bunx tsc --noEmit && bun run build:ui && bun test.
4. groma scan (matched 1), groma accept logs, re-read overview, groma scan && groma lint; refactor any duplicate-logic finding.
5. Record modified files from git, check ACs/DoD with evidence, Done, commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls (open in the spec):
- Claude assistant rows carry `text` only when the event has at least one text block (C.3 seq 5 has none and lists no text).
- Claude tool_result join: the first tool_result per tool_use_id wins; a result without a boolean `is_error` counts as not an error (status ok, is_error false on the call); the event row carries is_error only when the block has a boolean.
- Claude run meta: the first system/init counts; the last result event gives model_usage and the fallback session_id; provenance is null without an init.
- Claude ts: an ISO time without a zone, or an invalid date, is null; fractional seconds beyond 6 digits are truncated, as Python fromisoformat does.
- Claude mirror dedup compares tool_use_result string leaves with tool_result `content` values that are strings (not text blocks inside a content list).
- Opencode: a tool_use without `state.status` gets status "" (not sent); cost_usd sums the numeric step_finish costs left to right, null when none has one; missing token counts add 0; a data: URI without `;base64` is percent-decoded to bytes.
- Codex: an unfinished item (no_result) takes is_error from its last item (false unless status failed or exit_code non-zero); an `error` item row has no text (the spec names none); a missing item.type gives event_type `<type>/`.
- Rows omit undefined optional fields; `artifacts` is always a list (empty when none); tool-call nulls are kept as the vectors show.
- No flow added: the only relation of logs, `runs -> logs`, stays draft until TASK-6 builds runs.
API as shipped: the interface the task specified, plus exports `pyStrip`, `isoToMillis`, types `ArtifactKind` and `Rollup`. logs.ts imports nothing from store.ts or canonical.ts; hashing uses Bun.CryptoHasher.

Evidence:
- `bunx tsc --noEmit && bun run build:ui && bun test`: exit 0, 60 pass, 0 fail, 2370 expect() calls across 6 files (test/logs.test.ts: 21 pass, 66 expects).
- AC1: test/logs.test.ts "claude log (C.3)" compares meta, event rows, seq 4/6 payloads, tool calls and the two artifacts (sha, kind, mime, size, filename, textRef) with the vectors exactly.
- AC2: "opencode log (C.3)" compares meta, rollup, event rows, seq 1 payload and tool calls (after store.ts coerceJson on output, `run` placeholder dropped).
- AC3: "codex log" tests the spec captured log and documented tool-item shapes: event types, roles, text (5000 cap), token fields, tool calls from the last event with no_result for an unfinished item, session_id from the first thread.started, null ts, rollup with null cost/duration.
- AC4: "splitLines and strip", "seq" (blank/non-object lines counted, thinking_tokens dropped, every Python line break advances seq, invalid UTF-8 replaced) and "claude timestamps" (values computed in Python with the spec formula).
- groma scan: matched 1 (logs); groma accept logs; groma edit logs --overview; groma scan && groma lint: No findings, exit 0 (first lint flagged exciseLongText/exciseBase64 as duplicates; merged into one exciseField helper).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/logs.ts, the logs component: parseLog(harness, bytes) turns a claude, opencode or codex trial log into run meta, event rows, tool calls, content-addressed excised artifacts and (opencode, codex) a rollup, with Python splitlines/strip line rules and the spec claude timestamp formula; pure, no DB or file access. Shared helpers (eventLines, ArtifactRegistry.excise/exciseField, eventRow, tokenFields, tokenRollup) keep the three parsers free of duplicate logic. test/logs.test.ts checks the C.3 claude and opencode vectors exactly and the codex rules from the spec text. Gate green (60 tests); groma scan matched and accepted logs; groma lint clean. runs -> logs stays draft for TASK-6.
<!-- SECTION:FINAL_SUMMARY:END -->
