# Adapter contract — what the desk needs from a tracker

The desk's analysis scripts never talk to a tracker. They read a **snapshot**: one JSON
document, produced by an adapter, in the shape below. Anything that can produce that shape
and consume a changeset is a valid backend — this file is enough to write a second adapter
without reading the first one.

Backend-neutral by construction: no tracker command appears here, and no ref syntax is baked
into any script.

## The loop

```
export   adapters/<name>.py export [--project P] [--status open|all] --out snapshot.json
analyze  conformance.py | coverage.py | reconcile.py  --snapshot snapshot.json
apply    adapters/<name>.py apply --changeset changeset.tsv        # dry-run
         adapters/<name>.py apply --changeset changeset.tsv --apply
```

The analysis scripts also run the export themselves when no `--snapshot` is given
(`--adapter <name>` picks which; default is the one the skill ships). Passing a file is how you
analyze the same state twice, diff two exports, or work offline.

Why the snapshot exists at all: a tracker's own list output carries every body in full, so
piping it through a model burns the context the analysis needs. The adapter is what normalizes
and bounds it, and it is the only component that has to change when the tracker does.

## Snapshot shape

```json
{
  "tracker": {"name": "<project name>", "backend": "<adapter name>"},
  "items": [
    {
      "key": "xmwb",
      "title": "Wire the adapter",
      "state": "open",
      "kind": "issue",
      "labels": ["chore", "infra"],
      "body": "## Acceptance criteria\n- ...\n",
      "parent": "p937",
      "blocked_by": ["ay9p"],
      "priority": "P1",
      "owner": "some-actor"
    }
  ]
}
```

| Field | Type | Rules |
| ----- | ---- | ----- |
| `tracker.name` | string | the project the items came from; `""` when the tracker reports none |
| `tracker.backend` | string | the adapter's own name |
| `key` | string | the tracker's stable, human-typable id — what a plan's `## Tracking` names |
| `title` | string | never null; `""` when unset |
| `state` | `"open"` \| `"closed"` | any backend-specific lane collapses to one of these two |
| `kind` | `"issue"` \| `"epic"` | `"epic"` = the item has children or is labelled as one |
| `labels` | string list | sorted; `[]` when none |
| `body` | string | the full body — the conformance audit reads its headings |
| `parent` | string \| null | the parent's `key` |
| `blocked_by` | string list | prerequisite `key`s, sorted; `[]` when none |
| `priority` | `"P0"`–`"P3"` \| null | a value outside the band vocabulary normalizes to null |
| `owner` | string \| null | the assignee; null when unassigned |

**Every changeset cell has a snapshot cell.** That is what lets `apply` drop no-ops, so a
field the adapter can write but cannot read back does not belong in the changeset vocabulary.

Invariants an adapter must hold:

- **Items sort by `key`**, so two exports of unchanged state are byte-identical and diffable.
- **Every field is present on every item.** An unset scalar is explicit `null` and an unset
  list is `[]` — never an absent key. The scripts read cells by name, and an absent key is a
  crash mid-audit rather than a finding.
- **A value outside the contract's vocabulary becomes null, never an invention.** A native
  priority with no band is null; it is not rounded into the nearest band.
- **`--status open` is the default; `--status all` includes closed items.** `reconcile.py`
  needs `all`, because an archived plan row can only be checked against a closed item.

## Changeset shape

TSV, one cell per line: `key<TAB>field<TAB>value`. Blank lines, `#` comments, and a
`key/field` header row are skipped. A tab inside the value survives (everything after the
second tab is the value).

```
key	field	value
ay9p	labels	documentation,needs-plan
xmwb	priority	P1
xmwb	owner	
```

**Three columns, always** — the last line above ends in a tab. A row with only two columns
is a fatal parse error, not an empty value: a trailing tab lost to an editor would otherwise
read as "clear this cell", and on a `labels` row that means removing every label the item has.

| Field | Value | Semantics |
| ----- | ----- | --------- |
| `labels` | comma-separated | the **full desired set**; the adapter diffs it against what is attached and emits adds + removes |
| `priority` | `P0`–`P3`, or blank | blank clears the cell |
| `owner` | an actor name, or blank | blank unassigns |

Rules every adapter's `apply` must hold:

- **Dry-run by default**; writing is opt-in (`--apply`).
- **Re-resolve against a FRESH export every run.** A changeset written an hour ago must not
  clobber a value someone else changed in the meantime.
- **Cells already at the target value are dropped**, so re-running a changeset is free and an
  applied changeset re-plans to nothing. No exceptions: this is why every changeset cell needs
  a snapshot cell to compare against.
- **An unresolvable row is a `SKIP` on stderr and a non-zero exit; the resolvable rows still
  apply.** Unknown key, unknown field, a value outside the vocabulary — all named, never
  guessed.
- **`state`/`status` is not a changeset cell.** Closing and reopening are decisions carrying
  their own evidence, made on the tracker directly. A `state` row is a SKIP, never fabricated
  into a label.
- **Anything the backend cannot store is unmapped and said so** in that adapter's own
  reference, rather than being written somewhere approximate.

## Writing a second adapter

One file under `scripts/_utils/adapters/<name>.py`, stdlib only, with `export` and `apply`
subcommands as above, plus a sibling `references/adapters/<name>.md` recording the prerequisite,
what `key` is, the field map, and what is unmapped and why. The desk then reaches it with
`--adapter <name>`; nothing else in the toolkit changes.

Keep the transformations in plain functions (`build_snapshot`, `normalize`, `parse_changeset`,
`plan`) and the tracker calls in thin wrappers — that split is what makes the adapter testable
without a live tracker.
