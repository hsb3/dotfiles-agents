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
is the one stripping bodies, in `build_snapshot()`, same as every other adapter does for
its own backend.

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

## The maintenance rhythm

Triage is one move in a longer loop, and the tools are split across two plugins — nothing
else names them in order, which is why they get run piecemeal or not at all. Run at session
start, or whenever `board_health.py` says a pass is due:

| # | Tool | Ships in | Answers |
|---|---|---|---|
| 1 | `kata_doctor.py` | kata plugin | Is this checkout even wired to the board? Every warn is wiring debt. |
| 2 | `audit_issues.py` | kata plugin | Is each card *defined* — a title that fits, acceptance text, real edges instead of prose? |
| 3 | `board_health.py --vocabulary` | this skill | Does the board *discriminate*, or has it decayed into one undifferentiated band? |
| 4 | this skill, §5 | this skill | The pass itself, when step 3 says one is due. |
| 5 | `board_health.py --vocabulary` | this skill | Did the pass take? Exit 0 or it did not. |

Steps 2 and 3 look redundant and are not, and the difference is the whole reason step 3
exists. `audit_issues.py` reads one card at a time and asks whether its fields are
**populated**; `board_health.py` reads the whole board and asks whether those fields still
**discriminate**. A board can pass every per-card check and still be unusable: measured on a live board
2026-09-08, the audit reported `no-priority: 0` and `body-thin: 0` while 34 of 55 open items
sat in one priority band, 16 carried no label at all, and the area grouping existed only
inside title prefixes where no query could reach it. Per-card checks cannot see a
distribution, so run both.

Step 1 is a gate, not a suggestion — a FAIL there means every later step is reading or
writing the wrong board.

### Steps 3 and 5 run with a declared vocabulary

```bash
python3 "$S/board_health.py" --vocabulary "$S/core-labels.txt" <(python3 "$S/kata_board.py" export --project <name>)
```

`core-labels.txt` ships next to the scripts and is the default declaration. Without
`--vocabulary` the `vocabulary-fossils` check reports SKIP on every run: the only label set a
snapshot carries is `fields.labels.options`, which the adapter derives from the board's whole
history, so retired names live in it forever and it can never go green. A declaration is the
only input that makes the check answerable, and passing one is what turns a permanent SKIP
into a verdict.

The core vocabulary is a closed set of names plus one family (decision-023): exactly one
type label per item from type:feat, type:fix or type:chore; the container and behaviour
labels epic, decision, handoff, meta, needs-review and up-next; and exactly one area label,
whose values each project defines for itself — which is why no area name is in the file, as
a fixed one would be a fossil on every board that spells its areas differently. A project
adds labels **on top of** the core, never instead of it, and points `--vocabulary` at its
own copy once it does. The grouping lives in these labels, never in a title prefix — a
prefix is the smell `check_grouping_latent` reports.

**If the project imports GitHub issues** (`kata sync github`), know that the sync is
**import-only by design** — a card never becomes an issue, and a kata close never closes one.
Kata's intended loop closes the issue through the code: the fixing PR says `Fixes #N` and
GitHub closes on merge.

**That loop breaks in any repo whose PRs do not merge to the default branch.** GitHub
auto-closes only from the default branch, so where work lands on a `dev` branch and the
default branch is written by a publish job, `Closes #N` is inert and the issue stays open
forever. Such a repo needs a reconcile pass: classify each open issue as tracked (its card is
open), stale (its card is closed — close the issue with a pointer to the card), or untracked
(no card, so it is inbound intake awaiting decomposition). Left un-run this is worse than
untidy: `kata sync github enable` resets the sync cursor and re-applies GitHub state onto the
board, **reopening every closed card whose mirror is still open**.

Two mirror rules the sync enforces whether or not you reconcile: the sync **owns** a mirror's
title, body, labels and comments and re-applies GitHub's version whenever that issue next
changes, so put acceptance criteria in native children (`--parent <mirror>`) and never in the
mirror's body; and anything rewritten in place — a rolling handoff, a living plan — must be a
native card, never a mirror.

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
