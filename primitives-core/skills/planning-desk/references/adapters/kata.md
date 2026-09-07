# Adapter — Kata

Backend for the desk's snapshot contract ([`contract.md`](contract.md)) against a Kata
project. The whole adapter is one script that ships with this skill:
`scripts/_utils/adapters/kata.py`, stdlib only — it shells out to the `kata` binary rather
than talking HTTP, since Kata already gives a scriptable CLI with `--json` output and
per-field mutation commands.

## Prerequisite

The `kata` binary on PATH, already pointed at the right daemon (`KATA_SERVER` /
`KATA_AUTH_TOKEN`; if `kata health` fails, that is a wiring problem, not an adapter problem).
No separate credentials for this adapter: it runs as whatever actor the shell resolves
(`--as` overrides, same as any other kata command).

`--project` is **optional**. With none, no `--project` flag is passed at all and Kata resolves
the project from the workspace binding (`.kata.toml` in the working tree) — the usual case for
a desk living in its project's own repo. The exported `tracker.name` then comes back from the
items' own qualified ids, so the snapshot still records which project it describes.

## Key

The issue's **short_id** (the `xmwb` in `myproject#xmwb`), not the internal numeric `id`. That
is what a plan's `## Tracking` section names, what the README ref column holds, and what a
changeset row addresses. `apply` re-resolves every key against a fresh export each run, so a
stale changeset cannot write to the wrong issue.

## Export

```bash
A="${CLAUDE_PLUGIN_ROOT}/skills/planning-desk/scripts/_utils/adapters"
python3 "$A/kata.py" export --project myproject --out snapshot.json   # explicit project
python3 "$A/kata.py" export --status all --out snapshot.json          # bound project, incl. closed
python3 "$A/kata.py" export                                           # JSON to stdout
```

With `--out` it prints one line: `<n> items (<n> open, <n> closed) -> <path>`. Default
`--status open`; `reconcile.py` asks for `all`, since an archived plan row can only be checked
against a closed issue. The listing is unpaged (`--limit 0`), so the analysis sees the whole
project rather than a first page.

## Apply

```bash
python3 "$A/kata.py" apply --changeset changeset.tsv            # dry-run diff
python3 "$A/kata.py" apply --changeset changeset.tsv --apply    # write
```

Dry-run by default. `coverage.py --changeset <file>` is the loop's usual producer: it proposes
a `needs-plan` label on every uncovered issue, and that file goes straight into `apply`.

Each changed cell is its own `kata` subprocess call (`edit`, `label add`/`label rm`,
`assign`/`unassign`); unresolvable rows print as `SKIP` on stderr and set a non-zero exit,
while the resolvable rows still apply. Apply resolves keys against `--status all`, so a label
on already-archived work still lands.

## Field map

| Desk cell | Kata field | Values |
| --------- | ---------- | ------ |
| `key` | `short_id` | e.g. `xmwb` |
| `title` | `title` | verbatim |
| `state` | `status` | `closed` when Kata says closed, else `open` |
| `kind` | `child_counts.total` + labels | `epic` when the issue has children **or** carries the `epic` label |
| `labels` | `labels` (via `kata label add`/`label rm`) | comma-separated **full desired set**; the adapter diffs it |
| `body` | `body` | verbatim, in full |
| `parent` | `parent.short_id` | null when the issue has no parent |
| `blocked_by` | `blocked_by[].short_id` | prerequisites only; `blocks` is the mirror edge and is not exported |
| `priority` | `priority` (int, via `kata edit --priority`) | `0`-`3` map to `P0`-`P3`; blank clears via `-` |
| `owner` (changeset only) | owner (via `kata assign`/`kata unassign`) | actor name; blank unassigns |

**Unmapped and why.** Deliberately not in the snapshot: `metadata` (including the `work.*`
attention signals and `deadline_on`), `related` edges, `scheduled_on`, `closed_reason`,
timestamps, and `owner`. The desk's three questions — is this body buildable, does this work
have a plan, does the plan table still agree with reality — need none of them, and every field
carried is a field the contract has to keep true across backends. Add one only when a script
actually reads it.

`owner` is a changeset cell without being a snapshot cell, which is the one asymmetry here: an
owner row therefore always writes, because there is no exported current value to compare it
against. Everything else is dropped when already at target.

**A `state`/`status` row is refused, never fabricated into a label.** Kata's close is a hard
state with a required reason and evidence (`kata close --done|--wontfix|...`), so closing or
reopening is a decision made on the tracker, not a cell an analysis script flips.

## Notes verified against a live instance

Verified 2026-09-07 against the `dotfiles-agents` project (303 issues, 101 open):

- **`kata list --json` omits unset scalars entirely** — no `priority` key at all when unset
  (116 of 303 issues had one), no `parent` key when there is no parent. The adapter normalizes
  every gap into an explicit `null` / `[]`, per the contract.
- **`child_counts` is either `null` or `{"open": n, "total": n}`** — it is not an integer and
  it is not always present, so `kind` is derived through `(child_counts or {}).get("total")`.
  On this project that made 17 items epics, 11 of them by the `epic` label and the rest by
  having children alone.
- **`blocked_by`/`blocks` are `null` when empty**, not `[]`, and their entries are objects
  (`{uid, short_id, project, qualified_id, status}`) — only `short_id` is exported.
- **Native priority 4 exists and has no band.** It normalizes to `null` rather than being
  rounded into `P3`.
- **Omitting `--project` resolves the project from the workspace binding.** `export --status
  all` with no project returned all 303 issues and a `tracker.name` of `dotfiles-agents`,
  identical to passing `--project dotfiles-agents`.
- **`--limit` defaults to 200**, so an unpaged export must pass `--limit 0` explicitly; without
  it a 303-issue project silently truncates.
- Not verified here: the `apply --apply` write path was exercised only through its planned argv
  (unit tests), never against the live daemon — this desk's live proof runs are read-only.
