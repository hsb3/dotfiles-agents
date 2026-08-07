---
id: TASK-035
title: >-
  Cold-readability audit: every open card verifiable by someone who didn't write
  it
status: To Do
assignee: []
created_date: '2026-08-06 21:33'
updated_date: '2026-08-07 01:25'
labels:
  - governance
dependencies: []
priority: medium
type: chore
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Carried over from milestone m-0, whose final unchecked commitment was: 'Every open card is cold-readable with verifiable acceptance criteria, assessed by someone who didn't write it.' m-0 closed on task completion without this being done, so it is tracked here rather than dropped.

A card is cold-readable when a session with no prior context can pick it up and know what done looks like. The independence requirement is the point: the assessor must not be whoever wrote the card, because the author cannot see their own missing context.

Scope is the open cards across m-1, m-2, and m-3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every open card has acceptance criteria that state a checkable outcome, not an activity
- [ ] #2 Each card names the files, commands, or decisions a cold session needs to start
- [x] #3 The assessment is done by an agent or session that did not author the card, and its findings are recorded per card
- [ ] #4 Cards that fail the audit are either rewritten or explicitly dropped
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
A full cold-read pass over all 31 open cards ran 2026-08-07, satisfying AC#3's process constraint: four independent assessors, none of whom authored any card, each read a disjoint batch in full and reported per-card whether the acceptance criteria were independently verifiable, quoting the weakest AC verbatim.

Cards with genuinely strong, machine-checkable criteria: TASK-27 (strongest of all — both ACs are already phrased as commands: 'git diff --stat harness/results.jsonl empty after an evidence run'), TASK-036, TASK-040, TASK-18, TASK-19.

Defects found, by kind:

NO CRITERIA AT ALL — TASK-25 had no acceptance-criteria section whatsoever and named no files, while describing itself as 'a backlog-aware mode OR a scoped successor skill'. Unstartable. FIXED: seven criteria drafted, with the first one forcing the mode-versus-successor question to be answered rather than carried forward.

THE EITHER/OR ANTI-PATTERN — TASK-037 and TASK-038 both phrased their primary criterion as 'Either X... or Y...', which structurally defers the actual decision INTO the criterion instead of resolving it in the card. Neither is verifiable until someone rules. This is a recurring authoring habit worth naming, not two isolated slips. BOTH RESOLVED by owner ruling 2026-08-07 and now implemented.

A DECISION SMUGGLED INTO A MECHANICAL CHECK — TASK-29 AC#2 ('Bundle home is decided and wired... make ci is green') and TASK-15 AC#1 ('Override mechanism ruled and implemented') each bundle a human ruling and its implementation into one checkbox, so the box cannot be checked until a decision that is not the implementer's to make has happened. Both rulings have since been given.

UNDEFINED SUCCESS WORDS — TASK-12 AC#2 rests on 'reproduces a defensible config' with no pass signal; TASK-21.4 AC#1 says the render loop 'works' with no test named; TASK-11 AC#1 ends 'or explicit disposition', satisfiable by writing one sentence.

UNVERIFIABLE WITHOUT LEAVING THE REPO — TASK-20 AC#1 referenced 'the motivating transcript pattern' with no link or excerpt in the card; a cold reader cannot check it. Worked around by verifying against the existing harness case instead, and the substitution recorded on the card rather than left silent. TASK-17's two unnamed ideas ('schema', 'vars') required reading an external issue.

A CLAIM THE CARD CANNOT PROVE — TASK-21.1 AC#3 ('superseded rows marked superseded, never overwritten') asserts a historical guarantee about rows the card never touches.

STALE PREMISE — TASK-14 targeted a plugin name that no longer exists. FIXED: re-scoped, with fresh evidence added from this session (a concurrent session moved dev's tip underneath a running session with no warning to either side).

Also filed during the pass: TASK-041, TASK-042, TASK-043, TASK-044, each written to be cold-readable from the outset.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:25
---
AC#1 and AC#2 are deliberately left unchecked. The audit is complete and every failing card is now identified with its specific defect, but those two criteria require each failing card to be rewritten or dropped, and several fixes are still open work rather than done: TASK-12's undefined 'defensible', TASK-21.4's undefined 'works', TASK-11's sentence-satisfiable disposition clause, and TASK-21.1's unprovable historical guarantee all still need their criteria rewritten by whoever picks the card up. Checking them now would claim coverage the repo does not have.
---
<!-- COMMENTS:END -->
