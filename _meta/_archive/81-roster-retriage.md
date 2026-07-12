---
title: "harden: roster re-triage — demote untested authored primitives + correct external provenance"
type: spec
status: active
created: 2026-07-12
purpose: Source-grounded build plan for #81 — demote the untested authored primitives flagged in the 2026-07-05 owner roster review to the workbench incubator, and flip five mis-recorded authored entries to origin sourced with pinned upstream refs. Two paired PRs (da removes, wb receives), mirroring the da#79/da#80 portability-demotion wave.
notes: Drafted + executed 2026-07-12. Precedent studied first (da#80 commit cfe6c1f + wb docs/promotions-log.md #79 records). One deliberate deviation from the issue body's literal wording, documented under "Demotion mechanics" below.
---

# harden: roster re-triage — demote untested authored primitives + correct external provenance

_The 2026-07-05 owner roster review flagged two classes of hygiene: (A) a set of
`grandfathered-pending-use` **authored** primitives that are not yet proven and should leave
the distributed `core`/`toggle` shelves until they pass the workbench gate, and (B) five
entries recorded `origin: authored` that were in fact **sourced** from upstream and must flip
to `origin: sourced` with a pinned ref. This plan executes both as two paired PRs — da#81
removes the roster entries + moves the source; a workbench PR receives them into `incubator/`
with REGISTRY rows + promotions-log records — mirroring the da#79/da#80 demotion wave._

Status: active
Date: 2026-07-12

## Tracking

- Issue: #81 (`Roster re-triage: demote untested skills + correct external provenance
  (2026-07-05 review)`, OPEN, `type:chore`). Staged body:
  `_meta/plans/roster-retriage/issue-body.md` (verbatim copy of the live #81 body).
- Origin: 2026-07-05 owner roster review.
- Paired workbench PR: `feat/receive-da81-demotions` (branch on
  `dotfiles-agents-workbench`) — receives the 14 demoted candidates.
- Relations: precedent is **da#79 / da#80** (portability-conformance wave) + **wb#32/wb#33**
  (workbench receipt). Cross-refs #36 (clone-at-build externalizes `sourced` skills — the
  Deliverable-B flips feed it).

## Demotion mechanics (the precedent + one deviation)

The issue body says "Set `disposition: demoted` in the da roster". The **actual da#79/da#80
mechanic** (commit `cfe6c1f`, wb `docs/promotions-log.md`) is different and is what this PR
follows:

1. **The roster ENTRY is removed entirely** — not marked `disposition: demoted`.
   `roster-update: … entry removed` in every #79/#80 promotions-log record.
2. A **retirement-record** (trigger citing the review) is written in wb
   `docs/promotions-log.md`.
3. A **REGISTRY.md** row (`incubating` + blocker) is added.
4. The **source moves** to wb `incubator/<name>/`.

**Why entry-removal, not `disposition: demoted`:** `scripts/translate.py` branches only on
`shelf`, never on `disposition` — a `demoted` entry that still points at on-disk source would
**still be built into `targets/`** (defeating the demotion), and moving the source while
keeping the entry fails the roster↔disk drift guard (`scripts/check_roster.py`). Entry-removal
+ source-move is the only mechanic that actually drops a primitive from `targets/` AND keeps
`make ci` green. The `demoted` disposition value remains defined in the schema but is
vestigial (0 uses in practice). **This deviation from the issue's literal wording is
deliberate; the intent — "these leave the distributed shelves now" — is honored exactly.**

## Deliverables

**A — Demote queue (14 primitives → wb incubator).** For each: remove the roster entry, move
the source to `dotfiles-agents-workbench/incubator/<name>/`, write a wb promotions-log
retirement-record + REGISTRY row, `make build` so `targets/` drops it.

- 13 skills: `api-server-design`, `developer-focus`, `setup-project-dashboard`,
  `update-project-dashboard`, `cms-pdf-to-markdown`, `cms-json-data-dictionary`,
  `cms-bigquery-etl-generator`, and the six `obsidian-*`
  (`obsidian-api-basics`, `obsidian-best-practices`, `obsidian-chat-ui`, `obsidian-cli`,
  `obsidian-dom-helpers`, `obsidian-mcp-server`).
- 1 hook (3 handler entries + `hooks.json`): the `python-standards` hook
  (`python-standards.SessionStart.session-start`, `.PostToolUse.post-tool-use`, `.Stop.stop`).
  **Foldered in the workbench as `incubator/python-standards-hook/`, NOT `python-standards`**,
  to avoid a name collision with the NEW `python-standards` **SKILL** that **wb#37** is
  incubating in parallel. The hook (da#81) and the skill (wb#37) are DISTINCT artifacts —
  recorded in both the REGISTRY row and the promotions-log record.

**Plugin fallout (forced by the demotions, handled like da#80):**
- `dev-focus` plugin — sole member `developer-focus` demoted (its hooks already left at
  da#79) → plugin **removed** from `plugins.yaml` + marketplace (regenerated).
- `project-dashboard` plugin — both members demoted → plugin **removed**.
- `python-standards` plugin — all three hooks demoted → plugin **removed**.
- `obsidian-plugin-dev` plugin — **survives** (10 members, only 6 obsidian-* removed;
  `langgraph-sse-client` skill + `chat-ui-builder`/`mcp-integrator`/`plugin-scaffolder`
  agents remain). Version bumped `0.1.1 → 0.1.2`.

**Acceptance** (issue AC-1): every Deliverable-A item is removed from the roster + moved to
the incubator with a REGISTRY row + promotions-log record; none remains a distributed
`grandfathered-pending-use` authored primitive. `make build-check` confirms `targets/` no
longer ships them.

**B — Provenance corrections (5 entries flip `authored → sourced`).** With `vendor` +
`upstream` + PINNED `ref` (SHA/tag, never a branch — `check_roster.py` enforces).

| Entry(ies) | vendor | upstream | ref (pinned) | Evidence |
| ---------- | ------ | -------- | ------------ | -------- |
| `framework-selection` | langchain-ai | `github.com/langchain-ai/langchain-skills` | `c88193a48f387560697e1152e32dc5fd239c83e4` | Local rename of the `ecosystem-primer` skill, which exists at that exact ref (same ref the roster's sibling deep-agents-* / langchain-* entries already pin). Same org, same purpose, same distinctive opening directive ("INVOKE … at the START of any LangChain/LangGraph/Deep Agents project"). |
| `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`, `openspec-propose` | Fission-AI | `github.com/Fission-AI/OpenSpec` | `6a3a1263fe4d5994716841c46acdd3c3d799c042` (tag `v1.2.0`) | The four SKILL.md files are GENERATED by the OpenSpec CLI (`generatedBy: "1.2.0"`, `author: openspec`, `compatibility: Requires openspec CLI.`). `src/core/shared/skill-generation.ts` at `v1.2.0` emits exactly these four `dirName`s + this frontmatter; `src/core/init.ts` binds `generatedBy` to the package version → `1.2.0` = release `v1.2.0`. `vendor` recorded as the GitHub org `Fission-AI` (not `openspec`) so the naming guard doesn't flag `openspec`-in-id. |

**Acceptance** (issue AC-2): the five entries read `origin: sourced` with recorded
`upstream` + pinned `ref`; `make ci` green.

**Confirm-only (issue AC-3, MUST NOT change):** `shadcn`, `find-skills`,
`deep-agents-{core,orchestration,memory}`, `langgraph-persistence`, `langchain-fundamentals`,
`langchain-dependencies` — verified untouched.

## Two flagged judgment items (for the owner)

1. **`setup-project-dashboard` + `update-project-dashboard`** were demoted **pending the
   "disambiguate from `board-reporting`" decision** (J4). Bench-side follow-up; tracked on
   their REGISTRY rows as a J4 blocker. They are not being merged/kept here — the overlap call
   is deferred.
2. **CMS trio** (`cms-pdf-to-markdown`, `cms-json-data-dictionary`,
   `cms-bigquery-etl-generator`) demoted **pending genericizing** (J2 — SKILL.md is
   CMS-domain-scoped). Bench-side follow-up; tracked on their REGISTRY rows as a J2 blocker.

## Gate & contract hygiene

| Gate | Fires on #81? | Why / result |
| ---- | ------------- | ------------ |
| CI aggregate (make ci) | YES | roster + plugins.yaml + source moves → all five lanes must pass. Green. |
| Roster drift guard (make check) | YES | 16 entries removed + 5 origins flipped → roster↔disk must reconcile. Clean. |
| Targets drift guard (make build-check) | YES | demotions drop from `targets/`; run `make build`, commit. In sync. |
| Naming taxonomy (make names) | YES | flipping `origin: sourced` adds `vendor:` — the guard bans vendor-in-id (token-boundary). `openspec` vendor would collide with the `openspec-*` ids → recorded vendor as org `Fission-AI` instead. Clean. |
| yamllint / actionlint | manual | `primitives-core.yaml` + `plugins.yaml` edited; ASCII-safe. |
| Canonical-doc amendment | no | no spine-doc behavior change (CLAUDE.md's "mcp empty" note unaffected; hooks now also empty — noted in the test fixture, not a spine doc). |

**Stale-test reconciliation:** `tests/test_check_roster.py::test_parses_real_roster` asserted
`python-standards.Stop.stop` as a live hook fixture. That hook is now demoted and **no hooks
remain in the roster** — the assertion was updated (dropped, with a comment mirroring the
existing "mcp empty since #79" note) to reflect hooks empty since #81. This is legitimate
reconciliation of a test pinning superseded state, not a scope creep.

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| B — origin flips | primitives-core.yaml (5 entries) | none | parallel with A; pure roster edit |
| A1 — roster removals + source moves | primitives-core.yaml + primitives-core/ + plugins.yaml | none | parallel with B |
| A2 — wb receipt | wb incubator/ + REGISTRY.md + promotions-log.md | A1 (source in hand) | the paired wb PR; rebase on origin/main (wb#36 hook rows + wb#34 fix live there; wb#37 python-standards SKILL row is a foreseeable trivial conflict) |
| build + gates | make build; make ci (da) · make promote-check-all + make test (wb) | A1+A2+B | foreman-run, not asserted |

Landing order only; no timelines. The da and wb PRs are opened together and cross-reference;
**do not merge** without owner review. wb PR body notes "rebase before merge" (REGISTRY.md +
promotions-log.md also touched by the parallel wb#37 PR).
