# Adapter — file tracker

Backend for the `board-triage` contract (SKILL.md §2) against the plain-file tracker: one
Markdown file per item under `.tasks/`, specified in
[`../file-tracker-format.md`](../file-tracker-format.md). The whole adapter is
`scripts/file_tracker.py`, stdlib only. It reads and writes the item files directly, so there
is no daemon, token or network to configure.

Tracker id `file`. Detected by `.tasks/` at the repo root, and the fallback when detection finds no other board.

## Key

The item id, `t<n>`, which is also the filename. Apply re-reads every item file each run, so a
stale changeset cannot write over a value changed since the export.

## Export

Replace `<board-triage-skill-dir>` with the absolute installed directory containing
board-triage SKILL.md. Run from the repo root, or pass `--root`.

```bash
S="<board-triage-skill-dir>/scripts"
T=$(mktemp -d)   # scratch for snapshot + changeset; see SKILL.md §5
python3 "$S/file_tracker.py" export --out "$T/board-snapshot.json"
```

Prints `<n> items (<n> untriaged) -> <path>`. Only open items are exported;
`done` and `dropped` are closed, not triage work. While any item file breaks the grammar,
export exits 1 and prints a `BROKEN <path>: <why>` line per problem instead of a snapshot: a
pass over a tracker it cannot fully read would rank a partial board.

## Apply

```bash
python3 "$S/file_tracker.py" apply --changeset "$T/changeset.tsv"            # dry-run diff
python3 "$S/file_tracker.py" apply --changeset "$T/changeset.tsv" --apply    # write
```

Dry-run by default; cells already at the target value are dropped, so re-runs are free. Each
write rewrites one frontmatter line and leaves every other byte of the file alone. Commit the
pass as one commit, and add a `## Log` line by hand where the reasoning is worth keeping.

## Field map

| Rubric output | Cell | Values |
|---|---|---|
| Priority band | `priority` | `P0`-`P3` stored verbatim; empty clears it |
| Grouping | `labels` | comma-separated **full desired set**, written back as `[a, b]` |

**Unmapped: Ready lane, Time, Impact, Effort.** Readiness is computed from `blocked-by`, not
stored, and `status` only says open, done or dropped; closing is the landing step, so a
`status` row is a `SKIP`. The format has no date field, so a dated critical path goes in a
label or the body. Impact and Effort stay rubric inputs, and the reasoning goes in the item's
Log.

## Health

```bash
python3 "$S/board_health.py" --vocabulary "$S/core-labels.txt" <(python3 "$S/file_tracker.py" export)
```

`core-labels.txt` is the shipped core vocabulary. On a tracker that has not adopted it, read the
fossil findings as the adoption gap, as the Kata adapter explains; point `--vocabulary` at the
project's own list once it declares one.
