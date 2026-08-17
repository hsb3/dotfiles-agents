# Agent Instructions for this repo

## Task interface

`make ci` is canonical and is what CI runs on every PR into `dev`. `make help` lists the rest.

## Source-of-truth rules

- **`primitives-core/` is the only place a primitive is edited**, and it is self-authored only
  (ADR 0015) — third-party items are recorded by reference in `externals.yaml`, never copied in.
- **Root `plugins/<id>/` are hand-authored thin symlink assemblies** over it (ADR 0017):
  `plugin.json`/`hooks.json`/bundle READMEs are regular files, everything else symlinked;
  `.claude-plugin/marketplace.json` lists them; `make symlinks` lints.
- **Nothing generated is tracked** (ADR 0017) — generate at install/run time instead. A tracked
  artifact needing a regen step is a design smell. Generators that remain (`gen_opencode.py`)
  stay deterministic: stable ordering, no clocks, no random.
- **`primitives-core.yaml` (the roster) is the provenance manifest** — the drift guard reads it,
  not a directory listing. Schema in `primitives-core/README.md`; `origin: sourced` requires
  non-null `upstream` + `ref`. Plugin membership is NOT a roster field — membership is the
  symlink assemblies.
- **Tests are stdlib-only** (`python3 -m unittest`) — zero install is an invariant. Fixtures live
  in `tests/` tempdirs, never under `primitives-core/` (the roster guard flags orphans).

## Governance

Contributor SOP: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md). Traps this repo has
already hit — how to read `make ci`, which gates are CI-only, what `flow.yaml` breaks:
[`docs/gotchas.md`](docs/gotchas.md).

Branch off `dev`, PR into `dev`. Never merge PRs or commit to the default branch. `main` is
publish-only (CI, `.github/workflows/publish.yml`) and is never checked out locally — a
PreToolUse hook blocks it. Read the published surface with `git show origin/main:<path>`, or
`git worktree add ../dotfiles-agents-main origin/main` (remove the worktree after).

Keep changes surgical and match existing style. Get the owner's approval before major
information-architecture changes (moving/renaming top-level structures, reshaping the roster).

GitHub issues are bug intake only; planned work lives on the Kaneo board (see "Task tracking").

### Branch hygiene

Merge or abandon a branch **within the session that opened it** — parked work is invisible to
later sessions and dies with the branch. Delete after merge (`--delete-branch`, or a separate
`git push origin --delete` if the tree is dirty, since the flag switches branches). Before
deleting any branch, `git rev-list --count origin/dev..<branch>`; nonzero means diff each
changed file against `dev` before calling the work superseded. `dev-legacy` is a deliberate
pre-restructure archive — never delete it.

## Task tracking

The tracker is the **Kaneo board** (project `DFA` / "dotfiles-agents", workspace `hsb3`) — a
live board, not files in this tree. Work it through the `kaneo` plugin's skill: the claim
ritual, the level rules, and how decisions get recorded are that skill's law, not this page's.

**The session handoff is a board task too**: the one labeled `HANDOFF` in the `Document` lane
(DFA-233). Read it at session start; at session end rewrite its **description** in place under
the `handoff` skill's content rules. **No handoff file is tracked in this tree, and there is no
handoff branch — never create either.**

`handoff-freshness-guard` knows this via the `handoff: {mode: external, …}` block in
`.claude/atelier.local.md` (gitignored, per-project): it stats `.claude/handoff.stamp` instead
of searching for a handoff file. **Update the board task first, touch the stamp last** — the
guard reads the stamp's age, never the board's content, so an early touch certifies a handoff
that has not happened. No stamp yet in a fresh clone means the first manual `/compact` is
refused until `/handoff` runs, which is the intended answer. Needs atelier ≥ 0.15.0.

Config is the five `KANEO_*` values in `.claude/settings.local.json` (gitignored — they carry a
credential); missing or wrong, ask the owner rather than guessing. Never create a
`backlog.md`, a `TODO` file, or any other in-repo task list — file it on the board.
