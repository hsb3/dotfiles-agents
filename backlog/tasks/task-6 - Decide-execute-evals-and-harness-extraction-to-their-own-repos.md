---
id: TASK-6
title: Decide + execute evals/ and harness/ extraction to their own repos
status: Done
assignee: []
created_date: '2026-08-04 00:42'
updated_date: '2026-08-07 01:10'
labels:
  - governance
  - decision
milestone: m-3
dependencies: []
priority: low
type: task
ordinal: 1450
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
evals/ tracked data.db is 16MB of the repo's 29MB; consumers clone the marketplace repo under the new model. Owner already intends harness extraction. Decide scope (one or both, when), then execute the move with pointers back. Removes 3 workbench nodes from this repo's DAG.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ruling recorded
- [ ] #2 Extracted repos own their history; this repo keeps consume-pointers only
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Owner ruling 2026-08-04 (decision-5): extract BOTH eventually (harness first, then evals) — but DEFERRED. 'Not yet; dev is my workbench; we'll move after things mature.' Parked at Low; no scheduling this cycle.

Owner ruling 2026-08-07, verbatim: 'remove plan to move them. if i decide to move, i'll bring it up.'

This withdraws the 2026-08-04 ruling (decision-5) that both evals/ and harness/ would eventually be extracted, harness first. That plan had been deferred with no schedule since, and a deferred-forever card reads as available work every time the backlog is reviewed, which is the cost being removed here.

evals/ and harness/ stay in this repo. No extraction is planned. If the owner wants to revisit, the owner raises it — no card is needed to hold the option open, and the harness's existing no-repo-coupling gate (make harness-coupling, DESIGN section 5) already keeps extraction cheap if it is ever wanted.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed by owner ruling: the extraction plan is withdrawn, not merely deferred. evals/ and harness/ remain in this repo and no move is planned. AC#1 (ruling recorded) is satisfied by this decision. AC#2 (extracted repos own their history; this repo keeps consume-pointers) is moot and will not be executed — dropped rather than left as a permanently unreachable criterion. The owner will raise extraction directly if that ever changes.
<!-- SECTION:FINAL_SUMMARY:END -->
