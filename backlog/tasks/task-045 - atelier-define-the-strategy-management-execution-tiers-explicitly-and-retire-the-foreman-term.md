---
id: TASK-045
title: >-
  atelier: define the strategy/management/execution tiers explicitly and retire
  the foreman term
status: Done
assignee: []
created_date: '2026-08-07 01:38'
updated_date: '2026-08-07 02:07'
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
- [x] #1 The three tiers are each named and defined as layers, stating for each: what work is irreducibly its own, what context it needs, and what it must never do
- [x] #2 Each shipped agent definition is mapped to exactly one tier, and the tier is stated in the agent's own body so a dispatched agent knows which layer it is on
- [x] #3 The default for non-trivial work is all three layers; collapsing a layer is the exception and the card states when collapsing is correct
- [x] #4 The prefer-fewer-layers tiebreak is removed or inverted, and its replacement carries an honest provenance tag rather than being asserted as measured
- [x] #5 Every measured [lab] and [cost] finding in the current skill survives the rewrite, verifiable by diffing the provenance map before and after
- [x] #6 The naming decision (whether the skill is renamed, and to what) is ruled by the owner before any rename is executed
- [x] #7 If renamed: no shipped body, roster row, symlink, catalog row, or manifest still refers to the retired name, while backlog and decision history keep theirs untouched
- [x] #8 make ci is green and the version is bumped in both manifests
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped in PR #270. The three layers are now defined by a discriminator table whose columns are the things that actually differ — may amend the contract, may spawn agents, does the user read its output, and context lifetime. Spawn authority is structural rather than merely stated: manager carries Agent and SendMessage, the execution agents do not, and the builder verified that before asserting it.

STRATEGY (strategist): the never-delegated floor folded in whole, plus a new statement of why it is irreducible — 'every item requires holding the user's actual intent next to the result. A layer below can satisfy a contract. It cannot notice that the contract was the wrong one.' Its forbidden context is the sharp part: no file contents, log dumps, tool transcripts, or per-worker back-and-forth, because 'this is the one context that never resets, so anything read here is paid for on every later turn, while the same bytes read one layer down are paid for once and thrown away.'

MANAGEMENT (manager): argued irreducible in BOTH directions, which is what makes it a layer rather than a convenience. It cannot move up because its traffic is high-volume and short-lived while strategy's context never resets; it cannot move down because a worker is deliberately blind to its siblings, so no worker can sequence a chain or notice two workers solving one sub-problem differently.

EXECUTION (scout/builder/reviewer): owns contact with the material AND independence — 'the differential and the panel are worth something only because these agents cannot see each other.'

A 'which layer am I on' resolver settles it in three questions, with the tiebreaker: 'If you were handed a written brief you did not write, you are not the strategist.'

COLLAPSE CONDITIONS are concrete and pre-dispatch checkable rather than a vibe: work-list final; slices independent IN OUTCOME rather than merely in file ownership; you can name what each worker hands back and it is a note rather than an artifact; reconciliation is mechanical. One failing puts a manager on the job. Never collapse strategy.

EVIDENCE HANDLING, which was the real risk. The promoted [cost] finding sits in a new 'Why three layers pay' section as the first pillar, wording intact, with the honest caveat added that at standard effort a manager is the SAME model tier as the session — so the layer buys context absorption, not tier arbitrage. Survival was checked mechanically, not by eye: each measurement cell was fingerprinted from the pre-rename provenance file via git show and matched against the new one — 10/10 [lab] rows and 6/6 [cost] rows present, zero missing. Two findings that were asserted in the skill but had NO provenance row (the evidence ranking and the streak figures) gained one.

The builder declined to over-claim in two places worth recording. It tagged the four collapse conditions [untested] rather than [field], because the owner's observation is the DEFAULT while the conditions operationalizing it are the builder's own reasoning — upgrading them would have been the exact silent promotion the provenance system exists to prevent. And it added a section, 'What the layer model replaced, and on what evidence', closing: 'Nothing measured was overturned. The replaced tiebreak was self-labelled unmeasured reasoning, and the replacement is an uncontrolled field observation. A [field] default beating an [untested] guess is the honest reading of the evidence and is not a result.'

Also caught late, outside every worker's scope: delegation-watermark and subagent-telemetry still shipped the retired vocabulary, including the nudge text a user READS ('executing rather than foremanning'). Fixed in the same PR.

Versions: atelier 0.9.0 -> 0.10.0; code-desk 0.4.1 -> 0.4.2, the latter caught by the new version-bump gate on its first live PR because planning-desk is dual-homed into code-desk.
<!-- SECTION:NOTES:END -->

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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
atelier's delegation doctrine now names and defines the three layers it always used implicitly. Skill foreman -> delegation, agent lead -> manager, the strategy layer gets the role noun strategist, and the org structure is called layers so that 'tier' keeps its existing meaning of model tier. Three layers is the default for non-trivial work and collapsing one now requires meeting four stated conditions, inverting guidance that had called the middle layer avoidable cost. The inverted rule carried [untested] and the provenance map recorded it had never been A/B'd, while a MEASURED [cost] finding supporting the layer model was buried inside one architecture's writeup and is now a pillar. A fourth provenance tag, [field], carries the owner's uncontrolled field evidence honestly rather than dressing it as measurement; TASK-046 files the harness run to settle it. No measured finding was lost, verified by fingerprinting every measurement cell against the pre-rename file.
<!-- SECTION:FINAL_SUMMARY:END -->
