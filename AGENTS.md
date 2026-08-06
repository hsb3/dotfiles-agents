# Agent Instructions for this repo

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

### Branch hygiene

**Merge or abandon a branch within the session that opened it.** Work parked on an unmerged
branch is invisible to every later session and is silently destroyed if the branch is deleted —
on 2026-08-06 deleting one such branch reverted a closed task to To Do while its shipped code
stayed live. Delete the branch immediately after merge (`--delete-branch`, or a separate
`git push origin --delete` if the working tree is dirty, since the flag switches branches).

**Before deleting any branch, check what it carries:** `git rev-list --count origin/dev..<branch>`.
Nonzero means unmerged commits — diff each changed file against `dev` before concluding the work
is superseded. A branch can show unmerged commits and still be redundant (renamed paths,
deliberately deleted files, an amended successor), so count alone decides nothing.

**The handoff rides one long-lived branch, `chore/handoff`.** At a session boundary:

```sh
git fetch origin && git checkout chore/handoff && git merge --ff-only origin/dev
```

`--ff-only` **refuses** if the branch still carries an unparked handoff update — that refusal is
the point, and it is the tripwire for the failure above. Write the update, PR into `dev`, merge
before the session ends, and leave the branch in place for next time.

`dev-legacy` is a deliberate pre-restructure archive — never delete it.

<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.48.0 -->

<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**For every user request in this project, run `backlog instructions overview` before answering or taking action.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:

- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD GUIDELINES END -->
