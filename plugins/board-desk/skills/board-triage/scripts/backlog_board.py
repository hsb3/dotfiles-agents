#!/usr/bin/env python3
"""Backlog.md adapter for board-triage: export a snapshot, apply a changeset.

Implements the adapter contract in the skill's SKILL.md §2 against a Backlog.md board.

    backlog_board.py export --root . --out board-snapshot.json
    backlog_board.py apply --root . --changeset changeset.tsv           # dry-run diff
    backlog_board.py apply --root . --changeset changeset.tsv --apply   # write

Config: just --root, the directory holding the board (default: cwd). Backlog.md finds its
board from the working directory, so every call runs with cwd=root.

Why a script and not raw `backlog` calls per changeset row: apply must re-resolve task id ->
current field values from a fresh `backlog task list` every run, same discipline as every
other adapter, so a stale changeset can't clobber a value someone else already changed.

Stdlib only, no install — shells out to the `backlog` binary already on PATH.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# --- rubric bands -> Backlog.md's native priority scale (high / medium / low) ---
# The rubric emits P0-P3 (SKILL.md §3); Backlog.md has three levels, so the map is lossy
# on purpose: P0 and P1 both write `high`, and `high` reads back as P1. A P0 row against
# a `high` task is therefore "no change", not a write.
BAND_TO_PRIORITY = {"p0": "high", "p1": "high", "p2": "medium", "p3": "low"}
PRIORITY_TO_BAND = {"high": "P1", "medium": "P2", "low": "P3"}


def _backlog(args, root):
    """Run `backlog <args>` from the board root; stdout on success, exit on any failure."""
    try:
        proc = subprocess.run(["backlog", *args], capture_output=True, text=True, cwd=root)
    except OSError as err:  # no binary on PATH, or --root is not a directory
        sys.exit(f"backlog {' '.join(args)} -> {err}")
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        sys.exit(f"backlog {' '.join(args)} -> exit {proc.returncode}: {detail}")
    return proc.stdout


def _csv(text):
    return [part.strip() for part in text.split(",") if part.strip()]


# --- pure logic (the part worth testing) ------------------------------------
def build_snapshot(root, tasks, statuses, config_labels):
    """Contract-shaped snapshot from `task list --json` and the board's config.

    The last configured status is Backlog.md's done lane; those tasks are finished work,
    not triage input, so they never reach the snapshot (their labels still count as
    vocabulary, so a label in use on shipped work isn't offered as unknown).
    """
    done = statuses[-1].casefold()
    label_options, items = set(config_labels), []
    for task in tasks:
        label_options.update(task.get("labels") or [])
        if (task.get("status") or "").casefold() == done:
            continue
        items.append(
            {
                "key": task["id"],
                "id": task["id"],  # backlog edits address by task id
                "title": task.get("title", ""),
                "state": "open",
                "labels": sorted(task.get("labels") or []),
                "fields": {
                    "priority": PRIORITY_TO_BAND.get(task.get("priority")),
                    "status": task.get("status"),
                    "due": task.get("dueDate"),
                },
            }
        )
    return {
        "board": {"name": os.path.basename(os.path.abspath(root)), "backend": "backlog"},
        "fields": {
            "priority": {"options": ["P0", "P1", "P2", "P3"]},
            "status": {"options": statuses[:-1]},
            "labels": {"options": sorted(label_options)},
            "due": {"options": ["YYYY-MM-DD"]},
        },
        "items": items,
    }


def normalize(field, value, statuses):
    """Changeset value -> the value Backlog.md stores. Returns (value, problem)."""
    value = value.strip()
    if field == "priority":
        if not value:
            return None, None
        native = BAND_TO_PRIORITY.get(value.lower())
        if native is None:
            return None, f"priority '{value}' is not a band (P0-P3)"
        return native, None
    if field == "labels":
        return sorted({n.strip() for n in value.split(",") if n.strip()}), None
    if field == "status":
        for name in statuses:
            if name.casefold() == value.casefold():
                if name == statuses[-1]:
                    return None, f"status '{name}' is the done status — closing is the landing step, not triage"
                return name, None
        return None, f"status '{value}' is not one of: {', '.join(statuses[:-1])}"
    if field == "due":
        if not value:
            return None, None
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError(value)
            datetime.date.fromisoformat(value)
        except ValueError:
            return None, f"due '{value}' is not a YYYY-MM-DD date"
        return value, None
    return value or None, None


def parse_changeset(text):
    """TSV -> [(task_id, field, raw_value)], skipping blanks, comments, and a header."""
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
        rows.append((key, field, value))
    return rows


def plan(snapshot, rows, statuses):
    """Changeset rows + current snapshot -> (ops, problems).

    An op is (argv, description). Only cells that differ produce an op; identical
    cells are dropped, which is what makes re-running a changeset free.
    """
    by_key = {item["key"]: item for item in snapshot["items"]}
    ops, problems = [], []

    for key, field, raw in rows:
        item = by_key.get(key)
        if item is None:
            problems.append(f"{key}: not on this board")
            continue
        if field not in ("priority", "labels", "status", "due"):
            problems.append(f"{key}: no Backlog.md cell for field '{field}'")
            continue

        value, problem = normalize(field, raw, statuses)
        if problem:
            problems.append(f"{key}: {problem}")
            continue

        edit = ["task", "edit", key]
        current = item["fields"].get(field)
        if field == "labels":
            want, have = set(value), set(item["labels"])
            if want == have:
                continue
            diff = [f"+{n}" for n in sorted(want - have)] + [f"-{n}" for n in sorted(have - want)]
            argv = edit + (["-l", ",".join(value)] if value else ["--clear-labels"])
            ops.append((argv, f"{key} labels: {' '.join(diff)}"))
        elif field == "priority":
            if value is None:
                if current is not None:
                    problems.append(f"{key}: Backlog.md cannot clear a priority")
                continue
            # Compare natively: the snapshot holds the lossy band, so P0 vs `high` is equal.
            if BAND_TO_PRIORITY.get((current or "").lower()) == value:
                continue
            ops.append((edit + ["--priority", value],
                        f"{key} priority: {current!r} -> {raw.strip().upper()!r} ({value})"))
        elif field == "status":
            if (current or "").casefold() == value.casefold():
                continue
            ops.append((edit + ["-s", value], f"{key} status: {current!r} -> {value!r}"))
        elif field == "due":
            if (current or None) == value:
                continue
            argv = edit + (["--due-date", value] if value else ["--clear-due-date"])
            ops.append((argv, f"{key} due: {current!r} -> {value!r}"))

    return ops, problems


# --- commands ---------------------------------------------------------------
def fetch_snapshot(root):
    """Fresh pull; returns (snapshot, configured statuses) — apply needs both."""
    # --sort id: backlog's default order is priority-first, so a re-triage would reshuffle it.
    listed = json.loads(_backlog(["task", "list", "--json", "--sort", "id"], root) or "{}")
    statuses = _csv(_backlog(["config", "get", "statuses"], root))
    if not statuses:
        sys.exit("backlog config get statuses -> empty; cannot tell which status is done")
    config_labels = _csv(_backlog(["config", "get", "labels"], root))
    return build_snapshot(root, listed.get("tasks") or [], statuses, config_labels), statuses


def cmd_export(args):
    snapshot, _ = fetch_snapshot(args.root)
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
    snapshot, statuses = fetch_snapshot(args.root)  # fresh pull, never the analyst's stale copy
    ops, problems = plan(snapshot, rows, statuses)

    for problem in problems:
        print(f"SKIP {problem}", file=sys.stderr)
    for _, description in ops:
        print(("APPLY " if args.apply else "DRY   ") + description)
    if not ops:
        print("nothing to change")

    if args.apply:
        for argv, _ in ops:
            _backlog(argv, args.root)
        print(f"applied {len(ops)} cell change(s)")
    elif ops:
        print("\ndry-run — re-run with --apply to write")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write a contract-shaped snapshot")
    export.add_argument("--root", default=".", help="directory holding the board (default: cwd)")
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)
    apply_ = sub.add_parser("apply", help="apply a changeset TSV (dry-run by default)")
    apply_.add_argument("--root", default=".", help="directory holding the board (default: cwd)")
    apply_.add_argument("--changeset", required=True)
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
