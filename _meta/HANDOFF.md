# HANDOFF — dotfiles-agents clean-room rebuild

_The cold-start bridge. Source of record for the work order: GitHub epic
[hsb3/dotfiles-agents#111](https://github.com/hsb3/dotfiles-agents/issues/111); crew execution
runs on Multica DEV-33._

## 0 · Orientation

`dotfiles-agents` is a Claude Code marketplace of coding-agent extenders. It is being rebuilt
clean-room (same repo name/remote, **fresh git history**) to the 0007 lineup: two self-authored
bundles — **project-workflow** and **repo-standards** — plus one-skill standalone distribution.
Claude-Code-only; the prior multi-vendor translation surface (`targets/`, `scripts/translate.py`)
is dropped. `dev` = source, `main` = CI-published (publish-only, off-limits to hand commits).

## 1 · Current standing

**D1 (fresh-history base + `make ci` harness) built.** This tree is a single orphan-root
commit: the repo scaffold, the `make ci` task interface, and the regenerate + drift-guard
pattern, seeded with one primitive (`project-workflow` / `handoff`) wired end to end. Making
this commit the new `dev` root is an owner-gated integration step (Henry) — the crew does not
force-push `dev`. D2+ resume normal PRs into `dev` once the root is set.

## 2 · What D1 delivered

- Root layout: `primitives-core/{skills,agents,hooks}/`, `hooks/`, `docs/decisions/`,
  `scripts/`, `tests/`, `.github/workflows/`, `.claude/`, `_meta/`. No `targets/`, no
  multi-vendor translate config.
- `make ci` = `check` (roster↔disk drift, `scripts/check_roster.py`, ported as-is) +
  `build-check` (marketplace regen drift, `scripts/gen_marketplace.py --check`) + `test`
  (`python3 -m unittest`, stdlib-only). `smoke` is opt-in and out of `ci`.
- Generated artifacts: `plugins/<bundle>/` (assembled CC plugin dirs) and
  `.claude-plugin/marketplace.json`, both produced by `scripts/gen_marketplace.py` and
  drift-guarded by its `--check`. The generator is deterministic (no clocks/random).
- CI: `.github/workflows/ci.yml` runs `make ci` on `pull_request`, `permissions: contents: read`.

## 3 · Where to start next

- **D2/D3** — port the 11 bundle skill bodies into `primitives-core/skills/` and split them
  across project-workflow (5) / repo-standards (6); author the two nudge hooks; add each
  bundle to `plugins.yaml`; `make build` regenerates the marketplace.
- **D4** — port the standalone catalog (`skill-catalog.yaml` + `gen_standalone.py`) and add a
  `catalog` lane; the marketplace assembler already establishes the regen/drift pattern to fold
  it into.
- **D6** — the entry-gate machine floor (identity-neutrality lint, provenance conformance,
  hook-layout check) folds new lanes into `make ci`; the seams are intentionally absent now,
  not stubbed.

## 4 · Conventions & gotchas

- **Never hand-edit generated files** (`plugins/`, `marketplace.json`). Change the source, then
  `make build`. `make ci` fails on drift.
- **Roster is the manifest.** Every entry needs the full schema; `origin: sourced` needs
  non-null `upstream`+`ref`. Fixtures must not live under `primitives-core/` or the roster
  guard flags them as orphans.
- **Worktree provisioning:** the tree is self-contained for `make ci` (no untracked assets
  needed); `make smoke` (later) needs a live Claude Code install.

## 5 · Incident log

_(none yet)_
