---
id: decision-012
title: starting-conditions ships in code-desk and rig-builder stays a distinct agent
date: '2026-08-22'
status: accepted
---
## Context

Promoting the `starting-conditions` skill and the `rig-builder` agent forced two calls a later
session could reasonably re-litigate, so they were put to the owner rather than left implicit in
a diff. Ruled on kata card `y8pd`; filed here 2026-09-07, having lived only in that card's
comment thread until then.

**Call 1 — which plugin carries the skill.** `solo-skills` is derived, not curated:
`scripts/check_solo_skills.py` claims every standalone-capable skill and rejects any that names
a roster agent in backticked prose. `starting-conditions` SKILL.md step 4 dispatches
`rig-builder`, so the gate classifies it non-standalone and `solo-skills` is closed to it **by
derivation, not by preference**. That left `atelier` (delegation agents and session discipline)
or `code-desk` (repo standards, audit, scaffold, planning, comms).

**Call 2 — whether `rig-builder` needs to exist.** `primitives-core/agents/builder.md` already
covers most of it: execution layer, owned file list, config read-only, never weaken a test or
lower a threshold to make a criterion pass, escalate an unsatisfiable gate rather than loosen
it, test-first with the observed-red failure reported. The lazy answer was to delete
`rig-builder` and express the difference as brief text.

## Decision

Owner ruling, 2026-08-22 (owner-signoff form, item A — "Approve both", no notes, no
amendments). The card's earlier "Approvals: pending" text is superseded by it.

1. **`code-desk` carries `starting-conditions`.** The skill's subject is a repo's own quality
   contract — the same desk as auditing a repo against a structure standard and scaffolding the
   gaps. `atelier` is about how a session splits work across agents; a gate is an input to that,
   not a member of it. `code-desk` becomes the first non-`atelier` bundle to carry an agent.

2. **`rig-builder` stays a distinct agent.** Three deltas from `builder.md`, one of them an
   inversion rather than an addition:

   - **Never remediate the artifact.** `builder`'s mandate is to implement until the acceptance
     criteria pass. `rig-builder`'s job is to MEASURE a baseline and leave it failing, because a
     baseline taken after remediation is worthless. A brief asking a builder not to make things
     pass fights the system prompt it is layered over, and the failure mode is silent: a helpful
     builder fixes violations and reports a clean baseline that never existed.
   - **Per-step red-proof protocol.** One deliberate sabotage per gate step, confirm the expected
     step catches it with file and line, revert, re-verify. `builder`'s test-first rule proves
     one test red; this proves every gate step red.
   - **Proof-package report shape.** Verbatim per-step output, a sabotage-to-message table, and a
     rule-by-rule baseline table ready to paste into the contract.

   The first delta settles it. The other two are brief-expressible; an inverted mandate is not.

## Consequences

- `code-desk` grows an `agents/` directory, so `scripts/check_catalog.py`'s derived `Contents`
  cell for that row gains an agent count. It stays a `bundle` either way.
- `starting-conditions` is permanently outside `solo-skills` as long as its SKILL.md names
  `rig-builder` in backticks. If the agent is ever collapsed into a brief, the skill becomes
  standalone-capable and `check_solo_skills.py` will DEMAND it be added to that assembly. That is
  the gate, not a choice.
- Two agents now sit near each other with overlapping-but-inverted mandates, so
  `primitives-core/agents/README.md` has to state the split or a dispatcher reaches for the wrong
  one. Done: `rig-builder` is listed under bundle-specific agents, carries its own model/tier
  row, is homed to `code-desk` explicitly, and the file spells out "Never swap `builder` for
  `rig-builder`" with the reason.
- **Revisit trigger, still open.** If a second "measure but do not fix" role appears, reopen this
  and consider one `auditor` role parameterized by brief instead of a family of near-copies. No
  such second role existed when this was filed.

Implementation status, checked 2026-09-06 on `y8pd`: both
`plugins/code-desk/skills/starting-conditions` and `plugins/code-desk/agents/rig-builder.md`
exist, and `primitives-core/agents/README.md` states the split. The ruling is executed; only
this record was missing.
