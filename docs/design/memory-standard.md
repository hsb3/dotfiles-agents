---
title: "Memory standard — technical design (two-layer, visible, portable agent memory)"
type: technical-design
status: active
created: 2026-07-02
updated: 2026-07-05
summary: The engineering design behind the memory-taxonomy skill — storage layers, loading tiers, flows, alternatives, risks. The applied standard ships in the skill; this is the rationale it defers to.
migrated_from: hsb-2026 vault 1_Engineering/technical-designs/memory-standard.md (2026-07-05)
tags: [devtools, memory, claude-code, project-workflow]
---

# Memory standard — two-layer, visible, portable agent memory

_This is the design rationale the `memory-taxonomy` skill cites but does not restate (loading-tier
mechanics, alternatives considered, risks). The as-built system is the shipped
`primitives-core/skills/memory-taxonomy/` + the `cc-project-memory` CLI._

*Priority P1: project-workflow's success criterion 4 (tracked memory in every adopted repo + one executed promotion) depends on this design, but it does not gate the extenders pipeline itself. PM is an affected workstream because curation is a cadence, not just a mechanism.*

## Problem context

Claude Code's behavior is heavily shaped by the memory context available at session start, but its native default stores project memory in a hidden, machine-local directory (`~/.claude/projects/<slug>/memory/`) — invisible and non-transferable. Henry's requirements (2026-06-22 dotfiles journal): memories must be **visible to me and portable across machines**; **separated global vs project**; some **always on**, some **invoked situationally**; with a **mechanism for promoting project memories to global**. The journal also fixes two anchors: global memories live in `~/dotfiles` symlinked to `~/.claude`, and every project keeps a git-tracked `.claude/memory` directory.

This TDD renders the two source canvases — `CLAUDE_MEMORY/memory-standard-architecture.canvas` and `memory-standard-process.canvas` — as one coherent system design. **Split of ownership:** this is the *engineering design* (storage, loading, flows, tracking); the *packaged content standard* that ships inside the `project-workflow` plugin — naming scheme, index format, v1 defaults, audit checklist — is the [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md) feature-spec, written in parallel. Where this doc says "taxonomy," that spec owns the answer.

## Goals & non-goals

### Goals

- Two storage layers with distinct write disciplines: curated global vs auto-accumulated project
- Loading semantics that separate always-on (hot-load) from situational (on-demand)
- A birth-routing rule cheap enough to run in the hot path, with fine sorting deferred to curation
- A defined promotion/curation process (project → global; memory → docs/ADRs)
- Visibility + portability: plain files, git-tracked or dotfiles-stowed; no hidden state as system of record

### Non-goals

- The naming scheme, index format, and v1 cadence/limit defaults — [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md)
- The audit/scaffold tooling that checks conformance — [repo-compliance-audit](../../primitives-core/skills/repo-compliance-audit/SKILL.md)
- Cross-harness memory (opencode etc.) — this designs against Claude Code's memory mechanisms; portability to other harnesses is an open question below
- Content policy for specs/decisions — those graduate *out* of memory into `docs/`/ADRs per [repo-meta-structure-standard](../../primitives-core/skills/repo-meta-structure/SKILL.md)

## Proposed design

### High-level overview

Two layers with parallel structure but **asymmetric loading and asymmetric authorship** (architecture canvas):

| Layer | Lives at | Tracked via | Who writes | Loaded how |
|---|---|---|---|---|
| **Global** | `~/dotfiles` → stow-symlinked to `~/.claude` | dotfiles repo | **Henry authors / curates**; grown only by promotion | `MEMORY.md` index hot-loads via `@import` in the global `CLAUDE.md`; topic files on-demand only |
| **Project** | `<repo>/.claude/memory/` | that repo's git | **Claude auto-writes** ("lean learnings") | active `autoMemoryDirectory` → index hot-loads; topic files lazily pulled |

