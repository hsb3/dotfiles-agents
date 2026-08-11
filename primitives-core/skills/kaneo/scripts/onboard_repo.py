#!/usr/bin/env python3
"""Onboard one repo onto a Kaneo board: discover, provision, import, verify.

Written for a fleet of repos that are a mix of greenfield (nothing to migrate, just
needs a project and its lanes) and brownfield (a Backlog.md tree to move over), run one
repo at a time so a failure costs one repo rather than the batch.

Three things here exist because of specific, observed failures rather than good taste:

  * **Discovery is a separate, read-only command, and `apply` refuses to invent a
    project.** A session on 2026-08-11 created a duplicate board for a repo that already
    had one, purely because nothing looked first.
  * **Statuses are resolved against the target project's own columns.** There is no
    global status vocabulary in Kaneo — a task's status is the slug of a column in its
    own project. A remembered four-slug list writes tasks into lanes the board lacks.
  * **Labels are re-attached in a second pass and verified by re-export.** Bulk import
    accepts a `labels` key, discards it, and still reports `"failed": 0`. Trusting the
    import summary loses every label while looking like success.

Idempotent: every created task is recorded in a state file keyed by its source id, so a
re-run after an interruption imports only what is missing. Delete the state file to
force a full re-import (which will duplicate — that is what it is for).

Stdlib only. Reads KANEO_API_URL and KANEO_API_KEY from the environment.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Backlog.md wraps each section in these markers, which makes the body parseable without
# guessing at heading levels that differ across repos.
SECTION = re.compile(
    r"<!--\s*SECTION:(?P<name>[A-Z_]+):BEGIN\s*-->(?P<body>.*?)<!--\s*SECTION:\1:END\s*-->",
    re.S,
)
FRONTMATTER = re.compile(r"\A---\r?\n(?P<fm>.*?)\r?\n---\r?\n(?P<body>.*)\Z", re.S)
# Sections worth carrying across, in the order they should appear in the Kaneo body.
CARRY = ("DESCRIPTION", "ACCEPTANCE_CRITERIA", "IMPLEMENTATION_PLAN", "IMPLEMENTATION_NOTES")
SOURCES = (("tasks", "TASK"), ("drafts", "DRAFT"), ("decisions", "DECISION"))
PRIORITIES = ("low", "medium", "high")
# Kaneo requires a colour on every label; these are the plugin's neutral defaults and are
# only used when creating a label that does not exist yet.
LABEL_COLOR = "#6b7280"


class ApiError(RuntimeError):
    pass


def api(method, path, body=None):
    """One REST call against $KANEO_API_URL, returning parsed JSON (or None on 204)."""
    base = os.environ.get("KANEO_API_URL", "").rstrip("/")
    key = os.environ.get("KANEO_API_KEY", "")
    if not base or not key:
        raise ApiError("KANEO_API_URL and KANEO_API_KEY must both be set")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        method=method,
        headers={"x-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(f"{method} {path} -> HTTP {exc.code}: {exc.read()[:400]!r}") from exc
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # A missing task answers 400 with a bare sentence rather than JSON; surfacing the
        # text beats a decode traceback that hides which call failed.
        raise ApiError(f"{method} {path} -> non-JSON body: {raw[:200]!r}") from None


def unwrap(payload):
    """Kaneo answers some routes bare and some wrapped in {"data": ...}."""
    if isinstance(payload, dict) and set(payload) >= {"data"} and len(payload) <= 2:
        return payload["data"]
    return payload


# --------------------------------------------------------------------------- parsing


def parse_frontmatter(text):
    """The small YAML subset Backlog.md actually emits.

    Covers scalars, `[]`, inline `[a, b]`, block lists, and — the one that matters —
    folded/literal block scalars (`>`, `>-`, `|`, `|-`). Backlog.md wraps any title past
    its line-width in a folded scalar, which in one real repo is 100 of 192 task files;
    treating `>-` as the value silently retitles more than half the import.

    Deliberately not a YAML parser: pulling in PyYAML would break the zero-install rule
    this repo holds, and the emitted subset is narrow and stable.
    """
    fields = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip():
            continue
        match = re.match(r"([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()

        if value[:1] in (">", "|") and value.strip("+-") in (">", "|"):
            folded = value.startswith(">")
            block = []
            while index < len(lines):
                nxt = lines[index]
                if nxt.strip() and not nxt[:1].isspace():
                    break
                block.append(nxt.strip())
                index += 1
            joined = (" " if folded else "\n").join(part for part in block if part)
            fields[key] = joined.strip()
            continue

        if value == "":
            # A bare `labels:` introduces a block list on the following lines. Consume
            # them here rather than leaving the key absent, so a `- ` inside some later
            # block scalar can never be mistaken for another entry.
            items = []
            while index < len(lines):
                item = re.match(r"\s+-\s+(.*)$", lines[index])
                if not item:
                    break
                items.append(item.group(1).strip().strip("'\""))
                index += 1
            if items:
                fields[key] = items
            continue

        if value == "[]":
            fields[key] = []
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fields[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
        else:
            fields[key] = value.strip("'\"")
    return fields


def parse_task_file(path, kind):
    """One Backlog.md file -> the record this script imports, or None if unreadable."""
    try:
        text = path_read(path)
    except OSError:
        return None
    match = FRONTMATTER.match(text)
    if not match:
        return None
    fields = parse_frontmatter(match.group("fm"))
    sections = {m.group("name"): m.group("body").strip() for m in SECTION.finditer(text)}
    body = "\n\n".join(
        f"## {name.replace('_', ' ').title()}\n\n{sections[name]}"
        for name in CARRY
        if sections.get(name)
    )
    if not body:
        # No marked sections (hand-written or an older Backlog.md): keep the whole body
        # rather than silently importing an empty description.
        body = match.group("body").strip()
    labels = [str(v) for v in (fields.get("labels") or []) if str(v).strip()]
    if fields.get("type"):
        labels.append(str(fields["type"]))
    if kind == "DECISION":
        # Matches the convention the reference board already uses: a decision is a task
        # in the Documents lane carrying a `decision` label, so it stays filterable once
        # its original Proposed/Accepted wording is no longer a status.
        labels.append("decision")
    priority = str(fields.get("priority", "") or "").lower()
    return {
        "source_id": str(fields.get("id") or path.rsplit("/", 1)[-1]),
        "kind": kind,
        "title": str(fields.get("title") or "(untitled)").strip(),
        "status": str(fields.get("status") or "").strip(),
        "priority": priority if priority in PRIORITIES else "medium",
        "labels": sorted(set(labels)),
        "body": body,
        "path": path,
    }


def path_read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def read_backlog(root):
    """Every task/draft/decision under <root>/backlog, sorted for a stable import order."""
    records = []
    for folder, kind in SOURCES:
        directory = os.path.join(root, "backlog", folder)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".md"):
                continue
            record = parse_task_file(os.path.join(directory, name), kind)
            if record:
                records.append(record)
    return records


def slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


# ------------------------------------------------------------------------ board reads


def get_columns(project_id):
    return unwrap(api("GET", f"/column/{project_id}")) or []


def get_tasks(project_id):
    return (unwrap(api("GET", f"/task/export/{project_id}")) or {}).get("tasks", [])


def workflow_records(records):
    """Only the kinds whose status is a workflow state.

    Drafts and decisions carry free text where a task carries a lane: real repos hold
    `Proposed`, `accepted`, `Accepted (corrected 2026-07-29)`, and
    `superseded by decision-002`. Feeding those to lane resolution asks the board to grow
    a column per historical footnote, so they are routed to a fixed lane instead and keep
    their original wording in the body.
    """
    return [r for r in records if r["kind"] == "TASK"]


def resolve_statuses(records, columns, create_for=None):
    """Map each source status onto a column slug on THIS project.

    Returns (mapping, unmapped). Nothing is guessed: a status with no column is reported
    so the caller can create the lane deliberately rather than silently parking work in
    whatever lane happens to be first.
    """
    by_slug = {c["slug"]: c["slug"] for c in columns}
    by_name = {slugify(c["name"]): c["slug"] for c in columns}
    mapping, unmapped = {}, []
    for status in sorted({r["status"] for r in records if r["status"]}):
        slug = slugify(status)
        target = by_slug.get(slug) or by_name.get(slug)
        if target:
            mapping[status] = target
        else:
            unmapped.append(status)
    if create_for and unmapped:
        for status in list(unmapped):
            created = unwrap(api("POST", f"/column/{create_for}", {"name": status}))
            mapping[status] = (created or {}).get("slug") or slugify(status)
            unmapped.remove(status)
    return mapping, unmapped


# ----------------------------------------------------------------------------- writes


def lane_for(record, mapping, lanes):
    """The column slug this record lands in — its own status, or its kind's fixed lane."""
    if record["kind"] == "TASK":
        return mapping.get(record["status"], "")
    return lanes[record["kind"]]


