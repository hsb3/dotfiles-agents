#!/usr/bin/env python3
"""File tracker: detect the tracker in play, list `.tasks/`, export and apply a triage pass.

    file_tracker.py detect                                  # kata | github | backlog | file
    file_tracker.py list [--all]                            # inventory with readiness
    file_tracker.py export [--out board-snapshot.json]      # triage snapshot
    file_tracker.py apply --changeset changeset.tsv         # dry-run diff
    file_tracker.py apply --changeset changeset.tsv --apply # write

The format is specified in references/file-tracker-format.md next to this script's
skill. `detect` honours a `tracker:` key in .claude/tracker.local.md before detecting. Every command reads from --root (default: the current directory). A file that
breaks the grammar is reported by path and fails the command: `list` exits 1 after
printing what did parse, `export` and `apply` refuse to run at all.

Stdlib only, no install.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

KEYS = ("id", "title", "status", "priority", "labels", "blocked-by")
LIST_KEYS = ("labels", "blocked-by")
STATUSES = ("open", "done", "dropped")
BANDS = ("P0", "P1", "P2", "P3")
ITEM_NAME = re.compile(r"^t([1-9][0-9]*)\.md$")
TRIAGE_VIEW = "triage.md"
TRACKERS = ("kata", "github", "backlog", "file")
SETTING = os.path.join(".claude", "tracker.local.md")


# --- reading ----------------------------------------------------------------
def parse(path):
    """One item file -> (fields, problems). Fields carry every key, lists as lists."""
    stem = os.path.basename(path)[:-3]
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    if lines[0] != "---":
        return None, ["first line must be ---"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None, ["frontmatter is never closed by a --- line"]

    fields, problems = {}, []
    for lineno, line in enumerate(lines[1:end], 2):
        key, sep, value = line.partition(": ")
        if not sep and line.endswith(":"):
            key, value = line[:-1], ""
        elif not sep:
            problems.append(f"line {lineno}: not 'key: value'")
            continue
        if key not in KEYS:
            problems.append(f"line {lineno}: unknown key {key!r}")
            continue
        if key in fields:
            problems.append(f"line {lineno}: duplicate key {key!r}")
            continue
        value = value.strip()
        if key in LIST_KEYS:
            if not (value.startswith("[") and value.endswith("]")):
                problems.append(f"line {lineno}: {key} must be a one-line [a, b] list")
                continue
            value = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        fields[key] = value

    missing = [key for key in KEYS if key not in fields]
    if missing:
        problems.append(f"missing key(s): {', '.join(missing)}")
    elif list(fields) != list(KEYS):
        problems.append(f"keys out of order; expected {', '.join(KEYS)}")
    if fields.get("id") is not None and fields["id"] != stem:
        problems.append(f"id {fields['id']!r} does not match the filename {stem!r}")
    if "title" in fields and not fields["title"]:
        problems.append("title is empty")
    if fields.get("status") not in (None, *STATUSES):
        problems.append(f"status {fields['status']!r} is not one of {', '.join(STATUSES)}")
    if fields.get("priority") not in (None, "", *BANDS):
        problems.append(f"priority {fields['priority']!r} is not P0-P3 or empty")
    return (None if problems else fields), problems


def load(root):
    """Every item under <root>/.tasks -> (items sorted by number, problems as 'path: why')."""
    tasks = os.path.join(root, ".tasks")
    if not os.path.isdir(tasks):
        return [], []
    items, problems = [], []
    for name in sorted(os.listdir(tasks)):
        rel = os.path.join(".tasks", name)
        if not name.endswith(".md") or name == TRIAGE_VIEW:
            continue
        if not ITEM_NAME.match(name):
            problems.append(f"{rel}: not an item filename (t<n>.md)")
            continue
        fields, why = parse(os.path.join(tasks, name))
        problems.extend(f"{rel}: {w}" for w in why)
        if fields:
            items.append(fields)
    items.sort(key=lambda item: int(item["id"][1:]))
    known = {name[:-3] for name in os.listdir(tasks) if ITEM_NAME.match(name)}
    for item in items:
        for ref in item["blocked-by"]:
            if ref not in known:
                problems.append(f".tasks/{item['id']}.md: blocked-by {ref!r} names no item")
    return items, problems


def open_blockers(item, by_id):
    """Blockers still open; an item is ready when this is empty. An unreadable blocker counts as open."""
    return [ref for ref in item["blocked-by"] if by_id.get(ref, {"status": "open"})["status"] == "open"]


def next_id(root):
    """1 + the highest number ever used, closed items and broken files included."""
    tasks = os.path.join(root, ".tasks")
    names = os.listdir(tasks) if os.path.isdir(tasks) else []
    numbers = [int(m.group(1)) for m in map(ITEM_NAME.match, names) if m]
    return f"t{max(numbers, default=0) + 1}"


# --- detection --------------------------------------------------------------
def configured(root):
    """The `tracker:` key in .claude/tracker.local.md frontmatter, or None when absent or blank."""
    path = os.path.join(root, SETTING)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    if lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() == "tracker" and value.strip():
            value = value.strip().strip("'\"")
            if value not in TRACKERS:
                raise SystemExit(f"{SETTING}: tracker {value!r} is not one of {', '.join(TRACKERS)}")
            return value
    return None


def detect(root, run=subprocess.run):
    """The configured tracker, else the first rung that holds: kata binding, GitHub issues in
    use, a Backlog.md board, .tasks/, else the file tracker as the fallback."""
    pinned = configured(root)
    if pinned:
        return pinned, f"set by {SETTING}"
    if os.path.isfile(os.path.join(root, ".kata.toml")):
        return "kata", ".kata.toml binds a kata project"
    try:
        remotes = run(["git", "-C", root, "remote", "-v"], capture_output=True, text=True)
    except FileNotFoundError:
        remotes = None
    if remotes and remotes.returncode == 0 and "github.com" in remotes.stdout:
        try:
            proc = run(["gh", "issue", "list", "--state", "all", "--limit", "1",
                        "--json", "number"], capture_output=True, text=True, cwd=root)
        except FileNotFoundError:
            raise SystemExit("a GitHub remote is configured but gh is not installed; "
                             "cannot tell whether its issues are in use")
        if proc.returncode != 0:
            raise SystemExit(f"a GitHub remote is configured but gh could not list its "
                             f"issues: {proc.stderr.strip()}")
        if json.loads(proc.stdout or "[]"):
            return "github", "the GitHub remote's issues are in use"
    for board in (".backlog", "backlog"):
        if os.path.isfile(os.path.join(root, board, "config.yml")):
            return "backlog", f"{board}/ holds a Backlog.md board"
    if os.path.isdir(os.path.join(root, ".tasks")):
        return "file", ".tasks/ holds the file tracker"
    return "file", "no tracker found: falling back to the file tracker (.tasks/ is created on first write)"


# --- triage snapshot and changeset ------------------------------------------
def build_snapshot(root, items):
    """Contract-shaped snapshot of the open items. Closed items are not triage work."""
    return {
        "board": {"name": os.path.basename(os.path.abspath(root)), "backend": "file"},
        "fields": {
            "priority": {"options": list(BANDS)},
            "labels": {"options": sorted({lbl for item in items for lbl in item["labels"]})},
        },
        "items": [
            {
                "key": item["id"],
                "id": f".tasks/{item['id']}.md",
                "title": item["title"],
                "state": "open",
                "labels": sorted(item["labels"]),
                "fields": {"priority": item["priority"] or None},
            }
            for item in items
            if item["status"] == "open"
        ],
    }


def parse_changeset(text):
    """TSV -> [(key, field, raw_value)], skipping blanks, comments, and a header."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            raise SystemExit(f"changeset line {lineno}: need key<TAB>field<TAB>value")
        key, field, value = parts[0].strip(), parts[1].strip().lower(), "\t".join(parts[2:])
        if key.lower() == "key" and field == "field":
            continue
        rows.append((key, field, value.strip()))
    return rows


