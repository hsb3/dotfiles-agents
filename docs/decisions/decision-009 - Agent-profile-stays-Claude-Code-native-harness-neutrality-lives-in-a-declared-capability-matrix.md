---
id: decision-009
title: >-
  Agent profile stays Claude-Code-native; harness-neutrality lives in a declared
  capability matrix
date: '2026-08-07 13:10'
status: accepted
---
## Context

TASK-034 found that the four agent definitions under `primitives-core/agents/` are authored
in Claude Code's native subagent frontmatter (`tools:` as a flat CC tool-name list, `model:`
as a bare CC alias, plus CC-only concepts `color`/`effort`/`maxTurns`), and the opencode
transform (`scripts/gen_opencode.py:115-136`) is a lossy, hardcoded remap: it drops `effort`
with no comment at all, silently omits `model` when an alias is unrecognized, and buckets
`tools` into opencode's permission map via two hardcoded Python sets (`WRITE_TOOLS`/
`BASH_TOOLS`) — so a tool in neither set, including `manager`'s `Agent` and `SendMessage`
(its actual delegate capability), falls through to an implicit `read: allow` with no signal
that spawn capability didn't translate. None of this mapping knowledge lives in
`translation.yaml`, the repo's own declared capability matrix; it lives in Python set
membership instead.

Verified against the live files (2026-08-07): all four agents' frontmatter matches the
task's original inventory, and `memory:` is confirmed gone from all four (TASK-037 holds).
`manager.md` is the one agent whose body also leaks CC-only vocabulary (its `Agent`/
`SendMessage` spawn-and-continuation mechanics); the task's original citation of
`reviewer.md:31` naming "Bash" is stale at current line numbers, so the prose leak is
narrower than first scoped — one agent, not two.

