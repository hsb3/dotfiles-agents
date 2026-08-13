# Adapter — GitHub Projects (v2)

Backend for the `board-triage` contract (SKILL.md §2). The export/apply scripts are not
duplicated here; they ship with the sibling **`github-project-board`** skill, which also holds
the field model, the capability matrix, and the GraphQL details.

## Prerequisite — the scripts live in another plugin

`github-project-board` ships in the **`solo-skills`** plugin; `board-triage` ships in
**`code-desk`**. `${CLAUDE_PLUGIN_ROOT}` resolves to *this* plugin, so it will not find them.
Install `solo-skills` alongside `code-desk` and resolve the scripts dir once:

```bash
S=$(find "$(cd "$CLAUDE_PLUGIN_ROOT/../../.." && pwd)" -type d \
      -path '*/skills/github-project-board/scripts' | sort | tail -1)
test -n "$S" || echo "install the solo-skills plugin — github-project-board ships there"
```

Outside a plugin harness, point `$S` at wherever the skill is checked out.

`gh` must be authenticated with `project` scope (`gh auth refresh -s project`). A `GITHUB_TOKEN`
env var shadows the keyring token and fails every Projects query with `INSUFFICIENT_SCOPES` —
the scripts unset it internally, but a hand-run `gh` needs `env -u GITHUB_TOKEN gh …`.

## Key

The **issue number**. Stable across item removal and re-add; `board-apply.py` re-maps
number → item-id from a fresh pull every run.

## Export

```bash
python3 "$S/board-fields.py" -o <owner> -n <number>                      # valid field/option names
python3 "$S/board-export.py" -o <owner> -n <number> --out board-snapshot.json
```

Emits `project`, `fields` (with option and iteration ids), and `items[]` carrying the full field
grid with `null` for unset cells, no issue bodies.

## Apply

```bash
python3 "$S/board-apply.py" -o <owner> -n <number> --changeset changeset.tsv            # dry-run
python3 "$S/board-apply.py" -o <owner> -n <number> --changeset changeset.tsv --apply
```

Dry-run by default, writes only differing cells, idempotent, non-zero exit on failure.

## Field map

| Rubric output | Board cell | Values |
|---|---|---|
| Priority band | `priority` | `P0` `P1` `P2` `P3` — passed through verbatim |
| Impact | `impact` | `High` `Medium` `Low` |
| Effort | `effort` | `S` `M` `L` `XL` |
| Grouping | `workstream` | single-select; the board's own option names |
| Ready lane | `status` | `Up Next` (`Backlog` `In Progress` `In Review` `Blocked` `Done`) |
| Time | `iteration` `start` `target` | iteration title / `YYYY-MM-DD` |

Nothing in the rubric is unmapped on this backend. The pseudo-fields `blocked_by` / `blocking`
route to the native dependencies endpoint and need `--repo`; single-select values are option
**names** (confirm them with `board-fields.py`).

## Notes

- These fields exist only if the board was built with them — `github-project-board` §5 creates
  them. Against a board missing `impact`/`effort`, `board-apply.py` reports the unresolved token
  rather than inventing a field.
- Views and workflows are UI-only on this backend; triage never touches them.
