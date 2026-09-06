#!/usr/bin/env python3
"""Kaneo adapter for board-triage: export a snapshot, apply a changeset.

Implements the adapter contract in the skill's SKILL.md §2 against a Kaneo board.

    kaneo_board.py export --out board-snapshot.json
    kaneo_board.py apply --changeset changeset.tsv           # dry-run diff
    kaneo_board.py apply --changeset changeset.tsv --apply   # write

Config comes from the environment, three of the values the `kaneo` skill already needs:
KANEO_API_URL, KANEO_API_KEY, KANEO_PROJECT_ID.

Why a script and not the MCP tools: `list_tasks` returns every description in full — a
few hundred KB on a real board, which is exactly the overflow the export/analyze/apply
loop exists to avoid. This emits the same board with bodies stripped.

Stdlib only, no install.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

# --- rubric bands -> Kaneo's native priority enum ---------------------------
# The rubric emits P0-P3 (SKILL.md §3); Kaneo stores a five-value enum. Both
# spellings are accepted in a changeset so the analyst never has to translate.
BAND_TO_PRIORITY = {"p0": "urgent", "p1": "high", "p2": "medium", "p3": "low"}
PRIORITIES = ("no-priority", "low", "medium", "high", "urgent")

# changeset field token -> (snapshot field key, bulk operation)
FIELD_OPS = {
    "priority": ("priority", "updatePriority"),
    "status": ("status", "updateStatus"),
    "due": ("due", "updateDueDate"),
    "assignee": ("assignee", "updateAssignee"),
}


# --- HTTP -------------------------------------------------------------------
def _request(method, path, body=None):
    base = os.environ.get("KANEO_API_URL")
    key = os.environ.get("KANEO_API_KEY")
    if not base or not key:
        sys.exit("KANEO_API_URL and KANEO_API_KEY must be set (see the kaneo skill)")
    req = urllib.request.Request(
        base.rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-api-key": key, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        sys.exit(f"{method} {path} -> {exc.code}: {exc.read().decode()[:300]}")


def _project_id():
    pid = os.environ.get("KANEO_PROJECT_ID")
    if not pid:
        sys.exit("KANEO_PROJECT_ID must be set")
    return pid


# --- pure logic (the part worth testing) ------------------------------------
def build_snapshot(project, columns, board, labels=()):
    """Contract-shaped snapshot from Kaneo's /column and /task/tasks payloads."""
    items = []
    for column in board:
        for task in column.get("tasks") or []:
            items.append(
                {
                    "key": task.get("number"),
                    "id": task["id"],
                    "title": task.get("title", ""),
                    "state": "done" if column.get("isFinal") else "open",
                    "labels": sorted(lbl["name"] for lbl in task.get("labels") or []),
                    "fields": {
                        "status": task.get("status"),
                        "priority": _band_of(task.get("priority")),
                        "due": (task.get("dueDate") or "")[:10] or None,
                        "assignee": task.get("assigneeName"),
                        # Impact and Effort have no home on this backend — see the
                        # adapter's field map. Absent, not null: a null cell reads as
                        # "unset and settable", which these are not.
                    },
                }
            )
    items.sort(key=lambda i: (i["key"] is None, i["key"]))
    return {
        "board": {"name": project.get("name", ""), "backend": "kaneo"},
        "fields": {
            "status": {"options": [c["slug"] for c in columns]},
            "priority": {"options": list(PRIORITIES)},
            "labels": {"options": sorted({lbl["name"] for lbl in labels})},
            "due": {"options": ["YYYY-MM-DD"]},
        },
        "items": items,
    }


def _band_of(priority):
    """Kaneo priority -> the band the rubric speaks, or None when untriaged."""
    if priority in (None, "", "no-priority"):
        return None
    for band, native in BAND_TO_PRIORITY.items():
        if native == priority:
            return band.upper()
    return priority


def normalize(field, value):
    """Changeset value -> the value Kaneo stores. Returns (value, problem)."""
    value = value.strip()
    if field == "priority":
        if not value:
            return "no-priority", None
        native = BAND_TO_PRIORITY.get(value.lower(), value.lower())
        if native not in PRIORITIES:
            return None, f"priority '{value}' is not a band (P0-P3) or a Kaneo priority"
        return native, None
    if field == "labels":
        return sorted(n.strip() for n in value.split(",") if n.strip()), None
    return value or None, None


