#!/usr/bin/env python3
"""Kata adapter for board-triage: export a snapshot, apply a changeset.

Implements the adapter contract in the skill's SKILL.md §2 against a Kata project.

    kata_board.py export --project keel --out board-snapshot.json
    kata_board.py apply --project keel --changeset changeset.tsv           # dry-run diff
    kata_board.py apply --project keel --changeset changeset.tsv --apply   # write

Config: just --project. Kata's own auth (KATA_SERVER / KATA_AUTH_TOKEN) is assumed
already configured on this machine — see the kata-hosted-daemon reference.

Why a script and not raw `kata` calls per changeset row: apply must re-resolve
short_id -> current field values from a fresh `kata list` every run, same discipline
as every other adapter, so a stale changeset can't clobber a value someone else
already changed underneath it.

Stdlib only, no install — shells out to the `kata` binary already on PATH.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# --- rubric bands -> Kata's native priority scale (0=highest .. 4=lowest) ---
# The rubric emits P0-P3 (SKILL.md §3); Kata stores an integer. Priority 4 exists
# on Kata but has no rubric band — it's out of this adapter's vocabulary, same as
# any other value a changeset didn't put there.
BAND_TO_PRIORITY = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
PRIORITY_TO_BAND = {v: k.upper() for k, v in BAND_TO_PRIORITY.items()}


def _kata(args, project):
    proc = subprocess.run(
        ["kata", *args, "--project", project, "--json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"kata {' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}")
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _kata_write(args, project):
    """Same call, but for mutations: --agent output, exit code is the contract."""
    proc = subprocess.run(
        ["kata", *args, "--project", project, "--agent"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"kata {' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}")


# --- pure logic (the part worth testing) ------------------------------------
def build_snapshot(project, issues, labels):
    """Contract-shaped snapshot from `kata list --json` and `kata labels --json`."""
    items = []
    for issue in issues:
        items.append(
            {
                "key": issue["short_id"],
                "id": issue["short_id"],  # kata mutations address by ref, not a separate id
                "title": issue.get("title", ""),
                # kata's close is a hard state, not a kanban "done" lane — this
                # adapter only ever exports --status open, so this is always "open".
                "state": "open",
                "labels": sorted(issue.get("labels") or []),
                "fields": {
                    "priority": PRIORITY_TO_BAND.get(issue.get("priority")),
                    "due": (issue.get("metadata") or {}).get("deadline_on"),
                    "assignee": issue.get("owner"),
                    # "status"/lane has no home on this backend — see the adapter's
                    # field map. Absent, not null: a null cell reads as "unset and
                    # settable", which this is not.
                },
            }
        )
    items.sort(key=lambda i: i["key"])
    return {
        "board": {"name": project, "backend": "kata"},
        "fields": {
            "priority": {"options": ["P0", "P1", "P2", "P3"]},
            "labels": {"options": sorted(lbl["label"] for lbl in labels)},
            "due": {"options": ["YYYY-MM-DD"]},
        },
        "items": items,
    }


def normalize(field, value):
    """Changeset value -> the value Kata stores. Returns (value, problem)."""
    value = value.strip()
    if field == "priority":
        if not value:
            return None, None
        native = BAND_TO_PRIORITY.get(value.lower())
        if native is None:
            return None, f"priority '{value}' is not a band (P0-P3)"
        return native, None
    if field == "labels":
        return sorted(n.strip() for n in value.split(",") if n.strip()), None
    if field == "status":
        return None, "status has no cell on Kata (no lane/column field) — leave it off the changeset"
    return value or None, None


def parse_changeset(text):
    """TSV -> [(short_id, field, raw_value)], skipping blanks, comments, and a header."""
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


def plan(snapshot, rows):
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
        if field not in ("priority", "labels", "due", "assignee", "status"):
            problems.append(f"{key}: no Kata cell for field '{field}'")
            continue

        value, problem = normalize(field, raw)
        if problem:
            problems.append(f"{key}: {problem}")
            continue

        if field == "labels":
            want, have = set(value), set(item["labels"])
            for name in sorted(want - have):
                ops.append((["label", "add", key, name], f"{key} +{name}"))
            for name in sorted(have - want):
                ops.append((["label", "rm", key, name], f"{key} -{name}"))
            continue

        current = item["fields"].get(field)
        if field == "priority":
            current_band = current  # already a band string or None
            if (current_band or None) == (PRIORITY_TO_BAND.get(value) or None):
                continue
            argv = ["edit", key, "--priority", str(value) if value is not None else "-"]
            ops.append((argv, f"{key} priority: {current_band!r} -> {PRIORITY_TO_BAND.get(value)!r}"))
        elif field == "due":
            if (current or None) == (value or None):
                continue
            argv = ["deadline", key, value or "-"]
            ops.append((argv, f"{key} due: {current!r} -> {value!r}"))
        elif field == "assignee":
            if (current or None) == (value or None):
                continue
            argv = ["assign", key, value] if value else ["unassign", key]
            ops.append((argv, f"{key} assignee: {current!r} -> {value!r}"))

    return ops, problems


# --- commands ---------------------------------------------------------------
def fetch_snapshot(project):
    listed = _kata(["list", "--status", "open", "--limit", "0"], project)
    labeled = _kata(["labels"], project)
    # `or []`, not a .get default: kata answers an empty project with an explicit null,
    # which a default never replaces.
    return build_snapshot(project, listed.get("issues") or [], labeled.get("labels") or [])


def cmd_export(args):
    snapshot = fetch_snapshot(args.project)
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
    snapshot = fetch_snapshot(args.project)  # fresh pull, never the analyst's stale copy
    ops, problems = plan(snapshot, rows)

    for problem in problems:
        print(f"SKIP {problem}", file=sys.stderr)
    for _, description in ops:
        print(("APPLY " if args.apply else "DRY   ") + description)
    if not ops:
        print("nothing to change")

    if args.apply:
        for argv, _ in ops:
            _kata_write(argv, args.project)
        print(f"applied {len(ops)} cell change(s)")
    elif ops:
        print("\ndry-run — re-run with --apply to write")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write a contract-shaped snapshot")
    export.add_argument("--project", required=True)
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)
    apply_ = sub.add_parser("apply", help="apply a changeset TSV (dry-run by default)")
    apply_.add_argument("--project", required=True)
    apply_.add_argument("--changeset", required=True)
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
