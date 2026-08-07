---
id: TASK-045
title: >-
  atelier: define the strategy/management/execution tiers explicitly and retire
  the foreman term
status: To Do
assignee: []
created_date: '2026-08-07 01:38'
updated_date: '2026-08-07 01:45'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: high
type: feature
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Owner direction 2026-08-07, verbatim: 'in atelier, we need to look at revising the language and potentially retiring the foreman term. the strategy/management/execution tiers are never explicitly defined. this makes things ambiguous. for anything except trivial tasks, there is good reason for having all three layers. because the job and context are very different it allows for specialization and actually is more efficient than using less levels with larger prompts.'

Two changes in one, and the second is the bigger one.

FIRST, TERMINOLOGY. 'foreman' currently names a skill, a role the session plays, and implicitly a tier. A foreman is also a two-tier metaphor by construction — one supervisor over workers — which is the wrong shape for a three-layer model, and it sits oddly beside the plugin's own atelier framing.

SECOND, DOCTRINE. The skill today presents five architectures (direct, scouts, flat fan-out, lead-driven team, phased crews) and treats the middle layer as ONE OPTION among them rather than as a standing layer. Its tiebreak explicitly tells a session to avoid that layer: 'When genuinely torn, prefer the cheaper architecture.' The owner's position inverts this — the middle layer is not overhead to be avoided, it is specialization that pays for itself, because each layer's job and context differ enough that three focused prompts beat two larger ones.

WHAT MAKES THIS CHEAP TO CHANGE: the prefer-fewer-layers tiebreak carries the skill's own '[untested]' provenance tag, meaning it was never measured. The doctrine being overturned is self-labelled as unmeasured reasoning, not as a finding. Any measured '[lab]' or '[cost]' result must survive the rewrite untouched.

Scope note: this is an information-architecture change to primitives-core, the repo's source of truth, so AGENTS.md requires the owner's approval on the specific shape before it is built. The naming decision and the tier definitions go to the owner as an approval gate, not as a done deal.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The three tiers are each named and defined as layers, stating for each: what work is irreducibly its own, what context it needs, and what it must never do
- [ ] #2 Each shipped agent definition is mapped to exactly one tier, and the tier is stated in the agent's own body so a dispatched agent knows which layer it is on
- [ ] #3 The default for non-trivial work is all three layers; collapsing a layer is the exception and the card states when collapsing is correct
- [ ] #4 The prefer-fewer-layers tiebreak is removed or inverted, and its replacement carries an honest provenance tag rather than being asserted as measured
- [ ] #5 Every measured [lab] and [cost] finding in the current skill survives the rewrite, verifiable by diffing the provenance map before and after
- [ ] #6 The naming decision (whether the skill is renamed, and to what) is ruled by the owner before any rename is executed
- [ ] #7 If renamed: no shipped body, roster row, symlink, catalog row, or manifest still refers to the retired name, while backlog and decision history keep theirs untouched
- [ ] #8 make ci is green and the version is bumped in both manifests
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:45
---
Owner rulings 2026-08-07, all four settled. Build may proceed.

1. SKILL NAME: foreman -> 'delegation'. Plainest accurate name for the job, and the plugin already ships a delegation-watermark hook, so the vocabulary is half-established.

2. VOCABULARY: the org structure is LAYERS, not tiers. 'Tier' stays reserved for MODEL selection (haiku/sonnet/opus), which is its existing meaning throughout the skill and the whole subject of references/tier-cutoff.md. Using one word for both in a document whose stated problem is ambiguity would have been self-defeating.

3. STRATEGY LAYER ROLE: 'strategist' — a real role noun, not just 'the session'. Owner's rationale, which is forward-looking rather than cosmetic: other harnesses let you set the primary agent as a NAMED PROFILE, so naming it now gets ahead of that and avoids churn when the collection expands to opencode plugins. This ties directly to TASK-034 (harness-agnostic agent profile): that card's neutral profile can adopt 'strategist' as the primary rather than inventing a name later.

4. MANAGEMENT AGENT: lead -> 'manager'. Maps one-to-one onto the management layer and removes a real collision the audit found — SKILL.md:42 says 'the session's lead seat' one line before the cheat-sheet lists 'lead' as a spawnable agent, and a reader cannot tell which is meant.

So the layer map is: STRATEGY = strategist (the session, never a spawned agent) / MANAGEMENT = manager (was lead) / EXECUTION = scout, builder, reviewer.

EVIDENCE STANDING, recorded honestly because the provenance system is the thing that makes this skill trustworthy. The owner states: 'i have some empirical evidence but we can prove later in harness/eval runs.' That is real but not a controlled measurement, and none of the three existing tags fits it — [lab] and [cost] would overstate it, [untested] ('reasoning that has never been measured') would understate it and invite a future session to discard it as a guess. Introduce a fourth tag, [field]: observed in practice by the owner, not yet reproduced under measurement. The three-layer default carries [field] until a harness run promotes it. Formal proof filed as its own card.
---
<!-- COMMENTS:END -->