def plan(snapshot, rows):
    """Rows + fresh snapshot -> (writes, problems). Only cells that differ become a write."""
    by_key = {item["key"]: item for item in snapshot["items"]}
    writes, problems = [], []
    for key, field, raw in rows:
        item = by_key.get(key)
        if item is None:
            problems.append(f"{key}: no open item with this id")
        elif field == "priority":
            band = raw.upper() or None
            if band is not None and band not in BANDS:
                problems.append(f"{key}: priority {raw!r} is not a band (P0-P3)")
            elif band != item["fields"]["priority"]:
                writes.append((key, "priority", band or "",
                               f"{key} priority: {item['fields']['priority']!r} -> {band!r}"))
        elif field == "labels":
            want = sorted({part.strip() for part in raw.split(",") if part.strip()})
            if want != item["labels"]:
                writes.append((key, "labels", want, f"{key} labels: {item['labels']} -> {want}"))
        elif field == "status":
            problems.append(f"{key}: status is not a triage cell — readiness comes from "
                            "blocked-by, and closing is the landing step")
        else:
            problems.append(f"{key}: no file-tracker cell for field {field!r}")
    return writes, problems


def write_field(root, key, field, value):
    """Rewrite one frontmatter line in place; every other byte stays as it was."""
    path = os.path.join(root, ".tasks", f"{key}.md")
    with open(path, encoding="utf-8", newline="") as handle:
        lines = handle.read().split("\n")
    end = next(i for i in range(1, len(lines)) if lines[i].rstrip("\r") == "---")
    rendered = f"[{', '.join(value)}]" if isinstance(value, list) else value
    for i in range(1, end):
        if lines[i].partition(":")[0] == field:
            eol = "\r" if lines[i].endswith("\r") else ""
            lines[i] = f"{field}: {rendered}".rstrip() + eol
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines))