The asymmetry is the point: the global layer is a per-session tax paid by every project, so it stays a curated index; the project layer is the frictionless capture surface and travels with its repo. A repo not opted in falls back to the hidden native default — separated, but invisible and non-portable, which is exactly the state this standard eliminates.

Alongside memory, the architecture canvas places the neighbors that memory must *not* absorb: `CLAUDE.md` + instructions and `rules/` (both layers — Henry-authored directives), `docs/` + `docs/decisions/` ADRs (durable authored artifacts, repo-tracked), and `_meta/operations/` (secrets, untracked). Machine-local knobs stay in `.claude/settings.local.json`, untracked.

### Loading semantics (session context at startup)

From the architecture canvas, three tiers:

1. **Hot-load, always on** — every `CLAUDE.md` in scope + non-path-scoped rules. Directives and standing preferences live here, never in memory.
2. **Hot-load, index only** — the `MEMORY.md` indexes: global (via `@import`, present even when a project overrides the active dir) and project (via the repo's `autoMemoryDirectory`). Both layers are simultaneously visible at index granularity.
3. **On-demand** — memory topic files and path-scoped rules. Project topics are lazily pulled when relevant; **global topic files are not auto-pulled** — a session must read one explicitly via its index line.

Always-on vs situational therefore maps to: instructions/unscoped rules = always-on; memory topics + path-scoped rules = situational. Where a "situational directive" should be a rule vs a skill vs a memory is the rules-vs-skills criterion — open in project-workflow, documented in [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md), pending Henry's sign-off.

### Data model

- **`MEMORY.md`** (each layer) — an index, one line per topic file with a hook, grouped per the taxonomy's sections. The global index is hard-capped (~1 screen; exact figure is a [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md) default) because it is a universal per-session cost.
- **Topic files** — freeform markdown, one theme each, self-standing (enough context to be read cold). Naming scheme owned by [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md) (the process canvas assumes a prefix-section scheme; the taxonomy spec decides and the curation pass renames to whatever it locks).
- No database, no binary state: **plain files only** — that is what makes the layer visible, diffable, and portable by construction.

### Process flows (from the process canvas)

**Birth — one question in the hot path: which kind?**

| Claude learns / produces… | Route |
|---|---|
| project-specific fact, state, lesson | write to `<repo>/.claude/memory/` + add one index line |
| clearly cross-project pattern | promote to `~/.claude/memory` (rare at birth; usually via curation) |
| durable decision | author an ADR in `docs/decisions/` — not memory |
| design / spec | author a doc in `docs/` — not memory |
| secret / live-op | `_meta/operations/`, untracked — never memory |

Then: index line → **commit with the repo** ("travels + mineable"). Fine sorting is deliberately *not* done at birth — capture stays frictionless; a global-worthy fact landing in project memory is fine, curation routes it later.

**Periodic curation** (canvas label: "run cc-project-memory audit") — findings → actions:

| Finding | Action |
|---|---|
| oversized file | graduate to `docs/` or an ADR, leave a one-line pointer (feeds back into the docs flow) |
| stale or resolved work | prune or archive — memories are batons, not journals |
| naming off-taxonomy | rename per [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md) |
| duplicate of a global | merge, or promote up to `~/.claude/memory` |

**Promotion (project → global)** — a curation act, never automatic: distill the fact, write it to the global layer, add its global index line *only if it fits the index cap* (prune/merge the global index first if not), then prune the project copy. This is the mechanism project-workflow success criterion 4 requires executed at least once.

### Tracking & gitignore convention

Track-by-default with a narrow ignore stanza per repo — track `memory/`, `rules/`, `settings.json`; ignore the machine-local/transient bits:

```gitignore
.claude/settings.local.json
.claude/worktrees/
.claude/*.lock
.claude/**/.DS_Store
```

The journal's "one gitignore convention for all repos" lands here; the exact template ships in [repo-meta-structure-standard](../../primitives-core/skills/repo-meta-structure/SKILL.md) and the audit in [repo-compliance-audit](../../primitives-core/skills/repo-compliance-audit/SKILL.md) checks it. Global-layer files are tracked in the dotfiles repo (stow-managed), so both layers are in version control — the portability requirement reduces to "clone your repos + stow your dotfiles."

### As-built vs to-be-built

**As-built (on Henry's machine today):** the two-layer setup itself — global memory stowed from dotfiles with the `@import` index; the `cc-project-memory` CLI (`init [--portable] [--migrate]`, `status`, `path`, `list`) that opts a repo in, points `autoMemoryDirectory` at the tracked dir, and fixes `.gitignore`; the `migrate-claude-memory` helper for relocated projects.

**To-be-built:** the **audit** the process canvas names (`cc-project-memory audit` — the curation findings table above as a runnable report: oversized/stale/off-taxonomy/duplicate-of-global); packaging the standard as plugin reference content ([memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md)); the compliance check ([repo-compliance-audit](../../primitives-core/skills/repo-compliance-audit/SKILL.md) verifies structure exists — tracked dir + index — not content quality); and rollout to the five named repos.

### Alternatives considered

- **Native hidden default (do nothing)** — rejected: separated per repo but invisible, machine-local, non-transferable; fails both stated requirements.
- **Single global memory store** — rejected: project facts pollute every session everywhere; project knowledge doesn't travel with its repo.
- **Fine-grained routing at birth (project vs global vs docs decided per write)** — rejected: friction kills capture; the two-way birth rule (secret? everything else → project) plus curation achieves the same end state.
- **Auto-promotion of recurring facts** — rejected: the global index is a curated, capped, per-session tax; promotion is a human judgment ("no unattended path into the trusted set" — same stance as the extenders promotion gate).

## Infrastructure & deployment

No services. Delivery is (a) dotfiles stow for the global layer, (b) `cc-project-memory init` + a committed `.claude/memory/` per repo, (c) the standard itself distributed as `project-workflow` plugin content through the extenders pipeline (extenders-system). Note for distribution: the standard is documents + CLI conventions — it requires no hooks, so it survives on hook-less harnesses per distribution-capability-matrix.

## Risks & mitigation

- **Risk:** global index bloat degrades every session → **Mitigation:** hard cap as a promotion gate (curate before adding); measure before building enforcement tooling ([memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md) v1 default).
- **Risk:** memory becomes a directive dump (instructions hiding in topic files, silently not always-on) → **Mitigation:** the birth table routes directives to CLAUDE.md/rules; the audit flags directive-shaped memory content.
- **Risk:** curation never happens (solo maintainer, no calendar) → **Mitigation:** bind curation to existing boundaries — wrap-up/handoff moments — rather than a schedule (project-workflow v1 default); the audit makes a pass cheap enough to actually run.
- **Risk:** tracked memory leaks a secret into a repo → **Mitigation:** secrets are routed to untracked `_meta/operations/` at birth; the secret question is the *only* hot-path decision precisely so it's never skipped.

## Open questions

(Carried from the 2026-06-22 journal and project-workflow; resolved to v1 defaults there, restated here for the engineering record.)

- **Curation cadence** — v1: triggered at project boundaries (handoff/wrap-up), not a calendar. Revisit on evidence of rot between boundaries.
- **File/token limits** — v1: cap only the always-loaded index (~1 screen); no cap on lazily-loaded topics. Exact figures in [memory-taxonomy](../../primitives-core/skills/memory-taxonomy/SKILL.md).
- **Rules-based memories vs skills** — v1 triage: rules = path-scoped standing directives; skills = invocable procedures; memory = facts/state. Criterion needs Henry's sign-off.
- **Cross-harness portability** — this design is Claude Code-native (`autoMemoryDirectory`, `@import`). Whether the translation service should render a memory-equivalent for opencode (which has no identical mechanism) was flagged as an open question in single-canonical-copy-with-translation-service and remains open.
- **Mining backlog** — the journal's inventory task (sweep `~/.claude/projects/*/memory/` for hidden stores worth migrating via `--migrate`) is operational follow-up, not design.
