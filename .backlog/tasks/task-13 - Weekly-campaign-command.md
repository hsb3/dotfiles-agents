---
id: TASK-13
title: Weekly campaign command
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies:
  - TASK-11
references:
  - campaign
  - campaign-logs
priority: high
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The weekly schedule runs every cased candidate with a dated label so a same-day rerun resumes, and logs the transcript (SPEC.md Campaign). Builds groma components campaign and the campaign-logs store.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Requires --cases-dir and --candidates-root; discovers candidates as sorted subdir names minus _template and smoke-echo; none prints "no candidates discovered under <dir>" and exits 1
- [ ] #2 Resolves each candidate path (first <root>/*/<name>/ in sorted order, else <root>/agents/<name>.md), warning and failing a missing one
- [ ] #3 Runs each candidate as the run command would with the campaign flags and default label weekly-<YYYYMMDD>, printing FAILED lines, the reports and the completion line, and appends everything to <dir of --results>/campaign-logs/<label>.log
- [ ] #4 --dry-run prints the DRYRUN lines, runs and writes nothing, and exits by the same rule
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
