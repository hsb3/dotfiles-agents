---
id: TASK-052
title: >-
  plugin-feedback files the wrong label and accepts reports about plugins it
  does not ship
status: To Do
assignee: []
created_date: '2026-08-10 02:45'
updated_date: '2026-08-10 02:52'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/282'
priority: high
type: bug
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two field-observed misfiles in the shipped reporter, both from real unattended sessions in other projects.

1. Every feature request fails to file (#282). `primitives-core/hooks/plugin-feedback-session/report_issue.py:73` sets `DEFAULT_LABELS[KIND_FEATURE] = "type:feature"`. This repo has no such label — `gh label list` returns `type:feat`, `type:fix`, `type:chore`, `decision`, `epic`. The bug path works because `type:fix` is real; the feature path is dead out of the box.

2. A report about a plugin from another marketplace landed here. On 2026-08-08 a session filed a `use-railway` defect into this tracker. `use-railway` is not in this repo — `rg -l use-railway` returns nothing — so the report had no target here and its technical claim was wrong besides. The owner deleted it on 2026-08-09 as inaccurate and out of scope, which is why no issue link survives for this half; the evidence is the filing itself, not the report content.

   The reporter documents the boundary in prose only (`report_issue.py:22-28`, and the note printed on both output paths at `:79-84`): it resolves the target from the REPORTING plugin manifest and trusts the caller to have scoped the report. Nothing checks that `--plugin <id>` is an entry the reporting marketplace actually ships, so a helpful agent files across the boundary and the prose never fires. Cost is real and asymmetric: the wrong tracker gets noise it must triage and delete, and the project that owns the bug never hears about it.

The second one is the same shape as the standing rule that a discovered silent failure becomes a machine-checkable check rather than a doc note — the marketplace manifest is already on disk next to the reporter, so the check has its data.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The feature-request path files successfully against this repo with no manual label argument, proven by a real filed issue or a --draft run asserted against the live label list
- [ ] #2 Default labels are derived from or validated against the target repo labels rather than hardcoded, so a label rename cannot silently break filing again
- [ ] #3 A report naming a plugin id the reporting marketplace does not ship is refused, or blocked pending an explicit override, rather than filed
- [ ] #4 A test fails if either default label stops existing in the target repo, and a test fails if an out-of-marketplace plugin id is accepted
- [ ] #5 The scope boundary is enforced by the check, not only by the prose note in the module docstring
<!-- AC:END -->
