---
id: TASK-13
title: >-
  Investigate: do under-scoped foreman briefs drive delegated sessions past 250k
  tokens?
status: To Do
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-10 02:23'
labels:
  - evals
milestone: m-2
dependencies:
  - TASK-036
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/217'
priority: medium
type: spike
ordinal: 300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Migrated from GH #217. Investigation only: pull token data (subagent-telemetry ledger + campaign runner), report the distribution, record a verdict on the under-scoping hypothesis. No SKILL.md edit ships here; a confirmed hypothesis gets a separate follow-up proposal.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Distribution reported for delegated sessions
- [ ] #2 Verdict recorded; follow-up proposal filed only if hypothesis holds
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 00:51
---
Blocked in practice, though nothing formally declares it. This spike's whole data source is the delegation ledger (logs/delegation.jsonl), and TASK-036 establishes that the ledger currently records the PARENT session's model and context tokens rather than each subagent's, with a row count running ~10x the real delegation count.

Token-distribution analysis over that data would not measure what this card asks about. It would measure the parent session repeatedly, inflated tenfold. Any verdict drawn from it would be confidently wrong, which is worse than no verdict — and this card's deliverable is precisely a recorded verdict.

Sequence it after TASK-036, and re-check that enough post-fix delegations have accumulated before starting: the fix corrects rows written from then on, it does not repair history. The existing ledger contents are not retrospectively salvageable, since the subagent identity that should have been recorded was never captured.
---
<!-- COMMENTS:END -->