Prior art surveyed (Google's A2A Agent Card, MCP's own tool/resource manifest schema,
Continue.dev's multi-provider `config.yaml`) converges on one shape: declare capabilities in
a fixed neutral vocabulary (booleans/enums, not vendor tool names), and make unsupported
fields an explicit, schema-checked declaration rather than a silent drop. None of the three
is a precedent for this repo's actual mechanism — install-time codegen driven by one
declarative matrix (`translation.yaml`'s own treatment enum: native/transform/render/
unsupported) — that pattern is closer to a build-tool concern than an agent-protocol
concern, and no clean external analog surfaced in the search.

`decision-2` already ruled Claude Code gets **no build step**: plugins are thin symlink
assemblies over `primitives-core/`, multi-homing is "one more symlink," and its own stated
tripwire for revisiting that is an external consumer or an outgrown translation layer — not
a differently-shaped source file. A design that requires *generating* the Claude Code agent
`.md` files from a separate neutral source reopens that tripwire pre-emptively, for a harness
that isn't broken today.

## Decision

The neutral agent profile is **not a new authored file**. Claude Code's existing agent
frontmatter stays the single, unbuilt source of truth — zero blast radius to the four live
files, `decision-2`'s no-build-step invariant for CC holds exactly as before, and AC #6's
round-trip requirement is trivially satisfied because there is no round trip. Harness
neutrality is realized as a **declared capability matrix** layered over that source,
extending `translation.yaml` (which already carries one per-field agent mapping,
`model_aliases`, as precedent for exactly this) with two new sections:

- **`tool_capabilities`** — a full mapping from every CC tool name used across the four
  agents (`Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`, `Agent`, `SendMessage`) to one of
  five neutral capabilities — read, search, edit, execute, delegate — replacing
  `scripts/gen_opencode.py`'s hardcoded `WRITE_TOOLS`/`BASH_TOOLS` sets (AC #8).
- **`field_treatments`** — a per-target declaration for every CC-only frontmatter concept
  (`color`, `effort`, `maxTurns`, and the delegate capability itself where a target has no
  spawn primitive), each tagged `unsupported` / `presentation-only` / `transform` with a
  reason string — replacing the generator's silent color-drop-with-comment and silent
  effort-drop-with-none (AC #5).

Both sections are data, not code: `transform_agent` reads them instead of hardcoding set
membership, and **fails the build**, rather than silently omitting, when it meets a tool name
or model alias absent from the matrix (AC #7). This generator change is deferred build work
(AC #4, #5, #7, #8), sequenced behind Claude Code stabilization per the task's existing
constraint; this decision fixes the shape so that build isn't guesswork later.

Body prose naming a harness-specific mechanism (`manager.md`'s `Agent`/`SendMessage` spawn
discussion) is **accepted, not neutralized** — the same pattern `translation.yaml`'s
`exclusions:` list already uses for `delegation`, `rubric-panel`, `layer-cycle`, and `waves`
("bound to Claude Code dispatch mechanics ... needs an opencode adaptation pass"). `manager`
joins that exclusions list rather than getting a body rewrite: an agent whose whole job is
spawning sub-agents has nothing coherent to say on a harness with no spawn primitive, so the
honest move is not shipping it there, not laundering its prose into vocabulary describing a
capability the target doesn't have. `scout`, `builder`, and `reviewer` bodies are already
clean (verified live) and stay that way as a documented authoring convention — no new lint
gate proposed here; add one only if a future agent's body actually drifts.

No roster schema-version field is added. `translation.yaml` already carries a top-level
`version:` field; that is what gets bumped when `tool_capabilities`/`field_treatments`
change shape, rather than duplicating the concept onto every roster row. Open question #3's
machine-detectable-drift need is better served by a completeness *check* than a version
*stamp*: extend `scripts/check_identity.py` (or a sibling gate) to fail when any agent's
`tools:`/`model:` frontmatter value has no corresponding matrix entry — deferred build work
alongside the generator change, but the check, not a version number, is what actually catches
drift.

Hooks and skills are explicitly **out of scope** for this decision. Hooks are already
`treatment: unsupported` for opencode (moot). Skills already have a working escape valve —
`translation.yaml`'s `exclusions:` list, hand-populated per skill — which is the exact
mechanism this decision extends to `manager`. A skills-specific version of this question, if
ever filed, can reuse this decision's exclusions-over-neutralization reasoning rather than
re-deriving it; it is not filed here because the task's own blast radius never named skill
files.

## Consequences

- No file under `primitives-core/agents/` changes shape or content as a direct result of
  this decision — the round-trip proof (AC #6) is by construction, not by testing.
- `translation.yaml` grows two new sections (`tool_capabilities`, `field_treatments`) and
  `manager` gains an `exclusions:` entry — both are build work, tracked as the remaining
  checkboxes on TASK-034 (AC #4, #5, #7, #8), still gated behind Claude Code stabilization
  per the task's existing constraint.
- `scripts/gen_opencode.py`'s `WRITE_TOOLS`/`BASH_TOOLS` module-level sets and its silent
  model/effort-drop branches are marked for removal when that build work lands; this
  decision does not touch the script itself.
- If a future harness needs a capability this matrix has no slot for (something beyond
  read/search/edit/execute/delegate), the matrix grows a new capability value — additive, not
  a source-file migration, which is the property that makes this cheaper than the rejected
  alternative.
- Revisit if Claude Code itself grows a "primary agent as named profile" concept (the
  forward-looking reason TASK-045 named the strategy layer "strategist" in the first place).
  At that point the neutral-profile-vs-CC-native-source tension this decision resolves in
  CC's favor may need reopening for the strategy layer specifically, since that role has no
  `primitives-core/agents/` file to anchor to at all.

**Affects:** `translation.yaml` (new `tool_capabilities` + `field_treatments` sections);
`scripts/gen_opencode.py` (`transform_agent` reads the matrix instead of hardcoded sets —
deferred); `scripts/check_identity.py` or a new gate (matrix-completeness check — deferred);
`primitives-core/agents/manager.md` (unaffected in content, gains a `translation.yaml`
`exclusions:` entry). TASK-034: this decision, once accepted, closes AC #1-3; AC #4-9 stay
open as deferred build work.

