---
id: TASK-034
title: >-
  Agent definitions are Claude-Code-native — map them to other harnesses via a
  declared capability matrix
status: To Do
assignee:
  - claude
created_date: '2026-08-06 19:30'
updated_date: '2026-08-10 02:27'
labels:
  - distribution
  - on-hold
milestone: m-1
dependencies: []
references:
  - primitives-core/agents/scout.md
  - primitives-core/agents/lead.md
  - scripts/gen_opencode.py
  - translation.yaml
  - primitives-core.yaml
  - tests/test_gen_opencode.py
  - >-
    backlog/decisions/decision-009 -
    Agent-profile-stays-Claude-Code-native-harness-neutrality-lives-in-a-declared-capability-matrix.md
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`primitives-core/agents/{scout,builder,reviewer,manager}.md` are the one editable source for the repo's four agent definitions, but they're written in Claude Code's native subagent frontmatter — bare model aliases, a flat `tools:` list, presentation fields like `color`, budget fields like `effort`/`maxTurns`. `scripts/gen_opencode.py` transforms this for opencode ad hoc: it drops `color` and `effort` silently, omits `model` with no warning when an alias it doesn't recognize lacks a `/`, and buckets tools into an opencode permission map via two hardcoded Python sets (`WRITE_TOOLS`/`BASH_TOOLS`) instead of a declared mapping. A field with no representation on a target harness should be an explicit "unsupported," not a silent drop.

decision-009 (owner-accepted 2026-08-07) settles the shape: no new neutral profile file — Claude Code's existing frontmatter stays the unbuilt source of truth. Harness-neutrality is instead a declared capability matrix extending `translation.yaml` (`tool_capabilities` + `field_treatments`), replacing `gen_opencode.py`'s hardcoded tool sets and silent drops. `manager.md`'s `Agent`/`SendMessage` body prose is accepted as-is and joins `translation.yaml`'s existing exclusions pattern rather than being neutralized. No new roster schema-version field — bump `translation.yaml`'s existing `version` instead, backed by a completeness gate. Hooks and skills stay out of scope.

What's left is the build: the capability matrix itself, the generator rewrite, and the completeness gate. It stays sequenced behind Claude Code stabilization per the owner's direction — parked, not scheduled. Nothing generated is tracked; per-harness definitions stay install-time artifacts, and the generator stays deterministic (stable ordering, no clocks or randomness).

Also touches: `primitives-core/agents/README.md` (per-agent model/tier table), the four `plugins/foreman-kit/agents` symlinks, and `scripts/check_identity.py` + `scripts/check_roster.py` (both parse agent frontmatter).

AC1-3 (the decision) are done. AC4-9 (the build) are deferred and on-hold — not blocked on any open decision, just parked behind Claude Code stabilization.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A decision record defines the harness-agnostic agent profile — its fields, value vocabularies, and per-field meaning independent of harness
- [x] #2 The decision answers all four open questions — profile location/form, harness-specific body prose, a roster schema-version field, and whether hooks/skills are in scope — none deferred silently
- [x] #3 The owner approved the profile before any file under primitives-core/ changes shape
- [ ] #4 Each supported harness has a declared mapping from the neutral profile to its native format; every field is either mapped or explicitly declared unsupported for that harness
- [ ] #5 No field is dropped silently — generation for a target reports every field it cannot represent
- [ ] #6 Claude Code definitions generated from the neutral profiles are observably identical to today's four agent definitions — round-trip proof, not assertion
- [ ] #7 An unrecognized model tier or capability fails loudly instead of being silently omitted, replacing transform_agent's current silent-omission behavior
- [ ] #8 Tool-to-capability mapping lives in the declared matrix, not hardcoded Python set membership
- [ ] #9 make ci and make symlinks pass green; all four plugins/foreman-kit/agents symlinks still resolve
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Draft decision-009 answering the four open questions (done, status: proposed).\n2. Present to owner for approval/ruling.\n3. On approval: check AC #1-3, flip decision-009 to accepted, leave AC #4-9 (the generator/matrix build) as deferred follow-on work per the task's existing Claude-Code-stabilization sequencing — does not block closing the decision-record deliverable.\n4. On rejection/amendment: revise decision-009 per owner feedback, re-present.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:09
---
Owner ruling 2026-08-07: TAKE THE DECISION NOW, BUILD LATER. Owner's note: 'there are good examples of how to handle this. we can do the build later tho.'

So this card's first deliverable is confirmed as the decision record, not code — which is what the card already proposed. The build stays sequenced behind Claude Code stabilization per the owner's earlier direction; the decision does not have to wait for it and unblocks planning now.

