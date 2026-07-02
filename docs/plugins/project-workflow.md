---
title: project-workflow plugin — user guide
status: active
created: 2026-07-02
---

# project-workflow — user guide

End-user documentation for the `project-workflow` Claude Code plugin (v0.1.0): what it
bundles, how to install it, what to say to trigger each capability, and what each one
produces. For the harness-agnostic *process* behind the core skills, read the SOPs in
[`docs/sops/`](../sops/README.md); this page documents the *runnable* side.

## What it is

One plugin that covers running a software project end-to-end:

- **Repo standards** — a canonical layout standard, a read-only compliance audit, and an
  additive-only scaffold that fills the gaps.
- **Board operations** — stand up a GitHub Project (v2) board, run weekly triage, and
  produce status digests, with a subagent for snapshot-based analysis.
- **Planning** — turn intent into conformant issue bodies and source-grounded build plans.
- **Session continuity** — a durable handoff file so any session can be cleared safely.
- **Project docs & comms** — CLAUDE.md/AGENTS.md authoring, value-and-proof READMEs,
  architecture diagrams, and recurring status decks/briefings.

13 skills + 1 agent, all generated from `primitives-core/` (membership is the
`plugins: [project-workflow]` field in `primitives-core.yaml`). **Never edit the plugin
directory under `targets/` — fix the primitive and rebuild.**

## Install

```console
$ claude plugin marketplace add hsb3/dotfiles-agents
$ claude plugin install project-workflow@dotfiles-agents
```

(Or install from the `/plugin` menu inside Claude Code.) Updates: rebuild + push this
repo, then update the marketplace/plugin from `/plugin` again.

## How invocation works

Skills trigger two ways:

- **Automatically** — Claude matches your request against each skill's description
  ("triage the backlog", "wrap up", "write me an issue" …). The trigger phrases listed
  below are examples, not magic words.
- **Explicitly** — `/project-workflow:<skill>` (e.g. `/project-workflow:handoff init`).

The `board-analyst` agent is not invoked directly; Claude launches it as a subagent
during board triage (or when you hand it a `board-snapshot.json`).

## The lifecycle at a glance

| Stage | You say | Skill(s) |
|---|---|---|
| Stand up / check a repo | "run the compliance audit" → "fill the audit gaps" | `repo-compliance-audit` → `mise-en-place-scaffold` |
| Layout / memory questions | "what's the standard for _meta?", "where does this memory go?" | `repo-meta-structure`, `memory-taxonomy` |
| Stand up the board | "set up a project board" | `github-project-board` |
| Weekly triage | "run board triage" | `board-triage` (+ `board-analyst`) |
| Status rollup | "board status", "weekly digest" | `board-reporting` |
| Plan work | "write me an issue", "plan this out" | `planning-desk` |
| End a session | "wrap up", `/project-workflow:handoff` | `handoff` |
| Project docs | "fix my CLAUDE.md", "refresh the README", "architecture diagram" | `agent-dot-md-authoring`, `readme-value-and-proof`, `diagrams` |
| Briefings & decks | "morning briefing", "board deck", "comms package" | `comms` |

## Component reference

### Repo standards

**repo-meta-structure** — the canonical layout standard: `_meta/` taxonomy
(archive/briefings/plans/operations/research + HANDOFF.md), tracked-vs-local `.claude/`
layout, `.github/` template set, root files, gitignore conventions, planning-doc
frontmatter. Reference-only: it answers "what is the standard for X"; it never audits or
scaffolds. Per-repo variance is declared in `_meta/mise-en-place.yml`, never as a silent
exception. Ships the checklist (`META-/CLAUDE-/GH-/ROOT-/IGNORE-/AVOID-/PLANS-xx` IDs)
and file assets the two skills below consume.

**memory-taxonomy** — the companion reference for agent memory: global dotfiles layer vs
project git-tracked `.claude/memory/`, always-on index vs situational topic files, memory
(facts) vs rules (directives) vs skills (procedures), the secret-only birth rule, and
promotion at curation time. Reference-only; the doing lives in the `cc-project-memory`
CLI and the scaffold.

**repo-compliance-audit** — read-only pass/gap audit against both standards above. Runs
the bundled `scripts/audit.py` from the repo root and presents its
`ID | Area | Verdict | Detail` table plus `N pass / M gap` summary verbatim. It **never
writes** to the audited repo and defines no checks of its own — rows come from the sibling
standards' checklists. Gaps are information, not a CI failure.

**mise-en-place-scaffold** — fills the gaps the audit found. `--plan` (default) prints
planned creations/conflicts and writes nothing; `--apply` creates only the planned items;
`--init-manifest` writes the variance template. **Additive-only**: it never overwrites,
merges, edits, deletes, or moves an existing file — a differing file is reported as a
CONFLICT and left byte-identical. It also never provisions GitHub-side objects (that's
`github-project-board`) and never authors README/CLAUDE.md content (see the docs skills).

Typical loop: **audit → scaffold → re-audit**.

### Board operations

All four components share one field model, one Impact×Effort rubric, and one changeset
contract, defined in `github-project-board`. Prereq for all: `gh` authenticated with the
project scope (`gh auth refresh -s project`).

**github-project-board** — stand up and operate a single GitHub Project (v2) board:
create the project and fields (including ITERATION), edit single-select options without
orphaning items, seed values and sub-issue/blocked-by dependencies, run the weekly
cadence. Knows what is scriptable via `gh`/GraphQL vs genuinely UI-only (views and
workflows), and documents the export → analyze → apply loop the other board components
run.