def body_for(record):
    """The imported description, keeping a non-workflow status rather than dropping it."""
    if record["kind"] == "TASK" or not record["status"]:
        return record["body"]
    return f"_{record['kind'].title()} status: {record['status']}_\n\n{record['body']}"


def import_tasks(project_id, records, mapping, title_prefix, lanes):
    """One bulk POST. Returns the created tasks, in the order they were submitted."""
    payload = [
        {
            "title": f"{r['source_id']}: {r['title']}" if title_prefix else r["title"],
            "description": body_for(r),
            "status": lane_for(r, mapping, lanes),
            "priority": r["priority"],
        }
        for r in records
    ]
    result = unwrap(api("POST", f"/task/import/{project_id}", {"tasks": payload})) or {}
    outcomes = (result.get("results") or {}).get("tasks") or []
    created = []
    for record, outcome in zip(records, outcomes):
        task = (outcome or {}).get("task") or {}
        if outcome.get("success") and task.get("id"):
            created.append((record, task["id"]))
    return created, result.get("results", {})


def attach_labels(workspace_id, created, existing_labels):
    """Second pass, because import discards labels and reports success anyway.

    Kaneo's label rows are per-attachment, so this posts one label per (task, name) pair
    rather than trying to reuse a single id across tasks.
    """
    known = {label["name"]: label.get("color") or LABEL_COLOR for label in existing_labels}
    attached = 0
    for record, task_id in created:
        for name in record["labels"]:
            api(
                "POST",
                "/label",
                {
                    "name": name,
                    "color": known.get(name, LABEL_COLOR),
                    "workspaceId": workspace_id,
                    "taskId": task_id,
                },
            )
            attached += 1
    return attached


