---
title: "dotfiles-agents — charter"
status: active
created: 2026-06-26
---

# dotfiles-agents — charter

The canonical page for this repo. **If anything anywhere disagrees with this page, this page wins; change it only here.**

## What this repo is

The git-tracked source of truth for **proven** *extenders* — anything that expands a coding agent's capability beyond toggling built-in config. It is **not** stowed; it is deployed by the distribution CLI that lives in `dotfiles`.

## Vocabulary

- **Extender** — the umbrella: any capability added to a coding agent.
- **Primitive** — the atomic unit. Four types only: **agent** (persona), **skill** (`SKILL.md`), **mcp** (server definition), **hook** (event script + config). *(Commands are not used — skills cover the same ground.)*
- **Distribution target** — a packaging form a primitive is rendered into for a tool: a **plugin** (Claude Code marketplace bundle) or a **raw primitive** (dropped into a tool's native dir).

**Governing rule:** one canonical source copy per primitive; copies are **generated** into targets by tooling, never hand-authored. Editing a target instead of the source is the drift bug this design exists to prevent.

## The four repos

| Repo | Job |
|---|---|
| `dotfiles` | machine config + the distribution CLI; reads this repo |
| **`dotfiles-agents`** (this) | proven primitives + assembled plugins; the only thing deployed |
| `dotfiles-agents-workbench` | unproven extenders; promotes *into* here through a gate; never deployed |
| `dotfiles-bootstrap` | clones + installs the content repos on a clean machine; verifies |

Acyclic: nothing depends on the workbench; this repo depends on nothing.

## Targets & portability

Priority: **Claude Code + opencode**. Third: **Claude managed agents** (CMA beta APIs). Per-primitive portability:

| Primitive | Claude Code | opencode | managed agents |
|---|---|---|---|
| skill | native | native (`~/.agents/skills/`) | `POST /v1/skills` (folder upload, SKILL.md at root) |
| agent | native | transform (frontmatter) | `POST /v1/agents` |
| mcp | render | render (`opencode.json`) | render (remote only) |
| hook | native | unsupported (CC-only) | unsupported |

A translation service renders each primitive into static per-target bundles under `targets/` at merge time; a CI drift guard keeps them current.

## Source of decisions

The full decision record and build plan live in the governance workspace at
`~/Documents/Claude/Projects/dotfiles-agents-cowork/_structure/` (`CANON.md` + `repository-technical-plan.md`) — kept out of this repo deliberately. This charter is the repo-local summary; CANON is the upstream record.

**Where any given doc belongs** — decisions vs execution vs state vs brainstorm — is mapped in [`governance-map.md`](governance-map.md): one canonical home per artifact type, and the rule that the Obsidian vault holds brainstorm/journal only.

## Process SOPs

Harness-agnostic standard operating procedures for running a software project (milestones & board, issues & plans, session continuity) live in [`docs/sops/`](./sops/) — the *process* layer that this repo's extenders (`github-project-board`, `planning-desk`, `handoff`) deliver.
