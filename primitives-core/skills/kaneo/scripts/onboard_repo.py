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

# Backlog.md wraps each section in HTML-comment markers, which makes the body parseable
# without guessing at heading levels that differ across repos. Two marker dialects exist
# in the wild: `<!-- SECTION:NAME:BEGIN -->` and the bare `<!-- NAME:BEGIN -->` (current
# Backlog.md emits AC and COMMENTS bare, everything else prefixed). Matching only the
# prefixed form silently dropped every acceptance-criteria section of a 101-card import.
SECTION = re.compile(
    r"<!--\s*(?:SECTION:)?(?P<name>[A-Z_]+):BEGIN\s*-->(?P<body>.*?)"
    r"<!--\s*(?:SECTION:)?(?P=name):END\s*-->",
    re.S,
)
FRONTMATTER = re.compile(r"\A---\r?\n(?P<fm>.*?)\r?\n---\r?\n(?P<body>.*)\Z", re.S)
# Sections worth carrying across, in the order they should appear in the Kaneo body.
# Both dialects' names for the same section appear here; first present wins its heading.
CARRY = (
    "DESCRIPTION",
    "ACCEPTANCE_CRITERIA",
    "AC",
    "IMPLEMENTATION_PLAN",
    "PLAN",
    "IMPLEMENTATION_NOTES",
    "NOTES",
    "FINAL_SUMMARY",
    "COMMENTS",
)
# Marker names whose title-cased form would mislabel the section on the board.
CARRY_HEADINGS = {
    "AC": "Acceptance Criteria",
    "PLAN": "Implementation Plan",
    "NOTES": "Implementation Notes",
}
# Marker pairs naming the same section across dialects — carry whichever appears first.
CARRY_SYNONYMS = {
    "AC": "ACCEPTANCE_CRITERIA",
    "PLAN": "IMPLEMENTATION_PLAN",
    "NOTES": "IMPLEMENTATION_NOTES",
}
# Backlog.md layouts differ per repo and the difference is silent: one repo keeps finished
# work in tasks/ with status Done, another moves it to completed/, a third nests
# archive/tasks/. A fixed list that happens to match the repo you tested on drops the rest
# without a word — 42 of 73 items in one real repo. Hence: known folders map to a kind,
# `archive` is excluded by default because the owner filed it out of view on purpose, and
# ANY other folder holding .md files is reported rather than guessed at.
SOURCES = (
    ("tasks", "TASK"),
    ("completed", "TASK"),
    ("drafts", "DRAFT"),
    ("decisions", "DECISION"),
    ("docs", "DOC"),
)
ARCHIVE_DIR = "archive"
PRIORITIES = ("low", "medium", "high")
# Kaneo requires a colour on every label; used only when creating one that does not exist.
LABEL_COLOR = "#6b7280"

# Kaneo has no document type — a board holds tasks. Filing documents on it anyway means
# the only thing that can carry "what kind of document is this" is a label, so documents
# get two: DOC on every one of them (the umbrella filter, the whole point of the exercise)
# plus at most one kind below. Same shape as a well-run backlog's one-area-plus-one-signal
# rule, and deliberately closed — an open vocabulary filters no better than the `other` it
# replaces.
#
# UPPERCASE on purpose, and it is the whole readability trick: a board mixes two
# taxonomies that answer different questions. Lowercase says where work lands and what
# kind it is (frontend, bug, chore); UPPERCASE says what kind of document this is. Casing
# tells them apart at a glance in a filter list, with no prefix and no nesting — which
# Kaneo's flat label model does not offer anyway.
DOC_LABEL = "DOC"
DOC_KINDS = {
    "DECISION": "#8b5cf6",     # a ruling, with consequences
    "SPEC": "#0ea5e9",         # a contract something else is built against
    "GUIDE": "#22c55e",        # how to carry out a procedure
    "REFERENCE": "#64748b",    # durable facts and pointers
    "RESEARCH": "#f59e0b",     # an investigation or comparison writeup
    "INCIDENT": "#ef4444",     # what happened, and what it cost
    "REGISTER": "#14b8a6",     # a living table someone updates
}
# Backlog.md's doc `type:` field, mapped onto the above. `other` is deliberately absent:
# it is the majority value in real repos and carries no information, so those documents
# get the umbrella label and are listed by `discover` for a human to classify. Guessing a
# kind from the title would put a wrong, confident label on the ones hardest to re-find.
DOC_TYPE_MAP = {"specification": "SPEC", "guide": "GUIDE", "reference": "REFERENCE"}

