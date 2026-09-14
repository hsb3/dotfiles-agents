# The memory taxonomy — v1

The standard that tells every session where knowledge lands and how it moves. Three axes,
one birth rule, one promotion mechanism, three stated defaults. Design rationale —
loading-tier mechanics, alternatives considered, risks — lives in the memory-standard
technical design in this repo at
`docs/design/memory-standard.md`; this file
is the standard itself.

Requirements traceability (2026-06-22): **visible/portable** → "Visible and portable by
construction"; **global/project split** → Axis 1; **always-on/situational** → Axis 2;
**promotion** → "The promotion mechanism".

## Visible and portable by construction

Both layers are plain markdown files under version control — never hidden machine-local
state. Global memory travels via the dotfiles repo; project memory travels via the project
repo. A repo not yet opted in falls back to Claude Code's hidden native default
(`~/.claude/projects/<slug>/memory/`) — invisible and non-transferable, exactly the state
this standard eliminates (see the error path in `SKILL.md`).

## Axis 1 — layer: global vs project

| Layer | Lives at | Travels via |
|---|---|---|
| **Global** | dotfiles-managed memory, symlinked into `~/.claude/` | the dotfiles repo |
| **Project** | `<repo>/.claude/memory/`, **git-tracked** | the project repo |

The layout requirement itself (a tracked `.claude/memory/` in the repo tree) is part of the
repo-meta-structure standard; this taxonomy owns what goes where and why.

## Axis 2 — loading: always-on vs situational

- **Always-on:** each layer's `MEMORY.md` index — a concise one-line-per-file index
  (each line `- [Title] → topic-file.md — hook`, a markdown link to the topic file plus a
  short hook), loaded every session.
- **Situational:** topic files behind the index — freeform markdown, one theme each,
  self-standing — pulled in only when relevant, the same on-demand shape as a skill.

## Axis 3 — kind: memory vs rules vs skills

| Kind | Holds | Loaded |
|---|---|---|
| **Memory** | Facts, state, decisions-as-record | Index always; topics situationally |
| **Rules** | Path-scoped standing directives | When matching files are in play |
| **Skills** | Invocable procedures | On invocation |

Triage test: *is it a fact* → memory; *is it a directive tied to certain files* → rule;
*is it a procedure you run* → skill. Specs and decisions are none of these — they graduate
to `docs/` / ADRs, with at most a one-line pointer in memory.

Directive-shaped memory (instructions hiding in topic files, silently not always-on) is a
curation concern: the triage routes directives to CLAUDE.md/rules — never a compliance row,
because judging it requires reading content.

## Birth rule — one hot-path question

**Secret / live-op?** (credentials, DSNs, live URLs) → `_meta/operations/`, untracked —
**never memory**. Everything else → the **project layer**: write a topic file under
`<repo>/.claude/memory/`, add one index line, commit with the repo.

That is the entire write-time decision. No global-vs-project agonizing at birth — a
global-worthy fact landing in project memory is fine; curation routes it later.

## The promotion mechanism

Promotion happens at curation, never automatically:

1. During a curation pass, a project memory proves generalizable across projects.
2. Distill it; write it to the global layer; add its global `MEMORY.md` index pointer —
   **only if it fits the index cap** (if not, prune/merge the global index first);
   prune the project copy.
3. The audit checks only that the *structure* exists (tracked memory dir, index) — it
   never judges content.

## v1 defaults — approved 2026-07-02

Each default below is explicitly marked. Position: ship with stated defaults, revise on
evidence.

1. **Curation cadence** — `accepted` (owner, 2026-07-02). Triggered by project boundaries
   (wrap-up / handoff moments), not a calendar. Revisit only if memory demonstrably rots
   between boundaries.
2. **Limits** — `accepted` (owner, 2026-07-02). Hard-cap the always-loaded index at ~1
   screen (~40 lines); **no cap** on lazily-loaded topic files. The cap is a promotion
   gate, not tooling: measure whether index bloat actually occurs before building
   enforcement for it.
3. **Rules vs skills vs memory** — `accepted` (owner, 2026-07-02). The Axis 3 triage above
   is the criterion.
