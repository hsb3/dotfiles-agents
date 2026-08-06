---
id: TASK-031
title: >-
  Marketplace front door: make the 20 plugins discoverable from the default
  branch
status: In Progress
assignee:
  - '@claude'
created_date: '2026-08-06 18:41'
updated_date: '2026-08-06 19:17'
labels:
  - docs
  - marketplace
  - gates
dependencies: []
references:
  - README.md
  - .claude-plugin/marketplace.json
  - plugins/foreman-kit/README.md
  - plugins/dataviz/README.md
  - scripts/check_symlinks.py
  - >-
    backlog/tasks/task-28 -
    check_symlinks-enforce-the-standalone-README-symlink-convention.md
priority: high
type: docs
ordinal: 500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Someone landing on the repo's default branch (`main`, the published consumer surface) has no
way to see what plugins exist, what each one is for, or which one to install. The front door
is a wall of prose, and it is wrong.

Verified 2026-08-06 against `origin/main` (tip `19f1df5`) and `dev` (`e8cf954`) — `README.md`
is byte-identical on both:

1. **The lineup paragraph is stale.** It says "eleven standalone one-skill plugins" and lists
   11. There are **16** (missing: `comms`, `iterm2`, `mise-en-place-scaffold`,
   `readme-value-and-proof`, `repo-meta-structure`). 20 plugins ship; the README names 15.