# The lowercase half: what KIND of work, closed and shared by every repo because it is
# Backlog.md's own `type:` axis. Per-repo area labels are deliberately dropped — one repo
# alone carried 52 (`area: agent`, `size/L`, `platform-opportunity`), and a central board
# whose label list is the union of every repo's local habits filters worse than one with
# fourteen labels that mean the same thing everywhere. `--keep-source-labels` opts out.
WORK_TYPES = {
    "feature": "#3b82f6",
    "bug": "#ef4444",
    "chore": "#6b7280",
    "docs": "#0ea5e9",
    "test": "#22c55e",
    "spike": "#a855f7",
}
# Common synonyms seen in the wild, folded into the closed set rather than carried.
WORK_ALIASES = {
    "enhancement": "feature", "documentation": "docs", "testing": "test",
    "task": "chore", "maintenance": "chore", "tooling": "chore",
}


# Set once from the CLI; read inside parse_task_file, which has no argument for it.
KEEP_SOURCE_LABELS = [False]


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
    parts = []
    carried = set()
    for name in CARRY:
        canonical = CARRY_SYNONYMS.get(name, name)
        if not sections.get(name) or canonical in carried:
            continue
        carried.add(canonical)
        heading = CARRY_HEADINGS.get(name, name.replace("_", " ").title())
        parts.append(f"## {heading}\n\n{sections[name]}")
    body = "\n\n".join(parts)
    if not body:
        # No marked sections (hand-written or an older Backlog.md): keep the whole body
        # rather than silently importing an empty description.
        body = match.group("body").strip()
    meta = frontmatter_metadata(fields)
    if meta:
        body = f"{body}\n\n{meta}" if body else meta
    labels = [str(v) for v in (fields.get("labels") or []) if str(v).strip()]
    if fields.get("type") and kind != "DOC":
        # On a task, `type:` is the kind of work (feature/bug/chore) and makes a good
        # label. On a document it is the doc type, which is mapped to a kind label below —
        # copying it raw as well would put a literal `other` and a duplicate
        # `specification` alongside `spec` on the board.
        labels.append(str(fields["type"]))
    labels = [
        WORK_ALIASES.get(name.lower(), name.lower())
        for name in labels
        if WORK_ALIASES.get(name.lower(), name.lower()) in WORK_TYPES
    ] if not KEEP_SOURCE_LABELS[0] else labels
    doc_labels = []
    if kind in ("DECISION", "DOC"):
        # Matches the convention the reference board already uses: a document is a task in
        # the Document lane, filterable by label once its original Proposed/Accepted
        # wording is no longer a status. Kept apart from the file's own labels because
        # only these get their casing forced — see attach_labels.
        doc_labels.append(DOC_LABEL)
        if kind == "DECISION":
            doc_labels.append("DECISION")
        else:
            mapped = DOC_TYPE_MAP.get(str(fields.get("type", "")).strip().lower())
            if mapped:
                doc_labels.append(mapped)
    priority = str(fields.get("priority", "") or "").lower()
    return {
        "source_id": str(fields.get("id") or path.rsplit("/", 1)[-1]),
        "kind": kind,
        "title": str(fields.get("title") or "(untitled)").strip(),
        "status": str(fields.get("status") or "").strip(),
        "priority": priority if priority in PRIORITIES else "medium",
        "labels": sorted(set(labels)),
        "raw_labels": sorted(set(labels)),
        "doc_labels": sorted(set(doc_labels)),
        "body": body,
        "path": path,
    }


