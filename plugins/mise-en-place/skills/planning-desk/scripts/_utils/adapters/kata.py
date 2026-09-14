#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Kata adapter for the planning desk: export a snapshot, apply a changeset.

Answers "what is on the tracker right now, in the desk's own vocabulary?" (export)
and "make these cells match what the analysis proposed" (apply). The snapshot
contract and the changeset TSV are in `references/adapters/contract.md`; what maps
to what on this backend is in `references/adapters/kata.md`.

    kata.py export --project keel --out snapshot.json
    kata.py export --out snapshot.json            # project from the workspace binding
    kata.py apply --changeset changeset.tsv       # dry-run diff
    kata.py apply --changeset changeset.tsv --apply

`--project` is optional: with no `--project` the binary resolves the project from the
workspace binding, so a desk sitting in its own repo needs no configuration at all.

Why a script and not raw tracker calls per changeset row: apply re-resolves every key
against a FRESH export on every run, so a changeset written an hour ago cannot clobber
a value someone else changed in the meantime.

Stdlib only, no install -- shells out to the `kata` binary already on PATH, which
carries its own auth (see the adapter reference).

Exit 1 when apply could not resolve a row (each one printed as SKIP on stderr); the
resolvable rows still apply. Exit 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

# --- desk bands <-> the backend's native priority scale (0 = highest .. 4 = lowest) --
# The desk speaks P0-P3. Native 4 exists but has no band, so it reads back as null
# rather than being invented into one.
BAND_TO_PRIORITY = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
PRIORITY_TO_BAND = {v: k.upper() for k, v in BAND_TO_PRIORITY.items()}

# The only cells a changeset may address. Anything else is a SKIP, never a guess.
CHANGESET_FIELDS = ("labels", "priority", "owner")


# --- pure logic (the part worth testing) ------------------------------------
def build_snapshot(project, issues):
    """Contract-shaped snapshot from this backend's `list --json` payload.

    Every field is normalized to an explicit value: an unset scalar comes back as
    null and an unset list as `[]`, because the analysis scripts read cells by name
    and an absent key would be a crash mid-audit rather than a finding.
    """
    items = []
    for issue in issues:
        children = issue.get("child_counts") or {}
        labels = sorted(issue.get("labels") or [])
        epic = bool(children.get("total")) or "epic" in labels
        items.append(
            {
                "key": issue["short_id"],
                "title": issue.get("title") or "",
                "state": "closed" if issue.get("status") == "closed" else "open",
                "kind": "epic" if epic else "issue",
                "labels": labels,
                "body": issue.get("body") or "",
                "parent": (issue.get("parent") or {}).get("short_id"),
                "blocked_by": sorted(
                    dep["short_id"] for dep in (issue.get("blocked_by") or [])
                ),
                "priority": PRIORITY_TO_BAND.get(issue.get("priority")),
                "owner": issue.get("owner") or None,
            }
        )
    items.sort(key=lambda i: i["key"])
    return {"tracker": {"name": project or _project_of(issues), "backend": "kata"}, "items": items}


def _project_of(issues):
    """The project the items came from, read off a qualified id ("<project>#<key>").

    Only used when no --project was given, so the snapshot still names the tracker
    the workspace binding resolved to.
    """
    for issue in issues:
        qualified = issue.get("qualified_id") or ""
        if "#" in qualified:
            return qualified.split("#", 1)[0]
    return ""


def normalize(field, value):
    """Changeset value -> the value this backend stores. Returns (value, problem)."""
    value = value.strip()
    if field == "priority":
        if not value:
            return None, None  # blank clears
        native = BAND_TO_PRIORITY.get(value.lower())
        if native is None:
            return None, f"priority '{value}' is not a band (P0-P3)"
        return native, None
    if field == "labels":
        return sorted(name.strip() for name in value.split(",") if name.strip()), None
    if field in ("state", "status"):
        return None, (
            "state is not a changeset cell -- closing and reopening are decisions with "
            "their own evidence, made on the tracker directly"
        )
    return value or None, None