Whoever drafts the decision should look for prior art rather than inventing a profile from scratch — the owner states good examples exist for the harness-neutral-profile-plus-per-harness-mapping shape. The four open questions in the card (profile location and form, body-prose handling, a roster schema-version field, and whether hooks and skills are in scope) are what the decision record must answer.
---

author: @claude
created: 2026-08-07 01:15
---
Body is now stale in one detail. The card's frontmatter-key inventory states 'memory: project on reviewer only' — as of 2026-08-07 no agent in primitives-core/agents/ carries a memory: key at all. It was removed from reviewer.md under TASK-037, because the Claude Code runtime resolves memory: project to <cwd>/.claude/agent-memory/<agentType>/ and creates that directory at dispatch, which is what was writing into target repos.

Relevant to this card beyond the correction: memory: is a real example of the problem this card exists to solve. It is a Claude-Code-native frontmatter key with runtime semantics (enum user|project|local, optional, no 'off' value) and no obvious counterpart in another harness. Any harness-agnostic agent profile has to decide whether such a key is part of the neutral profile or a per-harness mapping — and this one carries a filesystem side effect, so dropping it silently in translation is not neutral.
---

author: @claude
created: 2026-08-07 01:53
---
Path reference is now stale: this card lists primitives-core/agents/lead.md in its blast radius. That file no longer exists — it was renamed to primitives-core/agents/manager.md on 2026-08-07 under TASK-045, which defined the strategy/management/execution layers explicitly and retired the 'foreman' term.

Two things about that rename bear directly on this card rather than merely correcting a path.

First, the roster's four agents are now scout, builder, reviewer, manager, and each body states which layer it is on. A harness-neutral agent profile now has a layer field to carry, not just a role name.

Second, and the reason the owner chose the name: the strategy layer is now called 'strategist'. The owner's stated rationale was forward-looking and aimed squarely at this card — other harnesses let the primary agent be set as a named profile, so naming it now gets ahead of that and avoids churn when the collection expands beyond Claude Code. This card's neutral profile should adopt 'strategist' as the primary rather than inventing a name at build time.

Also relevant to this card's central problem: 'memory:' is gone from every agent (TASK-037), so the frontmatter-key inventory here is stale in that respect too.
---

created: 2026-08-07 13:05
---
Pulled forward 2026-08-07 per owner direction in the session that surfaced a related question (whether atelier's strategy-layer 'strategist' persona had an agent profile file). Answer to that question: no, and none should exist in primitives-core/agents/ — strategist is session-only per TASK-045's explicit ruling, never a spawned Claude Code subagent. This card is the deferred forward-looking piece: a harness-agnostic profile so other harnesses that DO support naming a primary agent can adopt 'strategist' without inventing a shape later. Owner chose to build the decision record now rather than continue deferring. Per the card's own scope note and AGENTS.md, build (ACs #4-9) stays gated on owner approval of the decision (ACs #1-3) — drafting that now, will present before touching any file under primitives-core/.
---

created: 2026-08-07 13:11
---
Decision drafted: backlog/decisions/decision-009 (status: proposed). Recommendation: no new neutral source file — CC's existing agent frontmatter stays the unbuilt source of truth (holds decision-2's no-build-step-for-CC invariant), harness-neutrality is realized as a declared capability matrix extending translation.yaml (tool_capabilities + field_treatments, replacing gen_opencode.py's hardcoded WRITE_TOOLS/BASH_TOOLS sets and silent drops), manager.md's Agent/SendMessage body prose is accepted and the agent joins translation.yaml's existing exclusions: pattern rather than being neutralized, no new roster schema-version field (bump translation.yaml's existing version: instead, backed by a completeness gate), hooks/skills stay out of scope. Full reasoning in the decision file. Presenting to owner now; AC #1-3 stay unchecked pending their ruling.
---

created: 2026-08-07 13:16
---
Owner accepted decision-009 as drafted 2026-08-07 (no walkthrough or amendments requested). Flipped decision-009 to status: accepted; AC #1-3 checked. AC #4-9 (translation.yaml tool_capabilities/field_treatments sections, generator rewrite, completeness gate) remain the deferred build, still sequenced behind Claude Code stabilization per the task's original constraint — not started now. Swapping the 'decision' signal label for 'on-hold' since the ruling this card was blocked on is resolved and what remains is deliberately parked, not blocked on a pending decision. Status back to To Do (unassigning is implicit — no one is actively driving the remaining build); pick it back up when Claude Code stabilization clears the precondition.
---
<!-- COMMENTS:END -->
