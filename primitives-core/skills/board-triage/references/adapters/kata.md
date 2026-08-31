# Adapter — Kata

Backend for the `board-triage` contract (SKILL.md §2) against a Kata project. The whole
adapter is one script that ships with this skill: `scripts/kata_board.py`, stdlib only —
it shells out to the `kata` binary rather than talking HTTP, since Kata already gives a
scriptable CLI with `--json` output and per-field mutation commands.

## Prerequisite

The `kata` binary on PATH, already pointed at the right daemon (`KATA_SERVER` /
`KATA_AUTH_TOKEN` — see the kata-hosted-daemon reference if `kata health` fails). No
separate credentials for this adapter: it runs as whatever actor your shell already
resolves (`--as` overrides, same as any other kata command).

Kata also ships an MCP server (`kata mcp serve`) — this adapter goes around it and calls
the CLI directly instead. Both surfaces return full issue bodies from `list`/`show` alike
(verified 2026-08-31: `kata list --json` includes every `body` in full), so neither is
free of the overflow problem the export/analyze/apply loop exists to avoid — the adapter
is the one stripping bodies, in `build_snapshot()`, same as the Kaneo adapter does for its
own backend.

## Key

The issue's **short_id** (the `9dj9` in `keel#9dj9`), not the internal numeric `id`. Apply
re-resolves short_id → current field values from a fresh `kata list` every run, so a stale
changeset cannot write to the wrong issue.

## Export

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/board-triage/scripts"
python3 "$S/kata_board.py" export --project keel --out board-snapshot.json
```

Prints `<n> items (<n> untriaged) -> board-snapshot.json`. Only `--status open` issues are
fetched — see the field map note on `state` below for why that's the whole board, not a
filtered view.

## Apply

```bash
python3 "$S/kata_board.py" apply --project keel --changeset changeset.tsv            # dry-run diff
python3 "$S/kata_board.py" apply --project keel --changeset changeset.tsv --apply    # write
```

Dry-run by default. Cells already at the target value are dropped, so re-runs are free.
Each changed cell is its own `kata` subprocess call (`edit`, `label add/rm`, `deadline`,
`assign`/`unassign`); unresolvable rows print as `SKIP` on stderr and set a non-zero exit,
the resolvable rows still apply.

## Field map

| Rubric output | Kata cell | Values |
|---|---|---|
| Priority band | `priority` (int, edited via `kata edit --priority`) | `P0`-`P3` map to `0`-`3`; empty clears via `-` |
| Grouping | `labels` (via `kata label add`/`kata label rm`) | comma-separated **full desired set**; the adapter diffs it against what's attached |
| Time | `metadata.deadline_on` (via `kata deadline`) | `YYYY-MM-DD`; empty clears via `-` |
| — | owner (via `kata assign`/`kata unassign`) | actor name |

**Unmapped: Ready lane, Impact, Effort.** Kata has no kanban-style status/column field —
an issue is only ever `open` or hard-`closed`, and readiness is *computed* from the
`blocked_by` graph (`kata ready`/`kata next`), not stored on the issue. A changeset row
with `field=status` is reported as a `SKIP`, never fabricated into a label. Impact and
Effort stay rubric *inputs* same as every other adapter: the analyst reasons with them,
the priority band records the conclusion, and the reasoning goes in a comment
(`kata comment <ref> --body "..."`) when it's worth keeping.

**Why `state` is always `"open"` in the snapshot:** unlike a kanban board's "Done" column
(still technically open, just parked), Kata's close is a hard state with a required
reason and evidence (`kata close --done|--wontfix|...`). A closed issue is genuinely done,
not merely triaged, so it's excluded at export time (`--status open`) rather than pulled
in and then dropped per SKILL.md §4 step 2 — for this backend that step is a no-op.

## Notes verified against a live instance

- `kata list --json` and `kata show --json` omit unset scalar fields entirely (no
  `priority` key at all when unset) rather than emitting `null` — the adapter normalizes
  that gap into an explicit `null` cell so blanks stay visible per the contract.
- `kata edit`, `kata label add/rm`, `kata deadline`, and `kata assign`/`unassign` are the
  only mutation surface needed; there's no bulk-write endpoint like Kaneo's `/task/bulk`,
  so apply makes one `kata` call per changed cell. Fine at triage volume; batch if a run
  routinely emits dozens of changed cells and the per-call daemon round-trip starts to
  show (`ponytail: sequential subprocess calls, batch via a future `kata` bulk verb or a
  worker pool if that ever measurably matters`).
- `kata deadline` does not add a first-class column — it writes `metadata.deadline_on`, a
  reserved key confirmed by reading an issue back after setting it (verified 2026-08-31 on
  a scratch issue in project `tmp-kata`).
- A live project (`keel`) already carries `kaneo-status:<column>` and `kaneo_column`
  metadata left over from a prior Kaneo migration. That's migration residue on one
  project, not an ongoing Kata feature — this adapter does not read or write it, and a
  fresh Kata-native project has no such labels at all.
