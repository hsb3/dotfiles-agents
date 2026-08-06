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

### Backlog card metadata

Four fields, each carrying one axis and no other. Overlap is what made them useless before.

| Field | Axis | Rule |
| --- | --- | --- |
| `type` | what kind of change | one of `bug feature task chore docs spike`; validated by Backlog.md |
| `priority` | how urgent | High / Medium / Low |
| `label` | **where** the work lands | **exactly one** area + **at most one** signal — never more |
| `milestone` | **which outcome** it serves | one of the active outcome milestones |

Areas: `primitives` `assembly` `distribution` `gates` `harness` `evals` `governance`.
Signals: `decision` (blocked on or produces an owner ruling), `on-hold` (parked on purpose).
The two signals are mutually exclusive. A card that seems to need two areas is two cards.

**`make backlog-labels` enforces this, because Backlog.md does not.** The tool validates
`types` and `statuses` against `backlog/config.yml` but silently accepts *any* label —
`-l whatever` just works, and the config's `labels:` list is only an autocomplete hint.
That gap is how the backlog reached 17 ad-hoc labels, 12 of them used exactly once, while
the two labels config actually declared went unused. Adding a label means adding it to
`backlog/config.yml` **and** to `AREAS`/`SIGNALS` in `scripts/check_backlog_labels.py`;
the gate cross-checks the two and goes red if either side drifts alone.

**Statuses are `To Do → Up Next → In Progress → Done`.** `Up Next` is the committed queue:
work that is picked, not merely filed. Promoting a card into it is a scheduling decision,
so leave it to the owner unless asked. Statuses cannot be set via `backlog config set` —
the CLI refuses and directs you to edit `backlog/config.yml` directly, which is sanctioned
(the "never edit directly" rule covers task/draft/document/decision/milestone markdown,
not the project config).

**Milestones are outcomes, not buckets** — each states a condition the repo reaches, so it
can actually be closed. A milestone whose tasks are all Done auto-reports as completed;
archive it, and if its body still carries an unchecked commitment, convert that into a task
first rather than letting it disappear with the milestone.

**Gotcha: `backlog task list -m` matches milestone *titles*, not IDs.** `-m m-1` returns
"No tasks found" with no error even when six tasks carry `milestone: m-1`; `-m "Measured"`
(any distinctive substring of the title) works. Assignment via `task edit -m m-1` does take
the ID, so the two commands disagree. Trust `backlog milestone list` for the counts.

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