def parse_changeset(text):
    """TSV -> [(key, field, raw_value)], skipping blanks, comments, and a header."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            sys.exit(f"changeset line {lineno}: need key<TAB>field<TAB>value")
        key, field, value = parts[0].strip(), parts[1].strip().lower(), "\t".join(parts[2:])
        if key.lower() == "key" and field == "field":
            continue  # header
        if not key.lstrip("#").isdigit():
            sys.exit(f"changeset line {lineno}: key '{key}' is not a task number")
        rows.append((int(key.lstrip("#")), field, value))
    return rows


def plan(snapshot, rows, label_ids=None):
    """Changeset rows + current snapshot -> (bulk operations, problems).

    Only cells that differ produce an operation; identical cells are dropped, which
    is what makes re-running a changeset free.
    """
    by_key = {item["key"]: item for item in snapshot["items"]}
    statuses = set(snapshot["fields"]["status"]["options"])
    label_ids = label_ids or {}
    ops, problems = [], []

    for key, field, raw in rows:
        item = by_key.get(key)
        if item is None:
            problems.append(f"#{key}: not on this board")
            continue
        if field not in FIELD_OPS and field != "labels":
            problems.append(f"#{key}: no Kaneo cell for field '{field}'")
            continue

        value, problem = normalize(field, raw)
        if problem:
            problems.append(f"#{key}: {problem}")
            continue

        if field == "labels":
            want, have = set(value), set(item["labels"])
            for name in sorted(want - have):
                if name not in label_ids:
                    problems.append(
                        f"#{key}: label '{name}' does not exist in this workspace — "
                        "create it first (kaneo skill: create_label)"
                    )
                    continue
                ops.append(("addLabel", label_ids[name], item["id"], f"#{key} +{name}"))
            for name in sorted(have - want):
                row_id = (item.get("label_ids") or {}).get(name)
                if not row_id:
                    problems.append(f"#{key}: cannot detach '{name}' — no attachment id in snapshot")
                    continue
                ops.append(("removeLabel", row_id, item["id"], f"#{key} -{name}"))
            continue

        snap_field, operation = FIELD_OPS[field]
        if field == "status" and value and value not in statuses:
            problems.append(
                f"#{key}: status '{value}' is not a lane on this board ({', '.join(sorted(statuses))})"
            )
            continue
        current = item["fields"].get(snap_field)
        if field == "priority":
            current = BAND_TO_PRIORITY.get((current or "").lower(), (current or "no-priority").lower())
        if (current or None) == (value or None):
            continue
        ops.append((operation, value, item["id"], f"#{key} {field}: {current!r} -> {value!r}"))

    return ops, problems


def group(ops):
    """Collapse per-item operations into one bulk call per (operation, value)."""
    grouped = {}
    for operation, value, task_id, _ in ops:
        grouped.setdefault((operation, value), []).append(task_id)
    return [
        {"operation": operation, "value": value, "taskIds": ids}
        for (operation, value), ids in grouped.items()
    ]


# --- commands ---------------------------------------------------------------
def fetch_snapshot():
    pid = _project_id()
    project = _request("GET", f"/project/{pid}")
    columns = _request("GET", f"/column/{pid}")
    board = _request("GET", f"/task/tasks/{pid}")
    board = board.get("data", board).get("columns", [])
    # labels are workspace-scoped, and the project carries its workspace id
    labels = _request("GET", f"/label/workspace/{project['workspaceId']}")
    snapshot = build_snapshot(project, columns, board, labels)
    # attachment ids, needed only to detach; kept off the contract shape
    attachments = {
        task["id"]: {lbl["name"]: lbl["id"] for lbl in task.get("labels") or []}
        for column in board
        for task in column.get("tasks") or []
    }
    for item in snapshot["items"]:
        item["label_ids"] = attachments.get(item["id"], {})
    return snapshot, {lbl["name"]: lbl["id"] for lbl in labels}


def cmd_export(args):
    snapshot, _ = fetch_snapshot()
    for item in snapshot["items"]:
        item.pop("label_ids", None)
    text = json.dumps(snapshot, indent=1, sort_keys=False)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text + "\n")
        untriaged = sum(1 for i in snapshot["items"] if i["fields"]["priority"] is None)
        print(f"{len(snapshot['items'])} items ({untriaged} untriaged) -> {args.out}")
    else:
        print(text)
    return 0


def cmd_apply(args):
    with open(args.changeset) as handle:
        rows = parse_changeset(handle.read())
    snapshot, label_ids = fetch_snapshot()  # fresh pull, never the analyst's stale copy
    ops, problems = plan(snapshot, rows, label_ids)

    for problem in problems:
        print(f"SKIP {problem}", file=sys.stderr)
    for *_, description in ops:
        print(("APPLY " if args.apply else "DRY   ") + description)
    if not ops:
        print("nothing to change")

    if not args.apply:
        if ops:
            print("\ndry-run — re-run with --apply to write")
        return 1 if problems else 0

    calls = group(ops)
    for call in calls:
        _request("PATCH", "/task/bulk", call)
    if args.settle_seconds > 0:
        time.sleep(args.settle_seconds)

    # Re-planning the same rows against a fresh pull is the read-back: plan() emits a cell
    # only while it still differs, so whatever survives never landed. One board GET, and it
    # covers labels and due as well as status. Bulk status writes on this instance have been
    # observed reverting seconds later — see references/adapters/kaneo.md.
    fresh, fresh_labels = fetch_snapshot()
    unlanded, _ = plan(fresh, rows, fresh_labels)
    for *_, description in unlanded:
        print(f"UNLANDED {description}", file=sys.stderr)

    stuck = {op[-1] for op in unlanded}
    print(f"applied {sum(1 for op in ops if op[-1] not in stuck)} cell change(s) "
          f"in {len(calls)} call(s)")
    if unlanded:
        print(f"{len(unlanded)} cell(s) did not land — re-issue those single-task",
              file=sys.stderr)
        return 2
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write a contract-shaped snapshot")
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)
    apply_ = sub.add_parser(
        "apply",
        help="apply a changeset TSV (dry-run by default)",
        epilog=(
            "exit codes:\n"
            "  0  every requested cell was confirmed on the board after the write\n"
            "  1  some changeset rows were unresolvable (SKIP on stderr); the rest applied\n"
            "  2  a written cell read back unchanged, so it did not land (UNLANDED on\n"
            "     stderr). 2 wins over 1 when both hold.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    apply_.add_argument("--changeset", required=True)
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.add_argument(
        "--settle-seconds",
        type=float,
        default=2.0,
        help="pause before re-reading the board to verify the write (default: 2.0; 0 skips)",
    )
    apply_.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