def frontmatter_metadata(fields):
    """Frontmatter worth keeping that has no Kaneo field: milestone, dependencies, references.

    Kaneo has no milestone primitive and relations are attached after import, so these
    ride in the body under one heading — dropping them silently loses the issue links
    and the outcome grouping the source cards carried.
    """
    lines = []
    if str(fields.get("milestone") or "").strip():
        lines.append(f"Milestone: {str(fields['milestone']).strip()}")
    deps = fields.get("dependencies") or []
    if isinstance(deps, str):
        deps = [deps]
    deps = [str(d).strip() for d in deps if str(d).strip()]
    if deps:
        lines.append("Dependencies: " + ", ".join(deps))
    refs = fields.get("references") or []
    if isinstance(refs, str):
        refs = [refs]
    refs = [str(r).strip() for r in refs if str(r).strip()]
    if refs:
        lines.append("References:\n" + "\n".join(f"- {r}" for r in refs))
    if not lines:
        return ""
    return "## Source Metadata\n\n" + "\n\n".join(lines)


def path_read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _markdown_under(directory):
    """Every .md below a directory, recursively — archive/ nests its tasks a level down."""
    found = []
    for base, _, names in os.walk(directory):
        found.extend(os.path.join(base, n) for n in names if n.endswith(".md"))
    return sorted(found)


def read_backlog(root, include_archive=False):
    """Every backlog item under <root>/backlog, sorted for a stable import order."""
    records = []
    folders = list(SOURCES) + ([(ARCHIVE_DIR, "TASK")] if include_archive else [])
    for folder, kind in folders:
        for path in _markdown_under(os.path.join(root, "backlog", folder)):
            record = parse_task_file(path, kind)
            if record:
                records.append(record)
    return records


def unhandled_folders(root, include_archive=False):
    """Folders under backlog/ holding .md files that no source claims.

    Reported rather than swept in: an unrecognised folder might be templates or notes, and
    importing it because it happens to contain markdown is how a board fills with junk.
    """
    backlog = os.path.join(root, "backlog")
    if not os.path.isdir(backlog):
        return {}
    claimed = {name for name, _ in SOURCES} | ({ARCHIVE_DIR} if include_archive else set())
    unclaimed = {}
    for name in sorted(os.listdir(backlog)):
        path = os.path.join(backlog, name)
        if not os.path.isdir(path) or name in claimed:
            continue
        count = len(_markdown_under(path))
        if count:
            unclaimed[name] = count
    return unclaimed


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


def resolve_lane(wanted, columns):
    """A column's slug, matched on slug or display name. None if the board has no such lane."""
    target = slugify(wanted)
    for column in columns:
        if column["slug"] == wanted or column["slug"] == target:
            return column["slug"]
    for column in columns:
        if slugify(column["name"]) == target:
            return column["slug"]
    return None


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
    # Keyed case-insensitively so an import of `research` reuses an existing `RESEARCH`
    # rather than seeding a second label that reads as the same one and filters as two.
    known = {
        str(label["name"]).lower(): (str(label["name"]), label.get("color") or LABEL_COLOR)
        for label in existing_labels
    }
    # The document vocabulary is owned here, so its declared UPPERCASE wins over whatever
    # casing happens to be on the board. Work labels are the repo's, so those keep the
    # board's existing casing — reusing `RESEARCH` rather than seeding a `research`.
    owned = {name.lower(): (name, color) for name, color in
             {DOC_LABEL: "#6366f1", **DOC_KINDS}.items()}
    palette = dict(WORK_TYPES)
    attached = 0
    for record, task_id in created:
        # A repo may legitimately use `decision` or `research` as ORDINARY task labels
        # (api-agents does). Forcing those to the document vocabulary's uppercase would
        # relabel plain tasks as documents, so only labels this script added are forced.
        for name in record["labels"]:
            canonical, color = known.get(
                name.lower(), (name, palette.get(name.lower(), LABEL_COLOR))
            )
            _post_label(workspace_id, task_id, canonical, color)
            attached += 1
        for name in record.get("doc_labels", []):
            canonical, color = owned.get(name.lower(), (name, LABEL_COLOR))
            _post_label(workspace_id, task_id, canonical, color)
            attached += 1
    return attached


