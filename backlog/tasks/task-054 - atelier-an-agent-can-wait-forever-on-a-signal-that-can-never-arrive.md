---
id: TASK-054
title: 'atelier: an agent can wait forever on a signal that can never arrive'
status: To Do
assignee: []
created_date: '2026-08-10 02:45'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/280'
  - 'https://github.com/hsb3/dotfiles-agents/issues/284'
  - 'https://github.com/hsb3/dotfiles-agents/issues/285'
  - 'https://github.com/hsb3/dotfiles-agents/issues/287'
priority: high
type: feature
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Four field reports from other projects, all the same failure: an agent blocks on something that cannot happen, and nothing in the doctrine or the tool grants makes that impossible or even detectable. Fixing any one alone leaves the deadlock reachable by the other three, so they are one card.

- No reply channel (#280). Only `manager` is granted `SendMessage` — `plugins/atelier/agents/manager.md:5` versus `builder.md:5`, `reviewer.md:5`, `scout.md:5`. A manager that messages a live builder or reviewer is waiting on a reply the callee has no tool to send. Two managers deadlocked this way in one session.
- Unbounded self-adopted waits (#284). The brief rules bound constraints handed TO a worker but say nothing about a stop condition an agent adopts for ITSELF. Three agents in one session blocked on conditions that could never be met.
- No liveness check (#285). Nothing tells a manager or the strategist how to distinguish a dead worker or gate from a slow one, so the only available move is to keep waiting.
- Manager writes over its own live builder (#287). The ownership map covers strategist-to-worker but not manager-to-its-own-worker, and `manager.md:5` grants the same Edit/Write as `builder.md:5`. A manager fix was silently reverted when its builder finished and wrote the file it owned.

The reply-channel half is structural and cheap: either grant the callee the tool, or state as doctrine that a message to a live execution-layer agent is one-way and never waited on. The liveness and ownership halves are doctrine, and doctrine that is only prose has already failed here once — prefer a rule an agent can check over a rule an agent must remember.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manager that sends a message to a live builder, reviewer, or scout either gets a reply channel that works, or is told by the doctrine that no reply can come and is given the alternative
- [ ] #2 The brief rules bound waits an agent adopts for itself: every stop condition names what would satisfy it, who produces that, and what the agent does when it does not arrive
- [ ] #3 There is a named way to tell a dead in-flight worker or gate from a slow one, usable by both a manager and the strategist, and it is written where a waiting agent will actually look
- [ ] #4 File ownership is defined for manager-to-its-own-worker, not only strategist-to-worker, and says what a manager may edit while a worker it dispatched holds a file
- [ ] #5 Each of the four reported scenarios is walked against the revised doctrine and shown to terminate
<!-- AC:END -->
