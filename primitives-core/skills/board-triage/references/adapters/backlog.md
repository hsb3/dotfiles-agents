# Adapter — Backlog.md

Backend for the `board-triage` contract (SKILL.md §2) against a Backlog.md board: a
`backlog/` (or `.backlog/`) directory of markdown task files in the repo. The whole adapter
is one script that ships with this skill: `scripts/backlog_board.py`, stdlib only — it
shells out to the `backlog` binary, which already gives `--json` reads and per-field edits.

## Prerequisite

The `backlog` binary on PATH, and a board to point at. Backlog.md finds its board from the
working directory, so the adapter runs every call with cwd set to `--root` (default: the
current directory); no credentials are involved. `--root` that holds no board fails with
backlog's own `No Backlog.md project found` and exit 1.

Detected by a `.backlog/` or `backlog/` directory holding the board's `config.yml`.

## Key

The task **id** (`TASK-12`), shown as the `id` in `backlog task list --json`. Apply
re-resolves id → current field values from a fresh `task list` every run, so a stale
changeset cannot write to the wrong task. A task that is Done is not on the exported board,
so a row naming one is a `SKIP: not on this board`.

## Export

Replace `<board-triage-skill-dir>` with the absolute installed directory containing
board-triage SKILL.md. Run from the consuming project; plugin environment variables
are not required.

```bash
S="<board-triage-skill-dir>/scripts"
python3 "$S/backlog_board.py" export --root . --out board-snapshot.json
```

Prints `<n> items (<n> untriaged) -> board-snapshot.json`. Tasks in the last configured
status (the done lane) are left out; everything else is `state: "open"`. Bodies never
appear: `task list --json` does not return them.

## Apply

```bash
python3 "$S/backlog_board.py" apply --root . --changeset changeset.tsv            # dry-run diff
python3 "$S/backlog_board.py" apply --root . --changeset changeset.tsv --apply    # write
```

Dry-run by default. Cells already at the target value are dropped, so re-runs are free;
the comparison is on Backlog.md's native value, so a `P0` row against a `high` task is no
change. Each changed cell is one `backlog task edit` call; unresolvable rows print as `SKIP`
on stderr and set a non-zero exit, the resolvable rows still apply. A row is a `SKIP` when:
the task is not on the board, the field is unmapped, the priority is not a band `P0`-`P3`
or is empty, the status is not a configured non-done status, or the due date is not
`YYYY-MM-DD`.

## Field map

| Rubric output | Backlog.md cell | Values |
|---|---|---|
| Priority band | `priority` (`task edit --priority`) | `P0`/`P1` → `high`, `P2` → `medium`, `P3` → `low`. **Lossy:** P0 has no home; it lands as `high` and reads back as `P1`. An empty value is a `SKIP` against a task that has a priority, since Backlog.md has no way to clear one, and no change against a task that has none |
| Grouping | `labels` (`task edit -l` / `--clear-labels`) | comma-separated **full desired set**; the adapter diffs it against what is attached and writes the set whole |
| Ready lane | `status` (`task edit -s`) | one of the board's configured statuses except the last; matched case-insensitively, written in the configured case. The last (done) status is a `SKIP`: closing is the landing step, not triage |
| Time | `dueDate` (`--due-date` / `--clear-due-date`) | `YYYY-MM-DD`; empty clears |

**Unmapped: Impact, Effort.** They stay rubric *inputs*: the analyst reasons with them, the
priority band records the conclusion, and the reasoning goes in a comment
(`backlog task edit <ID> --comment "..."`) when it is worth keeping.

## Notes verified against a live instance

Backlog.md 1.53.0, scratch board, 2026-10-11:

- `task list --json` includes Done tasks, so the done filter is the adapter's job. Their
  labels still feed `fields.labels.options` (a label in use on shipped work is not unknown).
- The default list order is priority-first, so the adapter asks for `--sort id`; a triage
  pass otherwise reshuffles the snapshot between runs.
- `task edit --priority ""` does not clear a priority; there is no clearing flag.
- `task edit -l a,b` replaces the whole label set rather than adding to it.
- `task edit -s` accepts any case and stores the configured one; an invalid
  `--due-date` exits 1, which is why the adapter checks the date before the first write
  instead of aborting mid-apply.
- `backlog init` needs a git repo, or it stops at an interactive prompt even with `--defaults`.