def _post_label(workspace_id, task_id, name, color):
    api("POST", "/label", {"name": name, "color": color,
                           "workspaceId": workspace_id, "taskId": task_id})


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
    records = read_backlog(args.repo, args.include_archive) if args.repo else []
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
        vague = [
            r for r in records
            if r["kind"] == "DOC" and not (set(r["labels"]) & set(DOC_KINDS))
        ]
        if vague:
            # These import with the umbrella `doc` label and no kind. Listed rather than
            # guessed at: a wrong kind label is worse than none on exactly the documents
            # that are hardest to find again.
            print(f"  {len(vague)} document(s) have no recognisable kind — label by hand after:")
            for record in vague:
                print(f"    {record['source_id']}: {record['title'][:58]}")
    else:
        print("  backlog: none found — greenfield, nothing to import")
    if args.repo:
        for name, count in unhandled_folders(args.repo, args.include_archive).items():
            flag = " (pass --include-archive to import)" if name == ARCHIVE_DIR else ""
            print(f"  NOT imported: backlog/{name}/ holds {count} markdown file(s){flag}")

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


SOURCE_ID = re.compile(r"\b(TASK|DRAFT|DECISION|decision|doc|DOC)-[0-9]+(?:\.[0-9]+)?\b")


def cmd_adopt(args):
    """Seed the state file from tasks already on the board, so apply does not duplicate.

    The realistic starting point is a half-finished migration: someone moved a slice by
    hand before there was a script. Those tasks are only recoverable if their source id
    survived into the title, which is exactly why apply writes `TASK-083: ...` titles by
    default. Writes nothing to the board.
    """
    tasks = get_tasks(args.project_id)
    state = load_state(args.state)
    found, skipped = {}, 0
    for task in tasks:
        match = SOURCE_ID.search(task.get("title") or "")
        if not match:
            skipped += 1
            continue
        # Export does not carry task ids, so record the title. apply only needs to know
        # the source id is spoken for; the value is for a human reading the state file.
        found[match.group(0)] = task.get("title")
    state["imported"].update({k: v for k, v in found.items() if k not in state["imported"]})
    print(f"{len(tasks)} on board, {len(found)} carry a source id, {skipped} do not")
    if skipped:
        print("  (unmatched tasks are left alone — they were not created from a backlog file)")
    if not args.yes:
        print("-- dry run, re-run with --yes to write the state file --")
        return 0
    save_state(args.state, state)
    print(f"state file now claims {len(state['imported'])} source ids: {args.state}")
    return 0


def cmd_labels(args):
    """Provision the document label vocabulary on a workspace, idempotently.

    Labels are workspace-scoped, so this runs once per workspace and every project in it
    can filter by the same set. A workspace label is one created with no `taskId`.
    """
    # This endpoint returns one row per ATTACHMENT, not per label: a name attached to 81
    # tasks comes back 81 times. Compare on distinct lowercased names — matching
    # case-sensitively invents a `research` next to an existing `RESEARCH`, and the two
    # look like one label in the UI while filtering as two.
    rows = unwrap(api("GET", f"/label/workspace/{args.workspace}")) or []
    existing = {str(label["name"]) for label in rows}
    folded = {name.lower(): name for name in existing}
    wanted = {DOC_LABEL: "#6366f1", **DOC_KINDS}
    missing = {name: color for name, color in wanted.items() if name not in existing}
    # A label that exists in the wrong case is NOT missing — creating it would leave two
    # that read as one and filter as two. Report it instead; re-pointing existing
    # attachments is a data migration, not a provisioning step.
    collisions = {
        name: folded[name.lower()]
        for name in missing
        if name.lower() in folded and folded[name.lower()] != name
    }
    for name in collisions:
        missing.pop(name, None)
    print(
        f"workspace {args.workspace}: {len(folded)} distinct labels across {len(rows)} "
        f"attachments, {len(missing)} to create"
    )
    for name, found in sorted(collisions.items()):
        print(f"  ! {found!r} exists where {name!r} is wanted — re-point it, do not duplicate")
    if not missing:
        return 0
    if not args.yes:
        print("-- dry run, re-run with --yes to write --")
        for name in sorted(missing):
            print(f"  + {name}")
        return 0
    for name, color in sorted(missing.items()):
        api("POST", "/label", {"name": name, "color": color, "workspaceId": args.workspace})
        print(f"  created {name}")
    return 0


