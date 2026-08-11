---
id: TASK-068
title: 'atelier: telemetry has no time axis, so run-length blowups cannot be diagnosed'
status: To Do
assignee: []
created_date: '2026-08-11 18:20'
labels:
  - primitives
milestone: m-3
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/300'
priority: high
type: feature
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Field report #300 (learn-pocketbase, severity raised to major by the owner): tasks expected to take ~30 minutes routinely take 2-4 hours, and atelier's own logs cannot say where the time goes. logs/delegation.jsonl records carry only agent_id, agent_type, ctx_tokens, model, session_id — no timestamps, no start/end, no durations — so per-agent wall clock, idle gaps between chain links, time-to-first-delegation, and stall windows are all uncomputable. The #299/#306 deadlock (TASK-067) was caught only by an external overseer hand-diffing transcript mtimes; atelier logged nothing about the 12+ minute stall.

Two parts, per the report:
(a) one-off analysis over accumulated logs + transcripts ranking the dominant causes of the blowup — field candidates: the TASK-067 notification deadlock, sequential chains where links could overlap, managers idling on notifications that never arrive, gate runs serialized behind port contention;
(b) instrument the telemetry hooks so each record carries start/stop timestamps and duration, and stall-shaped events (agent settled with pending children beyond a threshold) are logged, making that analysis routine instead of forensic.

Constraint from .claude/HANDOFF.md §5: delegation.jsonl history before 2026-08-07 inflates the parent session ~9x and uses the old 'lead' name — truncate before any analysis spanning that boundary.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 delegation.jsonl records carry start/stop timestamps and durations (or equivalent fields), so per-agent wall clock and inter-link idle gaps are computable from the logs alone
- [ ] #2 Stall-shaped events are logged: an agent settled with pending children beyond a named threshold produces a record an overseer can query, replacing transcript-mtime forensics
- [ ] #3 A one-off analysis over the accumulated logs and transcripts ranks the dominant causes of the observed 30-minutes-becomes-hours blowup, recorded on this card, honoring the pre-2026-08-07 truncation rule
- [ ] #4 The analysis distinguishes 'agent working long' from 'agent waiting dead' for at least the incidents already on file
<!-- AC:END -->
