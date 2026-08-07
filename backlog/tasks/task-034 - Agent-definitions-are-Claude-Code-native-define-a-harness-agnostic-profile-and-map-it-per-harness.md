---
id: TASK-034
title: >-
  Agent definitions are Claude-Code-native: define a harness-agnostic profile
  and map it per harness
status: To Do
assignee: []
created_date: '2026-08-06 19:30'
updated_date: '2026-08-07 01:53'
labels:
  - distribution
  - decision
milestone: m-1
dependencies: []
references:
  - primitives-core/agents/scout.md
  - primitives-core/agents/lead.md
  - scripts/gen_opencode.py
  - translation.yaml
  - primitives-core.yaml
  - tests/test_gen_opencode.py
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

`primitives-core/` is the one place a primitive is edited, but the four agent definitions there are authored in **Claude Code's native subagent frontmatter**. The canonical source is written in one harness's dialect, so every other harness is served by a lossy one-way transform bolted on at generation time rather than by a mapping from a neutral source.

Verified 2026-08-06 against `primitives-core/agents/{scout,builder,reviewer,lead}.md`.

**The frontmatter is vendor-shaped.** Representative (`scout.md:1-9`):

```yaml
name: scout
description: Read-only recon — ...
model: haiku
effort: low
maxTurns: 15
tools: Read, Grep, Glob
color: cyan
```

Only `name` and `description` are portable. `tools` is a flat list of Claude Code built-in tool names; `model` is a bare Claude alias with no provider path; `color`, `effort`, and `maxTurns` are Claude Code concepts. Key usage varies by agent (`effort` and `maxTurns` on scout only, `memory: project` on reviewer only), so there is no declared schema either — the format is whatever Claude Code happens to accept.

**The transform is lossy and silent.** `transform_agent` in `scripts/gen_opencode.py:115-136` hardcodes field names and:

- drops `color` (commented — opencode rejects the values),
- drops `effort` and `memory` with no comment at all; they are simply never referenced,
- **silently omits `model`** when an alias is unrecognized and contains no `/` (`:123`; `tests/test_gen_opencode.py:61` pins this with `model: mystery`),
- inverts `tools` into an opencode `permission:` map by membership in two hardcoded sets, `WRITE_TOOLS`/`BASH_TOOLS` (`:55-56`, applied `:130-134`). A tool in neither set — `Grep`, `Glob`, `Read`, `Agent`, `SendMessage` — gets no explicit bucket and is covered only by a blanket `read: allow`.

A field that has no representation on a target should be an explicit, declared "unsupported", not a silent drop. Today the mapping knowledge lives in Python set membership rather than in the capability matrix.

**The bodies leak too, narrowly.** `reviewer.md:31` names the literal tool "Bash"; `lead.md:45` names `SendMessage`, and its frontmatter requests `Agent, SendMessage` — which `gen_opencode.py:259-260` itself flags as having no opencode equivalent. Bodies are copied verbatim (`:136`), so this prose travels untouched to a harness where those tools do not exist. No agent body references `subagent_type`, slash commands, `.claude/` paths, hook events, or hardcoded model ids — so the problem is mostly frontmatter, with two narrow prose exceptions.

**The roster records no format information.** An agent entry carries `id, type, source, origin, disposition, targets` (`primitives-core.yaml:137-141`). `targets` names destination harnesses; nothing records the source format or a schema version, so nothing can detect a definition drifting away from whatever shape the generator expects.

**No prior art.** Searched `backlog/decisions/`, `backlog/docs/`, `AGENTS.md`, `CLAUDE.md`, `flow.yaml` for a harness-neutral or portable extender format: absent. `decision-2` and ADR 0017 cover distribution mechanics (pointer assemblies, generate-at-install-time), not the source format. `translation.yaml` is the closest thing — a capability matrix keyed by primitive type — but it is a remap layer over a Claude-Code-native source, which is the standing approach its own header describes.

## What is wanted

