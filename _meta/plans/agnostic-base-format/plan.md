---
title: "feat: agnostic base format + cross-vendor tool/config mapping (move off CC-as-baseline)"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #59 — ground the three CC-as-baseline breakdowns in translate.py, scope the prior-art survey, and stage the survey -> spec -> incremental-migration sequence with drift guards green throughout.
notes: "Drafted 2026-07-03; prior-art survey (deliverable A) resolves the flagged opencode-semantics hypotheses."
---

# feat: agnostic base format + cross-vendor tool/config mapping (move off CC-as-baseline)

_Residual: the #24 loadability smoke's first run (PR #60, commit `8a5094a`, merged 2026-07-03)
already landed the interim fixes — the opencode agent transform now drops `tools:` (silent
widening, documented in the docstring) and two source agents' raw multiline descriptions were
hand-folded to `>-` block scalars. What remains, and what this plan covers, is the owner-ruled
real fix (ruling 2026-07-02): survey prior art, specify an agnostic base format plus an explicit
cross-vendor mapping layer (tool ids, permission semantics, env interpolation, frontmatter
dialect), and migrate `primitives-core/` + `scripts/translate.py` off CC-as-baseline
incrementally — per primitive type, with `make ci` and `make smoke` green at every step. The
latent `${VAR}` env-interpolation bug in generated opencode mcp fragments is unfixed today and
rides in this scope._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #59 (this plan's tracking issue).
- Origin: the #24 loadability smoke's first run — opencode 1.17 rejected CC agent frontmatter at
  load; interim fix in PR #60 (`8a5094a`) drops `tools:`. Owner ruling 2026-07-02: drop for now,
  redesign the baseline as the real fix (recorded in the #59 body and the PR #60 commit message).
- Relations: #24 (merged — provides `make smoke`, the regression detector this plan's acceptance
  leans on). The transform docstring at `scripts/translate.py:207` names this issue as the
  follow-up ("Cross-vendor tool mapping is the baseline-format follow-up issue").
- Contract impact: **redesigns the translation baseline** — the source formats under
  `primitives-core/` (85 primitives), `scripts/translate.py` (the whole transform/render layer),
  the capability matrix in `primitives-core-translation-config.yaml`, and ALL of `targets/`
  (claude-code, opencode, claude-agents — every generated artifact regenerates). This is the
  largest contract surface in the repo. The results lock
  (`primitives-core-translation-results.json`) schema likely grows a surfaced-unsupported
  vocabulary. Consumers (dotfiles-bootstrap deploy, the installed plugin marketplace) read
  `targets/` only — output-shape compatibility per vendor is part of acceptance, not assumed.

## The problem (grounded in source)

`primitives-core/` uses Claude Code's formats as the base: agents are CC `.md`-with-frontmatter
copied verbatim to the claude-code target (`capability: native`,
`primitives-core-translation-config.yaml` capabilities block), and `translate.py` transforms
CC -> each other target. Three verified breakdown mechanisms, all re-checked in source today
(2026-07-03):

**1. `tools:` allowlist dropped for opencode — silent widening.**
`transform_agent_opencode` (`scripts/translate.py:200-223`): the docstring
(`translate.py:203-207`) documents that `tools` is dropped "because the CC allowlist doesn't
translate: opencode expects a per-tool boolean map that toggles against defaults, so a converted
list would load but not narrow — found by `make smoke` (opencode 1.17 rejects the CC string form
at load)". The drop is implemented in the skip-set at `translate.py:217`
(`{"name", "model", "color", "tools"}`). Every opencode agent therefore gets the default
toolset. The widening is **pinned as expected behavior** by `tests/test_translate.py:145-147`
(`assertNotIn("tools:", out)`) — migration must flip that pin, not just the transform.