# --- commands ---------------------------------------------------------------
def report(problems):
    for problem in problems:
        print(f"BROKEN {problem}", file=sys.stderr)


def cmd_detect(args):
    tracker, reason = detect(args.root)
    print(f"{tracker}\t{reason}")
    return 0


def cmd_list(args):
    items, problems = load(args.root)
    by_id = {item["id"]: item for item in items}
    shown = [item for item in items if args.all or item["status"] == "open"]
    for item in shown:
        if item["status"] != "open":
            state = item["status"]
        elif open_blockers(item, by_id):
            state = f"blocked by {', '.join(open_blockers(item, by_id))}"
        else:
            state = "owner-gated" if "decision" in item["labels"] else "ready"
        print("\t".join([item["id"], item["priority"] or "-", state,
                         ",".join(item["labels"]) or "-", item["title"]]))
    opened = [item for item in items if item["status"] == "open"]
    unblocked = [item for item in opened if not open_blockers(item, by_id)]
    gated = sum(1 for item in unblocked if "decision" in item["labels"])
    print(f"# {len(opened)} open ({len(unblocked) - gated} ready, {gated} owner-gated), "
          f"{len(items) - len(opened)} closed; next id {next_id(args.root)}")
    report(problems)
    return 1 if problems else 0


def checked_snapshot(root):
    items, problems = load(root)
    if problems:
        report(problems)
        raise SystemExit(f"{len(problems)} broken item file(s); fix them before a triage pass")
    return build_snapshot(root, items)


def cmd_export(args):
    snapshot = checked_snapshot(args.root)
    text = json.dumps(snapshot, indent=1)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        untriaged = sum(1 for i in snapshot["items"] if i["fields"]["priority"] is None)
        print(f"{len(snapshot['items'])} items ({untriaged} untriaged) -> {args.out}")
    else:
        print(text)
    return 0


def cmd_apply(args):
    with open(args.changeset, encoding="utf-8") as handle:
        rows = parse_changeset(handle.read())
    writes, problems = plan(checked_snapshot(args.root), rows)
    for problem in problems:
        print(f"SKIP {problem}", file=sys.stderr)
    for *_, description in writes:
        print(("APPLY " if args.apply else "DRY   ") + description)
    if not writes:
        print("nothing to change")
    if args.apply:
        for key, field, value, _ in writes:
            write_field(args.root, key, field, value)
        print(f"applied {len(writes)} cell change(s)")
    elif writes:
        print("\ndry-run — re-run with --apply to write")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repo root holding .tasks/ (default: .)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("detect", help="name the tracker in play").set_defaults(func=cmd_detect)
    list_ = sub.add_parser("list", help="inventory: open items with readiness")
    list_.add_argument("--all", action="store_true", help="include done and dropped items")
    list_.set_defaults(func=cmd_list)
    export = sub.add_parser("export", help="write a triage snapshot of the open items")
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)
    apply_ = sub.add_parser("apply", help="apply a changeset TSV (dry-run by default)")
    apply_.add_argument("--changeset", required=True)
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
