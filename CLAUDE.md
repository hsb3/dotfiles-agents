# CLAUDE.md — dotfiles-agents (agent-facing digest)

Claude Code marketplace of coding-agent extenders, assembled from `primitives-core/` into
plugin bundles. Clean-room rebuild to the 0007 lineup — Claude-Code-only, fresh history.

## Task interface

`make ci` is canonical (`make help` lists targets). CI runs `make ci` on every PR into `dev`.
It is `check` (roster↔disk drift) + `build-check` (marketplace regen drift) + `test`
(stdlib-only unit tests).

## Source-of-truth rules

- **`primitives-core/` is the only place a primitive is edited.** The `dist/claude-code/`
  lane (`plugins/`, `marketplace.json`, `PLUGINS.md`) is **generated** by
  `scripts/gen_marketplace.py`; never hand-edit it. Change the source, then `make build`.
- **Generated artifacts have a regen script + a `--check` drift guard.** Every generator is
  deterministic (stable ordering, no clocks/random) so `--check` never false-fails. Add new
  generated artifacts the same way; `make ci` must run their `--check`.
- **`primitives-core.yaml` (the roster) is the manifest** — the drift guard and the assembler
  read it, not a directory listing. Every roster entry needs the full schema
  (see `primitives-core/README.md`); `origin: sourced` requires non-null `upstream` + `ref`.
- **`primitives-core/` is self-authored only** (ADR 0015). Third-party items are recorded by
  reference in `externals.yaml`, never copied in.
- **Tests are stdlib-only** (`python3 -m unittest`) — zero install is an invariant. Fixtures
  live under `tests/` tempdirs, never under `primitives-core/` (the roster guard flags orphans).

## Governance

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