**board-triage** — the weekly ranking pass. Exports a snapshot, finds
unranked/blank/stale items, judges them against the repo's plans and issue bodies, and
emits a **diff-only changeset TSV** (`issue<TAB>field<TAB>value`). Applying is dry-run
first, idempotent, and writes only differing cells. Items lacking context are left blank
and flagged — "honest blank beats a fabricated rank."

**board-reporting** — a written digest from the snapshot: counts by
Status/Priority/Workstream, in-progress and blocked lists, target slippage, what landed
since the last snapshot. Read-first — it reports what the board says and changes nothing,
except optionally posting the project's native status-update banner, and only after you
confirm. The digest can feed a deck or audio brief — in this plugin that's `comms`.

**board-analyst** (agent) — the judgment half of the loop when it runs as a subagent:
reads a snapshot, applies the rubric, writes the changeset TSV plus per-issue rationale
and a skipped list. Hard boundary: it **never applies changes to the board**; applying is
a deliberate human/script step.

The three helper scripts behind the loop (`board-export.py`, `board-fields.py`,
`board-apply.py`) ship in the `github-project-board` skill's `scripts/` directory —
`$CLAUDE_PLUGIN_ROOT/skills/github-project-board/scripts/` in an installed plugin. They
are stdlib + `gh` only; no install step.

### Planning

**planning-desk** — a source-grounded planning desk under `_meta/plans/`: per-item
`issue-body.md` (the contract) + `plan.md` (build detail with claims cited to
`path:line`), driven through a draft → review → fix → reconcile loop, plus a bundled
toolkit of seven dependency-free governance scripts (conformance, coverage, reconcile,
sequence, deps-suggest, sync-bodies, evidence-audit). Enforces
deliverables/criteria/parallelism — never timelines. Staging on the desk is free; creating
or editing live GitHub issues always requires your confirmation. The desk holds detail and
rationale; the board stays the single source of truth for work state.

### Session continuity

**handoff** — maintains the session-handoff file (`_meta/HANDOFF.md`, or root
`HANDOFF.md` / `.claude/HANDOFF.md`) so a brand-new session picks up cold: current state,
in-flight work, decisions with whys, gotchas. `/project-workflow:handoff init` creates
the file in a project that lacks one. Edits are surgical and in-place; target ~150 lines;
never contains secrets. The exit test: "what do I still know that isn't written down?" —
the answer must be nothing.

### Project docs & comms

**agent-dot-md-authoring** — write a CLAUDE.md/AGENTS.md from scratch (8-section
skeleton) or audit an existing one (scored x/10 against a checklist, with line-referenced
failures). Verifies that every command, path, and port it cites actually exists in the
repo.

**readme-value-and-proof** — rewrite a README as an honest, user-centric pitch (why it
exists / what you get / what it's not / roadmap) backed by **real screenshots captured
from the running app** — never mockups. Needs a runnable app and headless Chromium via
Playwright.

**diagrams** — architecture/infrastructure diagrams via Python's `diagrams`
(mingrammer) library; AWS/Azure/GCP/K8s/on-prem/generic nodes; renders png/svg/pdf/jpg.
Needs `pip install diagrams` + Graphviz. Keeps its own memory file of rendering
learnings and improves across uses.

**comms** — Henry's recurring communication deliverables (morning briefing, EOD wrap-up,
weekly planning briefing, advisor board readout, client product overview) as a deck plus
optional audio, landing in a dated `_meta/briefings/<date>-<slug>/` folder with
provenance. Composes rather than replaces: internal decks use the **deck-builder MCP**,
external decks the **pptx-henry** skill, audio the **audio MCP**; the EOD wrap-up runs
`handoff` first and builds from the refreshed file. House rules: lead with the decision,
never round up, numbers live in systems and the deck points to them.

## Prerequisites by component

| Component | Needs |
|---|---|
| board skills + agent | `gh` CLI authed with project scope (`gh auth refresh -s project`); helper scripts bundled (stdlib-only) |
| planning-desk | `gh` authed; GitHub-backed repo; run from the main working tree (not a worktree) |
| diagrams | Python `diagrams` package + Graphviz |
| readme-value-and-proof | runnable app; Playwright/headless Chromium |
| comms | deck-builder + audio MCP servers (local); `pptx-henry` skill for external decks — none ship in this plugin |
| everything else | none beyond the repo itself |

## Safety guarantees (summary)

| Component | Guarantee |
|---|---|
| repo-compliance-audit | never writes to the audited repo |
| mise-en-place-scaffold | additive-only; plan-first; never touches an existing file |
| board-analyst | never applies changes to the board |
| board-apply step (triage) | dry-run by default; idempotent; diff-only |
| board-reporting | changes nothing; banner post only on explicit confirmation |
| planning-desk | live issue create/edit only with owner confirmation |
| handoff | no secrets, ever |

## Relationship to the SOPs

The process layer is harness-agnostic and lives in [`docs/sops/`](../sops/README.md);
this plugin is its Claude Code delivery:

| SOP | Delivered by |
|---|---|
| `milestones-and-board.md` | github-project-board (+ board-triage, board-reporting) |
| `issues-and-plans.md` | planning-desk |
| `session-continuity.md` | handoff |

The remaining components (repo standards, docs, diagrams, comms) have no SOP yet — the
skill text is currently their only process documentation.