**2. `${VAR}` vs `{env:VAR}` env-interpolation mismatch in mcp fragments — latent bug, live today.**
The neutral mcp connection-spec convention mandates `${VAR}` placeholders
(`primitives-core/mcp/README.md:19` and `:27` — "secrets as `${VAR}` placeholders ONLY").
`mcp_to_opencode` (`scripts/translate.py:273-287`) copies `spec["env"]` verbatim into the
opencode `environment` key (`translate.py:285-286`) with no syntax translation. Live instance:
`externals/mcp/github.json:8` carries `"${GITHUB_PERSONAL_ACCESS_TOKEN}"`, which lands
byte-identical in the generated `targets/opencode/mcp/github.json:17`. Per the issue (owner
account; not verifiable from this repo), opencode does not substitute `${VAR}` — its form is
`{env:VAR}` — so the value passes to the server literally. The passthrough is also pinned as
expected by `tests/test_translate.py:64-71`. The current smoke does not catch this: it asserts
servers are LISTED, not that env resolves (PR #60 commit message).

**3. Frontmatter-dialect mismatch — CC lenient, opencode strict; mitigated by hand today.**
The transform deliberately preserves the `description` byte-for-byte
(`translate.py:203-204`: it "carries literal \n / <example> blocks that re-serialization would
corrupt") — i.e. there is NO normalization layer; whatever dialect the source uses flows
through. The smoke's first run found `chat-ui-builder` and `mcp-integrator` source descriptions
in raw multiline form "parsed in CC but made opencode silently drop both agents"; the fix in
`8a5094a` folded both **source files** to `>-` block scalars (see the diff on
`primitives-core/agents/chat-ui-builder.md`). So the source dialect is currently constrained by
convention and hand-edits, enforced nowhere — `validate_primitives.py` does not check it, and
`translate.py`'s own parsers are hand-rolled regex, stdlib-only by design (`translate.py:18`).

**Current baseline (verified via `make build-check`, green today):**

| Fact | Value | Source |
| ---- | ----- | ------ |
| Roster size | 85 primitives: 58 skills, 18 agents, 5 hooks, 4 mcp | `primitives-core.yaml` type counts |
| Build result | claude-code 89 built 0 skipped; opencode 84 built 0 skipped; claude-agents 77 built 0 skipped | `make build-check` output 2026-07-03; matches `primitives-core-translation-results.json` |
| Target vendors | targets/claude-code (filesystem marketplace), targets/opencode (filesystem dirs), targets/claude-agents (CMA API payloads) | `primitives-core-translation-config.yaml` targets block; `scripts/translate.py:39` |
| Agent capability row | claude-code native copy; opencode transform; claude-agents render | config capabilities block |
| Hooks | claude-code only; unsupported elsewhere by decision | config capabilities block |
| Skipped-and-recorded machinery | exists already (capability `unsupported` -> skip + reason in results lock) | `primitives-core-translation-config.yaml` header; `translate.py:354-361` `rec()` |

Skills are near-portable already (native copy to CC and opencode; CMA multipart render) — the
breakdowns are concentrated in **agents** (frontmatter + tools) and **mcp** (env interpolation),
which is why the issue scopes the spec "agents first".

## Deliverables

### A — Prior-art survey + adopt/adapt/build memo

Survey the cross-vendor agent/config portability space before inventing a schema. One memo
(staged in this folder as `survey.md`), organized per concern because the answer may differ per
concern. Named candidates from an initial sweep (existence web-verified 2026-07-03; capabilities
NOT yet verified — that verification IS the survey):

| Lane | Candidates to assess | The question for this repo |
| ---- | -------------------- | -------------------------- |
| Context-file standards | AGENTS.md (agents.md, Agentic AI Foundation); SKILL.md open standard | Prose portability is solved there — do they touch agent definitions, tools, or config at all? |
| Cross-tool sync/convert CLIs | rulesync (dyoshikawa); ai-rules-sync (lbb00); agent_sync (yelmuratoff); agent-skills; symlink-based managers | Do any hold an internal canonical model with per-vendor emitters? Crucially: does ANY map subagent tool/permission semantics, or do they all copy/symlink prose? |
| Vendor-native schemas | opencode agent schema (mode, per-tool boolean map, permission); CC agent frontmatter; codex/goose/aider config layers; CMA BetaManagedAgentsCreateAgentParams | The authoritative per-vendor column of B's mapping tables — pin doc URLs + versions |
| MCP neutral-spec prior art | MCP official registry server.json shape; per-client env interpolation syntaxes (CC `${VAR}`, VS Code `${env:VAR}`, opencode `{env:VAR}`) | Is there an existing neutral connection-spec + interpolation convention to adopt instead of ours? |

The memo ends in an adopt / adapt / build recommendation **per concern** (agent frontmatter
dialect; tool/permission mapping; env interpolation; mcp spec shape), each with cited evidence,
weighed against the repo's stdlib-only/no-install constraint (`translate.py:18`).

**Acceptance:** memo covers all four lanes incl. every named candidate (or records why one was
skipped); contains an explicit yes/no finding on whether any surveyed tool maps tool-permission
semantics cross-vendor; each recommendation cites the evidence (URL + version); pins the
authoritative opencode docs for `{env:VAR}` and the tools boolean map (currently sourced only
from the issue text — see unverifiables); owner adopt/adapt/build ruling recorded on #59 before
B starts.

### B — Base-format spec (agents first) + vendor mapping tables

A spec document (graduates to `docs/` on acceptance; drafted in this folder) defining the
agnostic base format for the types we translate, agents first, plus the explicit mapping layer:

- **Tool ids + permission semantics table:** neutral tool-capability declaration -> CC allowlist
  string -> opencode per-tool boolean map computed against opencode's defaults -> CMA `tools[]`
  payload field. Every cell is one of: exact map, lossy map (documented loss), or
  **unsupported-surfaced** (recorded in the results lock with a reason and printed in the build
  summary — the existing `rec(skipped/reason)` machinery at `translate.py:354-361` extends to
  per-field records; no silent widening anywhere).
- **Env interpolation table:** neutral placeholder form in specs -> per-vendor render (`${VAR}`
  for CC `mcpServers`; opencode's own form for `environment`; CMA is remote-only so env doesn't
  apply — headers only).
- **Frontmatter dialect:** the YAML subset the base format permits (block-scalar descriptions
  mandatory, the `8a5094a` lesson codified), enforced at source by a new check in
  `scripts/validate_primitives.py` so dialect drift is caught at `make validate`, not discovered
  at smoke.
- **Skills/hooks stance:** recorded explicitly (expected: skills stay SKILL.md-shaped, hooks stay
  CC-only — owner decisions 2 below).

**Acceptance** (maps to the issue's first two checkboxes): the tools mapping table demonstrates,
for each of the 18 roster agents, either narrowing that survives to opencode or an explicit
unsupported-surfaced row — no cell is silent; the env table renders each vendor's own syntax with
a worked example for the live `github` external; a dry-run translation of all 18 agents + 5 mcp
specs (4 core + 1 external) against the spec is attached, reviewed against real opencode/CC
loads via `make smoke` in a branch.

### C — Incremental migration of primitives-core/ + translate.py

Per-type, incremental, drift guards green throughout — each step is one PR that changes source +
transform + tests together, runs `make build`, and lands with `make ci` AND `make smoke` green:

| Step | Scope | Key edits | Pinned tests to flip |
| ---- | ----- | --------- | -------------------- |
| C1 mcp env interpolation | smallest surface: 4 core specs + 1 external + one render fn | `mcp_to_opencode` translates placeholder syntax; `mcp/README.md` convention updated | `tests/test_translate.py:64-71` (verbatim env passthrough) |
| C2 agents | 18 source agents to base format; `transform_agent_opencode` becomes a real mapping incl. tools; validate gains the dialect check | `translate.py:200-223`; `validate_primitives.py`; results-lock surfaced-unsupported entries | `tests/test_translate.py:145-147` (tools dropped) |
| C3 skills + hooks | expected no-op per B's stance; confirm and record | config matrix comments; spec cross-refs | none expected |

Rollback unit is the PR: `targets/` is fully generated, so reverting a step is `git revert` +
`make build`. Results-lock schema changes (surfaced-unsupported records) land in the same PR as
the code that emits them, keeping `build-check` green at every commit on main.

**Acceptance** (maps to all three issue checkboxes): after each step `make ci` green and
`make smoke` green on a machine with opencode + claude installed; final state — every opencode
agent either narrows its toolset or has an unsupported-narrowing record in
`primitives-core-translation-results.json` surfaced in the build summary; `${VAR}` no longer
appears in any `targets/opencode/mcp/*.json` (grep-clean) unless A proves opencode substitutes
it; a smoke check asserts env syntax per vendor (extend `scripts/smoke.py` — today it only
asserts servers are listed).

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| make ci aggregate (required) | yes | always; fires on every PR of C |
| Targets drift guard (make build-check) | yes, heavily | every step edits primitives-core/ and/or translate.py -> full targets/ regeneration; never hand-edit targets/ |
| Unit tests (make test) | yes | test_translate.py pins current transform behavior at :64-71 and :145-147 — flipping those pins is in-scope work, not collateral |
| Content validation (make validate) | yes | B adds the frontmatter-dialect check to validate_primitives.py |
| make smoke (opt-in, NOT in ci) | yes — the end-to-end proof | Makefile smoke target; foreman runs it per step; requires installed opencode + claude, so it is a foreman gate, not a CI gate |
| Roster drift guard (make check) | no, unless source paths move | no primitive is added/removed/renamed; if the base format relocates or re-extensions source files, this DOES fire — flag in the step PR |
| Naming taxonomy | no | no new primitive or plugin names |
| yamllint | only if C edits primitives-core-translation-config.yaml or workflows | likely fires in C2 (capability matrix wording); actionlint does not fire (no workflow edits) |

Contract hygiene: the results lock is a consumed artifact — its schema gains fields, never
mutates existing ones (same additive discipline as the checklist stable-ID contract). `targets/`
output shapes per vendor are the deploy contract with dotfiles-bootstrap; C's PRs call out any
output-path or shape change explicitly.

## Parallelism + landing order

| Unit | Depends on | Parallelism |
| ---- | ---------- | ----------- |
| A survey | none | parallelizes across the four lanes — one research agent per lane (context-file standards; sync/convert CLIs; vendor schemas; MCP/env), reconciled into one memo by the foreman |
| Owner ruling on A | A memo | serial gate — adopt/adapt/build decision blocks B |
| B spec | A ruling | single author (one coherent schema); the dry-run translation + smoke branch can be a second agent verifying B's draft adversarially |
| C1 mcp | B accepted | independent of C2 in content but shares translate.py — serialize the translate.py edits (C1 then C2) or chain builders on one branch |
| C2 agents | B accepted; C1 landed | the 18 source-agent edits parallelize across files once the transform + validate changes exist; one owner for translate.py itself |
| C3 skills/hooks | B accepted | mostly a recorded confirmation; can overlap C2 |

Landing order: A -> ruling -> B -> C1 -> C2 -> C3, each C-step its own PR. No timelines —
execution determines timing.

## Open questions / owner decisions

1. **Adopt vs adapt vs build (the A ruling).** Recommended default: decide per concern, with the
   working hypothesis **build a thin in-repo neutral schema while adopting existing conventions
   where they exist** — AGENTS.md/SKILL.md for prose-shaped things, the MCP registry's spec shape
   for connections — because the stdlib-only, zero-install constraint (`translate.py:18`) weighs
   against taking a dependency on an external converter, and the crux (cross-vendor
   tool-permission mapping) is plausibly unsolved anywhere. A's explicit yes/no finding tests
   that hypothesis; if a surveyed tool genuinely solves it, adopt/adapt beats build.
2. **Do skills stay CC-shaped (SKILL.md)?** Recommended: **yes** — SKILL.md is a de-facto open
   standard that opencode already reads (skills are `native` in both filesystem targets today),
   and the issue itself calls skills "already near-portable". The spec records this stance;
   C3 is then a confirmation, not a migration. Alternative: fold skills into the base format —
   rejected as scope without a demonstrated breakdown.
3. **Per-vendor unsupported-feature policy.** Recommended: **surfaced-unsupported as a
   first-class outcome** — recorded per primitive (and per field where needed) in the results
   lock with a reason string, printed in the `make build` summary, and asserted by smoke (no
   silent widening). Alternative: hard-fail the build on any unsupported feature — rejected; it
   would block shipping any narrowed agent to opencode at all, which is worse than a recorded
   degradation.
4. **Base format carrier for agents: keep `.md`-with-frontmatter, or move to a data file that
   renders `.md`?** Recommended: **keep `.md` + a constrained frontmatter dialect** (block-scalar
   descriptions, enforced by validate) — the claude-code target is a verbatim copy and the body
   IS the persona; a data-file indirection buys dialect safety we can get more cheaply from
   validation. Revisit only if A finds a strong prior-art carrier.
5. **Neutral env-placeholder syntax.** Recommended: **keep `${VAR}` as the neutral source form**
   (it is already the documented convention at `primitives-core/mcp/README.md:19,27`) and make
   each renderer translate OUT of it per B's table — do not invent a third syntax and force-edit
   every spec.

## Unverifiables (to be resolved by A)

- opencode's `{env:VAR}` interpolation form and its non-substitution of `${VAR}` — sourced from
  issue #59's text (owner account of the smoke run), not verified against opencode docs from
  this repo. A pins the authoritative doc.
- opencode's per-tool boolean-map semantics ("toggles against defaults") — sourced from the
  transform docstring (`translate.py:203-207`) and the issue; same resolution path.
- Survey candidates (rulesync, ai-rules-sync, agent_sync, agent-skills): existence verified by
  web search 2026-07-03; capability claims unverified — assessing them IS deliverable A.
