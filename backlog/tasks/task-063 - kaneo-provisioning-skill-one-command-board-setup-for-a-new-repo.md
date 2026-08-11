---
id: TASK-063
title: kaneo provisioning skill - one-command board setup for a new repo
status: To Do
assignee: []
created_date: '2026-08-11 08:21'
labels:
  - primitives
milestone: m-2
dependencies:
  - TASK-061
priority: medium
type: feature
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Standing up a new repo on a Kaneo board is ~8 manual steps today, and the kaneo-ops README says so in its own 'what it is not yet' section. The steps span two repos and three credential surfaces: mint a durable agent account, mint a 30-day MCP bearer token from that agent key, clone or create the project board, capture the project id, write the five KANEO_* values into the consuming repo's .claude/settings.local.json, and verify the wiring with whoami. Every step is a place to wire the wrong key - and wiring the OWNER key instead of an agent key silently hands the repo owner rights over every workspace, with every claim comment misattributed.

This card is the provisioning half of the pair (see the brownfield adoption card for migrating work that already exists). Scope is a repo with no board yet.

Design constraints that already exist and must be honoured: the minting scripts live in kaneo-ops (mint-agent.sh, mint-mcp-token.sh, kaneo_template.py) and are instance ops, not plugin material - the skill drives them, it does not absorb them. The MCP token expires after 30 days with no refresh, and an edited token does nothing until the session restarts because headers expand at session start; whatever this ships must state that, because it is the most likely thing to look like a broken install later.

Verification is not optional here: the whoami tool returns the user the key belongs to, so the skill can prove it wired an agent identity and not the owner. That check is the difference between provisioning and hoping.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The skill takes a repo with no board from zero to a verified working setup, and the verification step proves the wired identity is an agent account and not the owner account
- [ ] #2 It drives the kaneo-ops minting scripts rather than reimplementing them, and says plainly what it needs from that repo
- [ ] #3 The 30-day token expiry, the absence of refresh, and the session-restart requirement are stated where someone hitting a 401 will find them
- [ ] #4 No live instance host, project id, or agent identifier is baked into the skill - every instance value is a placeholder or a KANEO_* env reference
- [ ] #5 It ships with the kaneo plugin assembly and carries a per-primitive README per primitives-core/README.md
- [ ] #6 make ci exits 0 including the identity lint and the solo-skills membership gate
<!-- AC:END -->
