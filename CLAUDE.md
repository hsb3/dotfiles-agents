# CLAUDE.md — dotfiles-agents (agent-facing digest)

Claude Code marketplace of coding-agent extenders, assembled from `primitives-core/` into
plugin bundles. Clean-room rebuild to the 0007 lineup — Claude-Code-only, fresh history.

## Task interface

`make ci` is canonical (`make help` lists targets). CI runs `make ci` on every PR into `dev`.
It is the entry-gate floor (identity · tests · provenance · hook-layout) + `check`
(roster↔disk, provenance manifest) + `symlinks` (assembly lint, ADR 0017) + `flow`.

## Source-of-truth rules

- **`primitives-core/` is the only place a primitive is edited.** Root `plugins/<id>/` are
  hand-authored thin symlink assemblies over it (ADR 0017: `plugin.json`/`hooks.json`/bundle
  READMEs regular files, everything else symlinked; root `.claude-plugin/marketplace.json`
  lists them; `make symlinks` lints). **Nothing generated is tracked** — the dist lanes and
  their generators retired with task-3; `gen_opencode.py` + `translation.yaml` remain for
  install-time opencode generation (task-4).
- **If something must be generated, it is generated at install/run time, never tracked**
  (ADR 0017). A tracked artifact needing a regen step is a design smell now; any generator
  kept (e.g. `gen_opencode.py`) stays deterministic (stable ordering, no clocks/random).
- **`primitives-core.yaml` (the roster) is the provenance manifest** — the drift guard reads
  it, not a directory listing. Schema: id/type/source/origin/disposition/targets/requires
  (see `primitives-core/README.md`); `origin: sourced` requires non-null `upstream` + `ref`.
  Plugin membership is NOT a roster field — membership is the symlink assemblies.
- **`primitives-core/` is self-authored only** (ADR 0015). Third-party items are recorded by
  reference in `externals.yaml`, never copied in.
- **Tests are stdlib-only** (`python3 -m unittest`) — zero install is an invariant. Fixtures
  live under `tests/` tempdirs, never under `primitives-core/` (the roster guard flags orphans).

## Task system

**Backlog.md is the task system** (backlog decision-1): tasks, drafts, decisions, and
milestones live in `backlog/` — `backlog board` for the live view, `backlog task list
--plain` for agents. **GitHub issues are bug-report intake only**; a reported bug gets a
backlog task when planned. PRs into `dev` never auto-close issues (auto-close fires only on
the default branch) — close bug issues by hand after the fix merges. The backlog CLI runs
with `auto_commit: false`; commit its file writes like any other edit. Task cards meet the
decision-7 minimum standard (cold-readable description, verifiable ACs, resolving
references, status truth); edit task files by hand, not via the CLI's write commands, and
repair any non-conforming card in the PR that touches it.

## Governance

Contributor SOP (the human-facing distillation of this digest): [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md).

Branch off `dev`, PR into `dev`. `main` is CI-published and off-limits (publish-only). Never
merge PRs or commit to the default branch. Keep changes surgical and match existing style.
Get the owner's approval before major information-architecture changes (moving/renaming
top-level structures or reshaping the roster).

**Never check out `main` locally** — publishing is CI-only (`.github/workflows/publish.yml`),
so a local `main` has no purpose; checking it out turns `dev`'s ignored residue into untracked
noise (its tree has no `.gitignore`). Inspect the published surface with
`git show origin/main:<path>`, or `git worktree add ../dotfiles-agents-main origin/main` for a
full checkout (remove the worktree after).

## Where things are

- `docs/FLOW.md` + `flow.yaml` — the repo-flow DAG: the home of every part and the edges
  between them, enforced by `make flow`. A new top-level path must claim a home there.
- `docs/decisions/` — ADR mirrors (the dev/main rule).
- `_meta/HANDOFF.md` — current build state and the rebuild deliverable map (D1–D8).
- `_meta/` is a tracked working desk; `_meta/operations/` is the only untracked part (secrets).