def cmd_apply(args):
    records = read_backlog(args.repo, args.include_archive)
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

    # Resolve by slug OR display name: a column created as "Documents" and later renamed
    # keeps slug `documents`, while one created as "Document" gets `document`. Two boards
    # meant to match then disagree on the value the API wants, and only the slug works.
    lanes, unknown = {}, {}
    requested = {
        "DRAFT": args.draft_lane,
        "DECISION": args.decision_lane,
        "DOC": args.doc_lane,
    }
    for kind in {r["kind"] for r in pending} & set(requested):
        wanted = requested[kind]
        found = resolve_lane(wanted, columns)
        if found:
            lanes[kind] = found
        else:
            unknown[kind] = wanted
    if unknown:
        print(
            "error: no lane matches "
            + ", ".join(f"{k}={v!r}" for k, v in sorted(unknown.items()))
            + f". Available slugs: {sorted(c['slug'] for c in columns)}",
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
    disc.add_argument("--keep-source-labels", action="store_true",
                      help="carry every label the repo used instead of the closed set")
    disc.add_argument("--include-archive", action="store_true",
                      help="also import backlog/archive, which the owner filed out of view")
    disc.set_defaults(func=cmd_discover)

    app = sub.add_parser("apply", help="import a repo's backlog onto an existing project")
    app.add_argument("--repo", required=True)
    app.add_argument("--project-id", required=True, help="never created for you; discover first")
    app.add_argument("--state", help="JSON id-map making re-runs resumable")
    app.add_argument("--create-columns", action="store_true", help="provision missing lanes")
    app.add_argument("--draft-lane", default="to-do",
                     help="lane for drafts, whose status is not a workflow state")
    app.add_argument("--decision-lane", default="document",
                     help="lane for decisions; they also get a `decision` label")
    app.add_argument("--doc-lane", default="document",
                     help="lane for backlog/docs; they also get a `doc` label")
    app.add_argument("--no-title-prefix", dest="title_prefix", action="store_false",
                     help="omit the source id from imported titles")
    app.add_argument("--keep-source-labels", action="store_true",
                     help="carry every label the repo used instead of the closed set")
    app.add_argument("--include-archive", action="store_true",
                     help="also import backlog/archive, which the owner filed out of view")
    app.add_argument("--yes", action="store_true", help="actually write (default is a dry run)")
    app.set_defaults(func=cmd_apply, title_prefix=True)

    ado = sub.add_parser("adopt", help="claim tasks already on the board so apply skips them")
    ado.add_argument("--project-id", required=True)
    ado.add_argument("--state", required=True, help="state file to seed")
    ado.add_argument("--yes", action="store_true", help="actually write the state file")
    ado.set_defaults(func=cmd_adopt)

    lab = sub.add_parser("labels", help="provision the document label vocabulary")
    lab.add_argument("--yes", action="store_true", help="actually write (default is a dry run)")
    lab.set_defaults(func=cmd_labels)

    args = parser.parse_args(argv)
    KEEP_SOURCE_LABELS[0] = bool(getattr(args, "keep_source_labels", False))
    try:
        return args.func(args)
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