def parse_changeset(text):
    """TSV -> [(key, field, raw_value)], skipping blanks, comments, and a header."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        # Three columns, always. A row that lost its trailing tab would otherwise read
        # as "clear this cell" -- on a labels row that plans a removal of every label
        # the item has. An EMPTY third column still splits into three, so a deliberate
        # blank (`key<TAB>labels<TAB>`) keeps working.
        if len(parts) < 3:
            sys.exit(f"changeset line {lineno}: need key<TAB>field<TAB>value")
        key, field, value = parts[0].strip(), parts[1].strip().lower(), "\t".join(parts[2:])
        if key.lower() == "key" and field == "field":
            continue  # header
        rows.append((key, field, value))
    return rows


def plan(snapshot, rows):
    """Changeset rows + a fresh snapshot -> (ops, problems).

    An op is (argv, description). Only cells that DIFFER produce an op; identical
    cells are dropped, which is what makes re-running a changeset free.
    """
    by_key = {item["key"]: item for item in snapshot["items"]}
    ops, problems = [], []

    for key, field, raw in rows:
        item = by_key.get(key)
        if item is None:
            problems.append(f"{key}: not on this tracker")
            continue
        value, problem = normalize(field, raw)
        if problem:
            problems.append(f"{key}: {problem}")
            continue
        if field not in CHANGESET_FIELDS:
            problems.append(f"{key}: no cell for field '{field}'")
            continue

        if field == "labels":
            want, have = set(value), set(item["labels"])
            for name in sorted(want - have):
                ops.append((["label", "add", key, name], f"{key} +{name}"))
            for name in sorted(have - want):
                ops.append((["label", "rm", key, name], f"{key} -{name}"))
        elif field == "priority":
            band = PRIORITY_TO_BAND.get(value)
            if (item["priority"] or None) == (band or None):
                continue
            argv = ["edit", key, "--priority", str(value) if value is not None else "-"]
            ops.append((argv, f"{key} priority: {item['priority']!r} -> {band!r}"))
        elif field == "owner":
            if (item["owner"] or None) == (value or None):
                continue
            argv = ["assign", key, value] if value else ["unassign", key]
            ops.append((argv, f"{key} owner: {item['owner']!r} -> {value!r}"))

    return ops, problems


# --- the subprocess boundary ------------------------------------------------
def _project_args(project):
    """No --project at all when none was given: the binary resolves it from the
    workspace binding, which is what a desk living in its own repo wants."""
    return ["--project", project] if project else []


def _read(args, project):
    proc = subprocess.run(
        ["kata", *args, *_project_args(project), "--json"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        sys.exit(f"{' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}")
    if not proc.stdout.strip():
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        # A notice or progress line on stdout, most likely. Say so rather than
        # surfacing a decoder traceback from the middle of an export.
        sys.exit(f"{' '.join(args)} -> output is not JSON ({err}): {proc.stdout[:120]!r}")


def _write(args, project):
    """Same call, but for mutations: agent output, exit code is the contract."""
    proc = subprocess.run(
        ["kata", *args, *_project_args(project), "--agent"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        sys.exit(f"{' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}")


def fetch_snapshot(project, status):
    listed = _read(["list", "--status", status, "--limit", "0"], project)
    return build_snapshot(project, listed.get("issues", []))


# --- commands ---------------------------------------------------------------
def cmd_export(args):
    snapshot = fetch_snapshot(args.project, args.status)
    text = json.dumps(snapshot, indent=1)
    if not args.out:
        print(text)
        return 0
    with open(args.out, "w") as handle:
        handle.write(text + "\n")
    states = [i["state"] for i in snapshot["items"]]
    print(
        f"{len(states)} items ({states.count('open')} open, "
        f"{states.count('closed')} closed) -> {args.out}"
    )
    return 0


def cmd_apply(args):
    with open(args.changeset) as handle:
        rows = parse_changeset(handle.read())
    # A fresh pull every run, never the analyst's stale copy: apply resolves keys
    # across open AND closed items so a row on archived work still lands.
    snapshot = fetch_snapshot(args.project, "all")
    ops, problems = plan(snapshot, rows)

    for problem in problems:
        print(f"SKIP {problem}", file=sys.stderr)
    for _, description in ops:
        print(("APPLY " if args.apply else "DRY   ") + description)
    if not ops:
        print("nothing to change")

    if args.apply:
        for argv, _ in ops:
            _write(argv, args.project)
        print(f"applied {len(ops)} cell change(s)")
    elif ops:
        print("\ndry-run -- re-run with --apply to write")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="write a contract-shaped snapshot")
    export.add_argument("--project", help="tracker project (default: the workspace binding)")
    export.add_argument("--status", choices=("open", "all"), default="open")
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)

    apply_ = sub.add_parser("apply", help="apply a changeset TSV (dry-run by default)")
    apply_.add_argument("--project", help="tracker project (default: the workspace binding)")
    apply_.add_argument("--changeset", required=True)
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