# ------------------------------------------------------------------------------ state


def load_state(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return {"imported": {}}


def save_state(path, state):
    if not path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")


# --------------------------------------------------------------------------- commands


def cmd_discover(args):
    """Read-only. What exists for this repo already, and what the backlog holds."""
    records = read_backlog(args.repo) if args.repo else []
    print(f"repo: {args.repo or '(none given)'}")
    if records:
        by_kind, by_status = {}, {}
        for record in records:
            by_kind[record["kind"]] = by_kind.get(record["kind"], 0) + 1
            by_status[record["status"]] = by_status.get(record["status"], 0) + 1
        print(f"  backlog: {len(records)} items " + json.dumps(by_kind))
        print(f"  statuses in use: " + json.dumps(by_status))
        labels = sorted({label for r in records for label in r["labels"]})
        print(f"  labels in use ({len(labels)}): {', '.join(labels) or '—'}")
    else:
        print("  backlog: none found — greenfield, nothing to import")

    projects = unwrap(api("GET", f"/project?workspaceId={args.workspace}")) or []
    print(f"\nprojects already in workspace {args.workspace}: {len(projects)}")
    for project in projects:
        print(f"  {project.get('id')}  {project.get('slug'):<12} {project.get('name')}")
    if args.project_id:
        columns = get_columns(args.project_id)
        print(f"\ncolumns on {args.project_id}:")
        for column in columns:
            final = " (final)" if column.get("isFinal") else ""
            print(f"  {column['position']:>2}  {column['slug']:<14} {column['name']}{final}")
        if records:
            mapping, unmapped = resolve_statuses(workflow_records(records), columns)
            for status, slug in sorted(mapping.items()):
                print(f"  map: {status!r} -> {slug}")
            if unmapped:
                print(f"  UNMAPPED (need lanes): {', '.join(unmapped)}")
            other = sorted({r["kind"] for r in records if r["kind"] != "TASK"})
            if other:
                print(
                    f"  {'/'.join(other)} route to a fixed lane (--draft-lane / "
                    "--decision-lane); their free-text status is kept in the body"
                )
        print(f"  tasks already on board: {len(get_tasks(args.project_id))}")
    return 0


def cmd_apply(args):
    records = read_backlog(args.repo)
    if not records:
        print("nothing to import (greenfield repo or no backlog/ directory)")
        return 0
    state = load_state(args.state)
    pending = [r for r in records if r["source_id"] not in state["imported"]]
    print(f"{len(records)} in backlog, {len(records) - len(pending)} already imported, "
          f"{len(pending)} to go")
    if not pending:
        return 0

    columns = get_columns(args.project_id)
    if not columns:
        print(f"error: project {args.project_id} has no columns — wrong id?", file=sys.stderr)
        return 2
    mapping, unmapped = resolve_statuses(
        workflow_records(pending),
        columns,
        create_for=args.project_id if args.create_columns else None,
    )
    if unmapped:
        print(
            "error: these task statuses have no lane on the target board:\n  "
            + "\n  ".join(unmapped)
            + "\nCreate them first, or re-run with --create-columns.",
            file=sys.stderr,
        )
        return 2

    lanes = {"DRAFT": args.draft_lane, "DECISION": args.decision_lane}
    slugs = {c["slug"] for c in columns}
    needed = {lanes[k] for k in {r["kind"] for r in pending} & set(lanes)}
    if not needed <= slugs:
        print(
            f"error: fixed lane(s) {sorted(needed - slugs)} do not exist on this board. "
            f"Available: {sorted(slugs)}",
            file=sys.stderr,
        )
        return 2

    if not args.yes:
        print("\n-- dry run, re-run with --yes to write --")
        for record in pending[:10]:
            title = f"{record['source_id']}: {record['title']}"
            print(f"  {lane_for(record, mapping, lanes):<14} {title[:70]}")
        if len(pending) > 10:
            print(f"  ... and {len(pending) - 10} more")
        return 0

    created, summary = import_tasks(
        args.project_id, pending, mapping, args.title_prefix, lanes
    )
    print(f"import: {summary.get('successful', 0)}/{summary.get('total', 0)} created, "
          f"{summary.get('failed', 0)} failed")
    for record, task_id in created:
        state["imported"][record["source_id"]] = task_id
    save_state(args.state, state)

    labelled = [(r, t) for r, t in created if r["labels"]]
    if labelled:
        existing = unwrap(api("GET", f"/label/workspace/{args.workspace}")) or []
        count = attach_labels(args.workspace, labelled, existing)
        print(f"labels: {count} attachments across {len(labelled)} tasks")

    return verify(args.project_id, created, labelled)


def verify(project_id, created, labelled):
    """Re-export and check the board, because the import summary cannot be trusted.

    It reports `"failed": 0` while silently discarding every label, so the only honest
    confirmation is reading the tasks back.
    """
    on_board = get_tasks(project_id)
    titles = {t.get("title") for t in on_board}
    missing = [r["title"] for r, _ in created if not _title_present(r, titles)]
    with_labels = sum(1 for t in on_board if t.get("labels"))
    print(f"verify: {len(on_board)} tasks on board, {with_labels} carry labels")
    if missing:
        print(f"  MISSING {len(missing)}: {missing[:5]}", file=sys.stderr)
        return 1
    if labelled and with_labels < len(labelled):
        print(
            f"  WARNING: expected at least {len(labelled)} labelled tasks, found "
            f"{with_labels} — the label pass did not fully take.",
            file=sys.stderr,
        )
        return 1
    return 0


def _title_present(record, titles):
    return any(record["source_id"] in (title or "") or title == record["title"] for title in titles)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", required=True, help="target workspace id")
    sub = parser.add_subparsers(dest="command", required=True)

    disc = sub.add_parser("discover", help="read-only: what exists, what would move")
    disc.add_argument("--repo", help="path to the repo checkout")
    disc.add_argument("--project-id", help="existing Kaneo project, if there is one")
    disc.set_defaults(func=cmd_discover)

    app = sub.add_parser("apply", help="import a repo's backlog onto an existing project")
    app.add_argument("--repo", required=True)
    app.add_argument("--project-id", required=True, help="never created for you; discover first")
    app.add_argument("--state", help="JSON id-map making re-runs resumable")
    app.add_argument("--create-columns", action="store_true", help="provision missing lanes")
    app.add_argument("--draft-lane", default="to-do",
                     help="lane for drafts, whose status is not a workflow state")
    app.add_argument("--decision-lane", default="documents",
                     help="lane for decisions; they also get a `decision` label")
    app.add_argument("--no-title-prefix", dest="title_prefix", action="store_false",
                     help="omit the source id from imported titles")
    app.add_argument("--yes", action="store_true", help="actually write (default is a dry run)")
    app.set_defaults(func=cmd_apply, title_prefix=True)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
