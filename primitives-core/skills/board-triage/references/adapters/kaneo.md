# Adapter — Kaneo

Backend for the `board-triage` contract (SKILL.md §2) against a Kaneo board. The whole adapter
is one script that ships with this skill: `scripts/kaneo_board.py`, stdlib only.

## Prerequisite

Three environment values, the ones the `kaneo` skill already requires:

```
KANEO_API_URL      API base, e.g. https://<host>/api
KANEO_API_KEY      your agent's key (REST sends it as x-api-key)
KANEO_PROJECT_ID   the board to triage
```

The workspace id is read off the project, so it is not a separate value. Use the agent identity
you were assigned, never an owner key.

**Do not triage through the MCP `list_tasks` tool.** It returns every task description in full —
hundreds of KB on a real board, which overflows the analyst before triage starts. That overflow
is the reason this loop exists; the export below strips bodies.

## Key

The **task number** (the `232` in `DFA-232`). Apply re-resolves number → task id from a fresh
pull every run, so a stale changeset cannot write to the wrong task.

## Export

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/board-triage/scripts"
python3 "$S/kaneo_board.py" export --out board-snapshot.json
```

Prints `<n> items (<n> untriaged) -> board-snapshot.json`.

## Apply

```bash
python3 "$S/kaneo_board.py" apply --changeset changeset.tsv            # dry-run diff
python3 "$S/kaneo_board.py" apply --changeset changeset.tsv --apply    # write
```

Dry-run by default. Cells already at the target value are dropped, so re-runs are free. Writes go
through `PATCH /task/bulk`, grouped into one call per (operation, value). Unresolvable rows print
as `SKIP` on stderr and set a non-zero exit; the resolvable rows still apply.

## Field map

| Rubric output | Kaneo cell | Values |
|---|---|---|
| Priority band | `priority` | `P0`–`P3` **or** `no-priority` `low` `medium` `high` `urgent` — the bands map `P0→urgent, P1→high, P2→medium, P3→low`, empty clears to `no-priority` |
| Grouping | `labels` | comma-separated **full desired set**; the adapter diffs it against what's attached |
| Ready lane | `status` | a **column slug on this board** — there is no global status vocabulary; the snapshot's `fields.status.options` is the valid set |
| Time | `due` | `YYYY-MM-DD` |
| — | `assignee` | user id |

**Unmapped: Impact and Effort.** Kaneo has no field for either, and this adapter will not
manufacture one out of labels. They stay rubric *inputs*: the analyst reasons with them, the
priority band records the conclusion, and the reasoning goes in a task comment when it is worth
keeping. Their cells are absent from the snapshot rather than `null`, so they cannot be mistaken
for unset-but-settable.

## Notes verified against Kaneo image 2.16.4

- `PUT /task/priority/{id}`, `/task/due-date/{id}`, `/task/status/{id}`, `/task/title/{id}`,
  `/task/description/{id}` and `PATCH /task/bulk` all exist. Full-object `update_task` is never
  needed for triage, which matters: its read-merge-write can silently revert a status transition
  another integration just made.
- `GET /task/export/{projectId}` looks like the natural snapshot source and is not — it emits no
  task id and no number, so nothing can be keyed or written back. The adapter reads
  `GET /task/tasks/{projectId}` instead.
- Bulk `addLabel`/`removeLabel` take a label **id**, not a name (a name returns 404 "Label not
  found"). Kaneo labels are per-attachment rows sharing a name, so adding resolves the name to
  any existing row id, which the server copies onto the target task; removing needs that task's
  own attachment id. Both are handled by the script — but a label name that exists nowhere in the
  workspace cannot be created this way, and reports as a `SKIP`.
