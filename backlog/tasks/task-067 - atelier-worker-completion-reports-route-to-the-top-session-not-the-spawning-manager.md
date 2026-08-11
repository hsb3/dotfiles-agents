---
id: TASK-067
title: >-
  atelier: worker completion reports route to the top session, not the spawning
  manager
status: To Do
assignee: []
created_date: '2026-08-11 18:19'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/299'
  - 'https://github.com/hsb3/dotfiles-agents/issues/306'
priority: high
type: bug
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two field reports from learn-pocketbase, one defect, both silent and deadlock-shaped: a worker finishes but its completion notification is delivered to the TOP-LEVEL session's queue instead of the manager that dispatched it. The manager idles forever on a report that already fired one level up; the top session (correctly refusing to act on a subordinate's report) waits on the manager. Chain of command inverts and nothing errors.

Two observed shapes:
- #299 (2026-08-10): manager resumed a finished worker via SendMessage for the next chain link. The resume ran in the background with its output path under the TOP session's tasks dir; on completion the task-notification enqueued to the top session. Manager transcript shows zero entries after the SendMessage call.
- #306 (2026-08-11): backgrounded manager spawned a fresh builder; same misroute, even though the manager's brief explicitly instructed synchronous dispatch (run_in_background: false). Worker's own report ended 'I have no SendMessage tool in this session, so this report is my reply to atelier:manager' — and never reached it.

Distinct from TASK-054 (an agent can wait forever on a signal that can never arrive): that card's four scenarios are reply channels, self-adopted waits, liveness, and ownership — none cover notification routing. This card is the specific harness behavior that CREATES such a wait. If the routing is harness behavior the plugin cannot change, the fix is design: managers stop relying on notification delivery (poll the worker's report file, hard-require truly synchronous dispatch, or make the top-session relay a documented pattern instead of an ad-hoc rescue — the field workaround in both reports).

Settle the harness-vs-plugin question with the headless probe recipe in .claude/HANDOFF.md §5 before designing around a guess (see gotcha: 'Do not infer harness behavior' — probe it).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 It is established by probe, not inference, whether background-agent completion notifications can reach a spawning manager at all; the probe evidence is recorded on this card
- [ ] #2 A manager that dispatches or resumes a worker receives that worker's completion by a route proven to work — or the doctrine forbids the dispatch pattern and names the working alternative
- [ ] #3 Both reported shapes (SendMessage-resume #299, fresh spawn under a backgrounded manager #306) are walked against the fix and shown to terminate
- [ ] #4 The top session's role on receiving a subordinate's report is either made unnecessary or documented as the relay pattern the field already uses
<!-- AC:END -->
