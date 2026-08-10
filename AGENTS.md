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

Contributor SOP: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md).

Branch off `dev`, PR into `dev`. Never merge PRs or commit to the default branch. `main` is
publish-only (CI, `.github/workflows/publish.yml`) and is never checked out locally — a
PreToolUse hook blocks it. Read the published surface with `git show origin/main:<path>`, or
`git worktree add ../dotfiles-agents-main origin/main` (remove the worktree after).

Keep changes surgical and match existing style. Get the owner's approval before major
information-architecture changes (moving/renaming top-level structures, reshaping the roster).

GitHub issues are bug intake only; planned work is Backlog.md tasks.

### Branch hygiene

Merge or abandon a branch **within the session that opened it** — parked work is invisible to
later sessions and dies with the branch. Delete after merge (`--delete-branch`, or a separate
`git push origin --delete` if the tree is dirty, since the flag switches branches). Before
deleting any branch, `git rev-list --count origin/dev..<branch>`; nonzero means diff each
changed file against `dev` before calling the work superseded. `dev-legacy` is a deliberate
pre-restructure archive — never delete it.

The handoff rides one long-lived branch, `chore/handoff`:

```sh
git fetch origin && git checkout chore/handoff && git merge --ff-only origin/dev
```

`--ff-only` **refuses** if the branch still carries an unparked handoff update — that refusal is
the point. Write the update, PR into `dev`, merge before the session ends, leave the branch.

### Backlog card metadata

Four fields, one axis each. `make backlog-labels` enforces the label rule, because Backlog.md
silently accepts any label.

| Field | Axis | Rule |
| --- | --- | --- |
| `type` | kind of change | `bug feature task chore docs spike` |
| `priority` | urgency | High / Medium / Low |
| `label` | **where** it lands | **exactly one** area + **at most one** signal |
| `milestone` | **which outcome** it serves | an active outcome milestone |

Areas: `primitives` `assembly` `distribution` `gates` `harness` `evals` `governance`.
Signals: `decision`, `on-hold` — mutually exclusive. A card needing two areas is two cards.
Adding a label means editing `backlog/config.yml` **and** `AREAS`/`SIGNALS` in
`scripts/check_backlog_labels.py`; the gate goes red if either side drifts alone.

Statuses: `To Do → Up Next → In Progress → Done`. `Up Next` is the committed queue — promoting
into it is the owner's scheduling call, so leave it alone unless asked. Statuses are edited in
`backlog/config.yml` directly (the CLI refuses and says so; the "never edit directly" rule below
covers task/draft/document/decision/milestone markdown, not the project config).

Milestones are outcomes, not buckets — each states a condition the repo reaches, so it can be
closed. Before archiving a completed milestone, convert any unchecked commitment in its body
into a task.

Avoid two sessions writing the backlog concurrently: a 2026-08-04 race invalidated the CLI's
index and looked exactly like a CLI defect.

**Gotcha:** `backlog task list -m` matches milestone *titles*, not IDs — `-m m-1` returns
nothing with no error; `-m "Measured"` works. `task edit -m m-1` does take the ID, so the two
disagree. Trust `backlog milestone list` for counts.

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