2. **No catalog, no links.** Every plugin has a good `plugins/<id>/README.md` (bundles as
   regular files, standalones symlinked to the skill's own README) and the root README links
   to none of them. There is no table, no per-plugin one-liner, no "which do I want".
3. **Most of the README does not apply on `main`.** The Layout and Build-interface sections
   document `primitives-core/`, `scripts/`, `tests/`, `backlog/decisions/`, `flow.yaml`,
   `translation.yaml`, `primitives-core.yaml`, and `make ci` — **none of which exist in the
   published tree** (`main` carries only `.claude-plugin/`, `.gitignore`, `README.md`,
   `plugins/`). A visitor is handed contributor instructions for a tree they cannot see.
4. **The in-product surface is degraded.** `claude plugin` lists plugins by their
   `description`. `github-project-board`'s is truncated mid-word in both
   `plugin.json` and `marketplace.json` ("…sliced into ma…"), and descriptions run 158–956
   chars with the distinguishing detail buried past the first line.
5. **Two hand-authored surfaces already drift with nothing to catch it.**
   `mise-en-place-scaffold`'s description differs between its `plugin.json` and
   `marketplace.json`; `marketplace.json`'s `metadata.description` says "sixteen standalone"
   while the README says eleven. No gate reads either.
6. **The GitHub About box is empty** — no repo description, no topics. It is the literal first
   thing a visitor reads.
7. **The published opencode install is broken.** The README tells a visitor to
   `git clone https://github.com/hsb3/dotfiles-agents && cd ... && scripts/install_opencode.sh`.
   A clone lands on the default branch (`main`), and `publish.yml` lifts only `plugins/`,
   `.claude-plugin/marketplace.json`, `README.md`, and `.gitignore` -- there is no `scripts/`,
   no `translation.yaml`, no `Makefile`. The documented command cannot run as published.
8. **Internal vocabulary and IDs leak to consumers.** "desk sets", "kits", "primitive",
   "assembly", "laydown", "ADR 0017", "(task-4)", `.claude/HANDOFF.md`, `backlog/decisions/`:
   none defined, none resolvable on `main`. Roughly two-thirds of the published README
   (7 of Layout's 9 rows, all of Build interface, both Governance links, half of Install)
   describes a tree the reader cannot see.

## Design

Consumer-first inverted pyramid in one README (not two), plus a drift guard so the catalog
cannot rot the way the prose did.

### A. `README.md` restructured — sections in this order

1. **What this is** — two sentences: a Claude Code marketplace of coding-agent extenders;
   20 plugins, install by name.
2. **Install** — the three lines a visitor needs first (`claude plugin marketplace add
   hsb3/dotfiles-agents`, then `claude plugin install <name>@dotfiles-agents`), opencode
   laydown after. **The opencode block must be executable as published**:
   either pin the clone to the source branch (`git clone --branch dev ...`) or add
   `scripts/install_opencode.sh` + `translation.yaml` to `publish.yml`'s lift map. Prefer the
   branch pin — widening the published surface needs the owner's sign-off. Verify by running
   the block against a fresh clone of the default branch, never from a `dev` working tree.
3. **Start here** — a task-oriented chooser, 6–10 rows, "I want to … → install `<plugin>`".
   Written from the user's goal, not the plugin's name. Examples: delegate work across
   subagents and keep sessions clearable → `foreman-kit`; ship a release under a documented
   repo standard → `code-desk`; make a chart → `dataviz`; author or debug a Claude Code
   skill/hook/agent → `claude-code-expertise`; configure settings, permissions, hooks →
   `claude-code-config`; research a technology choice with citations → `tech-eval-research`.
4. **Catalog** — one row per plugin, all 20, sorted bundles-then-standalones then A–Z:

   | Plugin | Kind | What it does | Contents |
   |---|---|---|---|
   | [`foreman-kit`](plugins/foreman-kit/README.md) | kit | Tiered delegation agents + session-discipline hooks: size a task, dispatch to the right model tier, keep every session clearable. | 6 skills · 4 agents · 4 hooks |

   Rules: the name cell is a relative link to `plugins/<id>/README.md` (resolves on `main`
   and on GitHub); the blurb is **one sentence, ≤ 140 chars**, hand-written for scanning, not
   pasted from `description`; the Contents cell is counts, not names.
5. **Bundles vs standalone** — short: 4 multi-skill assemblies (`code-desk`, `diagrams`,
   `foreman-kit`, `obsidian-toolkit`) and 16 one-skill plugins; cross-desk items ship
   standalone, never inside a bundle; a dual-homed skill installed both ways loads once.
6. **Contributing / how it is built** — reduced to a short section that links out with
   **branch-qualified absolute URLs** (`https://github.com/hsb3/dotfiles-agents/tree/dev/…`)
   to CLAUDE.md, `.github/CONTRIBUTING.md`, `primitives-core/`, and the decisions dir. This is
   what fixes problem 3 without introducing a second README to maintain.

### B. In-product descriptions

Repair `github-project-board` (write the real sentence; it is truncated at the source in
`plugins/github-project-board/.claude-plugin/plugin.json`) and re-sync
`mise-en-place-scaffold` so `plugin.json` and `marketplace.json` agree. Front-load every
description so the first ~100 chars stand alone when the picker truncates — full rewrite of
all 20 is out of scope; fix the broken ones and the lede where it is buried.
Refresh `marketplace.json`'s `metadata.description` to match the new counts.

### C. Drift guard — `scripts/check_catalog.py`, wired into `make check`

Hand-authored README, machine-checked (ADR 0017: nothing generated is tracked, so this is a
guard, not a generator). Checks, each with its own failure message:

1. Every plugin in `marketplace.json` has exactly one catalog row; no row names a plugin that
   is not in the marketplace.
2. Every link in `README.md` either is an absolute URL or resolves to a path that exists
   **inside the published surface** (`plugins/`, `.claude-plugin/`, `README.md`) — this is
   what stops the README from pointing at `dev`-only paths again.
3. For each plugin, `plugin.json.description == marketplace.json` entry description.
4. No description ends in `…` or `...` (truncation guard).

Wire into `make check`, **not a new CI job** — dev's required checks are pinned by job name,
so the drift-guards job (already running `make check symlinks flow`) picks it up for free.
Tests in `tests/test_check_catalog.py`, stdlib `unittest`, fixtures in tempdirs.

### D. GitHub About box

Set the repo description and topics (`gh repo edit hsb3/dotfiles-agents --description … --add-topic claude-code …`). Owner's call on wording; propose one.

## Constraints

- Keep it to `README.md` + `scripts/` + `tests/` + the plugin manifests. A new top-level path
  (e.g. a separate `CATALOG.md`) must be declared in `flow.yaml` or `make flow` fails the PR.
- Content change on published files means a **version bump** in both
  `plugins/<id>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` for any
  plugin whose description changes; keep `ensure_ascii=True` if editing those programmatically.
- Related but separate: TASK-28 adds a standalone-README symlink check to
  `check_symlinks.py`. Keep the catalog checks in their own script; do not merge the two.
- Restructuring the repo's front door is an information-architecture change: get the owner's
  sign-off on the section order and the chooser wording before writing all 20 rows.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README.md opens with what-this-is, install, and a task-oriented chooser before any contributor content
- [ ] #2 README.md contains a catalog table with exactly one row per plugin in .claude-plugin/marketplace.json (20 today), each row linking to plugins/<id>/README.md
- [ ] #3 Every relative link in README.md resolves to a path present in the published surface (plugins/, .claude-plugin/, README.md) — verified against origin/main's tree, not just dev's
- [ ] #4 Contributor/build content is a short section that links to dev-branch paths with absolute branch-qualified URLs instead of documenting paths absent from main
- [ ] #5 github-project-board's description is a complete sentence in both plugin.json and marketplace.json, and no plugin description ends in a truncation ellipsis
- [ ] #6 plugin.json and marketplace.json descriptions match for all 20 plugins, and marketplace.json metadata.description states the current bundle/standalone counts
- [ ] #7 scripts/check_catalog.py fails on: a plugin missing from the catalog table, a catalog row for an unknown plugin, a README link that does not resolve in the published surface, a plugin.json/marketplace.json description mismatch, and a truncated description
- [ ] #8 check_catalog.py runs inside `make check` (no new CI job name) and tests/test_check_catalog.py covers each failure mode plus the passing shape with stdlib unittest and tempdir fixtures
- [ ] #9 Version bumped in both plugin.json and marketplace.json for every plugin whose published content changed
- [ ] #10 The GitHub repo description and topics are set (or a proposed wording is recorded for the owner's approval)
- [ ] #11 make ci green
- [ ] #12 The opencode install block in README.md runs end to end against a fresh clone of the default branch — verified by running it, not by reading it
- [ ] #13 No undefined internal vocabulary or bare internal identifiers (ADR numbers, task IDs, backlog/ or .claude/ paths) remain on the consumer surface without a resolvable link or a plain-English gloss
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Branch docs/marketplace-front-door off dev (done).
2. Contract = this task's design + the 13 acceptance criteria. Gate = make ci green AND python3 scripts/check_catalog.py exit 0.
3. Architecture C (flat fan-out), three workers on disjoint file ownership, no worktrees:
   A README.md rewrite to a fixed section skeleton the session owns (opus builder);
   B scripts/check_catalog.py + tests/test_check_catalog.py + Makefile wiring (sonnet builder);
   C manifest repairs: github-project-board truncated description, mise-en-place-scaffold plugin.json/marketplace.json mismatch, metadata.description counts, version bumps (sonnet builder).
4. Session reconciles the three slices, runs the gates itself, then evaluate (rubric-panel) -> triage -> refine cycles until convergence or budget 3.
5. PR into dev; publish to main after merge so the fixed front door actually reaches the default branch.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
**L1 contract amendments after the three-judge review (2026-08-06).** Recorded here because they change how two acceptance criteria are satisfied, not what they require.

- **AC #3** says links are verified against `origin/main`'s tree. `scripts/check_catalog.py` cannot do this from a `dev` checkout — it would need network access to a remote ref, which the offline local gates deliberately avoid. The criterion is satisfied by manual verification instead: two independent reviewers each confirmed all 20 relative links are present in `git ls-tree -r --name-only origin/main` (tip `19f1df5`). The guard's contribution is the working-tree half. Anyone re-running this check must do the `origin/main` half by hand.
- **AC #12** says the opencode block runs against a fresh clone of the default branch. The repo is **private** (`gh repo view --json isPrivate` -> true), so the clone succeeds only with credentials; an unauthenticated visitor gets a 404 on everything, including all three absolute `tree/dev/` URLs in the README. Two reviewers ran the block end to end with credentials and it exits 0. The unauthenticated-visitor audience the Problem statement describes does not exist until the repo is made public — worth knowing before anyone treats a 404 as a broken link.
- **AC #10** escape hatch taken: proposed About-box wording recorded below for the owner's approval rather than applied, since repo metadata is outward-facing.

  - description: `A Claude Code plugin marketplace: 20 installable extenders — delegation agents, session-discipline hooks, and skills for research, diagrams, decks, and repo standards.`
  - topics: `claude-code`, `claude-code-plugins`, `agent-skills`, `ai-agents`, `developer-tools`, `opencode`

**Findings routed out of scope, filed rather than absorbed:** TASK-032 (no gate ties published bytes to a version bump — the highest-cost uncaught mode in the repo, reproduced) and TASK-033 (the opencode laydown ships 25 of 34 skills and zero hooks, and the installer's cleanup trap deletes the exclusions record before the user can read it). TASK-031 adds only a one-sentence README disclosure for the latter; the fix belongs to TASK-033.
<!-- SECTION:NOTES:END -->

<!-- SECTION:DESCRIPTION:END -->