A harness-agnostic agent profile as the authored source, plus declared per-harness mappings that generate the concrete definitions at install time. The profile should describe **intent and capability**, not vendor nouns:

- capabilities (read, search, edit, execute, delegate) instead of a list of one harness's tool names;
- a tier intent (cheapest / standard / premium) instead of a bare model alias, with the alias resolution living in the per-harness mapping where `translation.yaml:34-40` already keeps `model_aliases`;
- budgets (turn caps, effort) as neutral fields that a mapping may declare unsupported;
- presentation-only fields (`color`) marked as such, so dropping them is a declared no-op rather than a silent one.

Claude Code is the reference harness (owner direction 2026-08-06: Claude Code first, other harnesses after it stabilizes), so **the neutral profile must round-trip to the current Claude Code definitions with no observable change** — that is the acceptance test that keeps this from being a rewrite for its own sake.

## Open questions to settle before building

1. **Where does the neutral profile live and in what form?** A new frontmatter schema in the same `.md` files, or a sidecar profile plus a body file? The second decouples format from prose but doubles the file count and changes what the symlink assemblies point at.
2. **What happens to body prose that names a specific harness's tools?** Options: accept the leak, keep per-target body fragments, or write bodies to a neutral vocabulary and let the mapping substitute. No option is obviously right; picking one is the point of the decision.
3. **Does the roster gain a format/schema-version field**, so drift from the declared profile shape is machine-detectable?
4. **Does this extend to hooks and skills**, or are agents the only primitive with a vendor-shaped source? Hooks are `treatment: unsupported` for opencode today, which may make them moot or may make them the next instance of the same problem.

## Constraints

- **This is an information-architecture change to `primitives-core/`, the repo's source of truth. It needs the owner's decision before any build** (AGENTS.md). Scope this task's first deliverable as the decision record, not code.
- Nothing generated is tracked; the per-harness definitions stay install-time artifacts, and any generator stays deterministic (stable ordering, no clocks or randomness).
- Agents ship through symlink assemblies — `plugins/foreman-kit/agents/{scout,builder,reviewer,lead}.md` are symlinks into `primitives-core/agents/`. A change to file shape or naming moves those four links and must keep `make symlinks` green.
- Sequenced behind Claude Code stabilization per the owner's direction. The decision can be taken earlier than the build.

## Blast radius (verified)

4 agent definitions + `primitives-core/agents/README.md` (carries a per-agent model/tier table) + 4 symlinks under `plugins/foreman-kit/agents/` + `translation.yaml` + `scripts/gen_opencode.py` + `scripts/check_identity.py` (parses agent frontmatter, `:168-182`, `:206-207`) + `scripts/check_roster.py` + `tests/test_gen_opencode.py` (pins the current transform, including the color-drop and model-alias behavior, `:39-61`, `:126-129`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A decision record defines the harness-agnostic agent profile: its fields, their value vocabularies, and what each field means independent of any harness
- [ ] #2 The four open questions (profile location/form, harness-specific body prose, roster schema-version field, whether hooks and skills are in scope) are each answered in the decision, not deferred silently
- [ ] #3 The owner has approved the profile before any file under primitives-core/ changes shape
- [ ] #4 Each supported harness has a declared mapping from the neutral profile to its native format, with every neutral field either mapped or explicitly declared unsupported for that harness
- [ ] #5 No field is dropped silently: generating for a target reports every field the target cannot represent
- [ ] #6 The Claude Code definitions generated from the neutral profiles are observably identical to today's four agent definitions (round-trip proof, not assertion)
- [ ] #7 An unrecognized model tier or capability fails loudly instead of being omitted, replacing the current silent-omission behavior in transform_agent
- [ ] #8 Tool-to-capability mapping lives in the declared matrix rather than hardcoded Python set membership
- [ ] #9 make ci green, make symlinks green, and the four plugins/foreman-kit/agents symlinks still resolve
<!-- AC:END -->

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
<!-- COMMENTS:END -->
