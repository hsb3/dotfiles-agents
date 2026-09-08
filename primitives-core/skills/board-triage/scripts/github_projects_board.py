#!/usr/bin/env python3
"""GitHub Projects (v2) adapter for board-triage: export a snapshot, apply a changeset.

Implements the adapter contract in the skill's SKILL.md §2 against a Projects v2 board.

    github_projects_board.py export -o acme -n 8 --out board-snapshot.json
    github_projects_board.py apply -o acme -n 8 --changeset changeset.tsv           # dry-run
    github_projects_board.py apply -o acme -n 8 --changeset changeset.tsv --apply   # write

Config: --owner and --number (--owner-type org for an org-owned board). Auth is `gh`'s own,
run with GITHUB_TOKEN unset: a repo-scoped GITHUB_TOKEN shadows the project-scoped keyring
login and every Projects query fails INSUFFICIENT_SCOPES. Needs `gh auth refresh -s project`.

Why a script and not raw `gh` calls per changeset row: apply must re-resolve issue number ->
project item id from a fresh pull every run, same discipline as every other adapter, so a
stale changeset can't clobber a value someone else already changed underneath it. The
snapshot carries each field's legal values too, so triage never needs a second read command.

Stdlib only, no install — shells out to the `gh` binary already on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

# dataTypes updateProjectV2ItemFieldValue can write. Built-ins like Labels / Milestone /
# Assignees are issue-native, so they are neither settable nor gridded onto an item.
SETTABLE = {"SINGLE_SELECT", "TEXT", "NUMBER", "DATE", "ITERATION"}

# Anything else (including a state the API grows later) stays "open": an item wrongly
# marked done vanishes from triage, which is the expensive direction of this mistake.
DONE_STATES = {"CLOSED", "MERGED"}

# What a legal changeset value looks like for a field with no enumerable choices.
HINTS = {"DATE": "YYYY-MM-DD", "NUMBER": "<number>", "TEXT": "<text>"}

PROJECT_Q = "query($o:String!,$n:Int!){ %SCOPE%(login:$o){ projectV2(number:$n){ id title } } }"

# fields(first:50) and fieldValues(first:30) are unpaginated practical limits — a board with
# more fields, or an item with more field values, would silently truncate.
FIELDS_Q = """
query($id:ID!){ node(id:$id){ ... on ProjectV2 { fields(first:50){ nodes{
  __typename
  ... on ProjectV2FieldCommon { id name dataType }
  ... on ProjectV2SingleSelectField { id name options { id name } }
  ... on ProjectV2IterationField { id name configuration {
      iterations { id title } completedIterations { id title } } }
}}}}}
"""

ITEMS_Q = """
query($id:ID!,$after:String){ node(id:$id){ ... on ProjectV2 {
  items(first:100, after:$after){
    pageInfo{ hasNextPage endCursor }
    nodes{
      id
      content{
        __typename
        ... on Issue { number title state repository{ nameWithOwner }
          labels(first:20){ nodes{ name } } milestone{ title } parent{ number } }
        ... on PullRequest { number title state repository{ nameWithOwner }
          labels(first:20){ nodes{ name } } milestone{ title } }
        ... on DraftIssue { title }
      }
      fieldValues(first:30){ nodes{
        __typename
        ... on ProjectV2ItemFieldSingleSelectValue { name field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldTextValue   { text   field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldNumberValue { number field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldDateValue   { date   field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldIterationValue { title field{ ... on ProjectV2FieldCommon{ name } } }
      }}
    }
  }
}}}
"""

_SET = "mutation($p:ID!,$i:ID!,$f:ID!,%s){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{%s}}){projectV2Item{id}}}"
CLEAR_M = "mutation($p:ID!,$i:ID!,$f:ID!){clearProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f}){projectV2Item{id}}}"
SELECT_M = _SET % ("$o:String!", "singleSelectOptionId:$o")
ITERATION_M = _SET % ("$o:String!", "iterationId:$o")
DATE_M = _SET % ("$d:Date!", "date:$d")
NUMBER_M = _SET % ("$nn:Float!", "number:$nn")
TEXT_M = _SET % ("$t:String!", "text:$t")


# --- gh ---------------------------------------------------------------------
def _gh(*args, check=True):
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if check and proc.returncode != 0:
        sys.exit(f"gh {' '.join(args[:2])} failed:\n{proc.stderr.strip()}")
    return proc.returncode, proc.stdout, proc.stderr


def _graphql(query, *raw, **fvars):
    args = ["api", "graphql", "-f", "query=" + query]
    for key, value in fvars.items():
        args += ["-f", f"{key}={value}"]
    args += list(raw)  # caller passes "-F", "n=9" for Int!/Float! vars
    out = json.loads(_gh(*args)[1])
    if "data" not in out:  # error-only response (rate limit, transient failure)
        sys.exit(f"graphql: no data in response: {out.get('errors') or out}")
    return out


# --- pure logic (the part worth testing) ------------------------------------
def field_value(node):
    """One fieldValue node -> its scalar. Keyed on __typename so "" and 0 survive as values."""
    kind = node.get("__typename", "")
    for suffix, key in (
        ("SingleSelectValue", "name"),
        ("TextValue", "text"),
        ("NumberValue", "number"),
        ("DateValue", "date"),
        ("IterationValue", "title"),
    ):
        if kind.endswith(suffix):
            return node.get(key)
    return None


def build_fields(nodes):
    """Field nodes -> {name: {id, dataType, choices}} in board order.

    `choices` is [(value, id)] for single-selects and iterations alike; completed
    iterations are included, since a closed bucket is still a legal changeset value.
    """
    fields = {}
    for node in nodes:
        if not node:  # the API returns nulls for field types the query does not fragment
            continue
        config = node.get("configuration") or {}
        buckets = (config.get("iterations") or []) + (config.get("completedIterations") or [])
        fields[node["name"]] = {
            "id": node["id"],
            "dataType": node.get("dataType"),
            "choices": [(o["name"], o["id"]) for o in node.get("options") or []]
            + [(it["title"], it["id"]) for it in buckets],
        }
    return fields


def choice_id(fdef, value):
    """Option / iteration id for a changeset value, or None if the board has no such choice."""
    return next((cid for name, cid in fdef["choices"] if name.lower() == value.lower()), None)


def build_snapshot(board, fields, nodes):
    """Contract-shaped snapshot from the project, its fields, and every item node."""
    grid = [name for name, fdef in fields.items() if fdef["dataType"] in SETTABLE]
    items = []
    for node in nodes:
        content = node.get("content") or {}
        if content.get("number") is None:  # a draft issue has no durable key
            continue
        cells = {name: None for name in grid}
        for value_node in (node.get("fieldValues") or {}).get("nodes", []):
            name = (value_node.get("field") or {}).get("name")
            if name in cells:
                cells[name] = field_value(value_node)
        items.append(
            {
                "key": content["number"],
                "id": node["id"],
                "title": content.get("title"),
                "state": "done" if (content.get("state") or "").upper() in DONE_STATES else "open",
                "labels": [lbl["name"] for lbl in (content.get("labels") or {}).get("nodes", [])],
                "milestone": (content.get("milestone") or {}).get("title"),
                "parent": (content.get("parent") or {}).get("number"),
                "repo": (content.get("repository") or {}).get("nameWithOwner"),
                "fields": cells,
            }
        )
    items.sort(key=lambda item: item["key"])
    return {
        "board": board,
        "fields": {
            name: {"options": [c for c, _ in fields[name]["choices"]]
                   or [HINTS.get(fields[name]["dataType"], "<value>")]}
            for name in grid
        },
        "items": items,
    }


def resolve_field(token, fields):
    """Match a changeset field token against the board's LIVE field names (case-insensitive,
    space/underscore-insensitive). Works for any current or future field — no hardcoded list."""

    def norm(name):
        return name.lower().replace("_", "").replace(" ", "")

    want = norm(token)
    return next((name for name in fields if norm(name) == want), None)


def values_equal(current, value):
    """Changeset string vs live value: case-insensitive text match, with a numeric
    fallback so a NUMBER field holding 3.0 matches the changeset's "3"."""
    if current is None:
        return False
    if str(current).lower() == value.lower():
        return True
    try:
        return float(current) == float(value)
    except (TypeError, ValueError):
        return False


def parse_changeset(text):
    """TSV -> [(key, field, value)], skipping blanks, comments, and either header spelling."""
    rows = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            sys.exit(f"changeset line {lineno}: need key<TAB>field<TAB>value")
        key, field = parts[0].strip(), parts[1].strip().lower()
        value = "\t".join(parts[2:]).strip()
        if field == "field" and key.lower() in ("key", "issue"):
            continue  # header; `issue` is the older spelling, kept so old changesets still run
        rows.append((key, field, value))
    return rows


def mutation(fdef, project_id, item_id, value):
    """One cell write -> (query, fvars, raw argv) for _graphql, or (None, problem, ())."""
    common = {"p": project_id, "i": item_id, "f": fdef["id"]}
    kind = fdef["dataType"]
    if value == "":
        return CLEAR_M, common, ()
    if kind in ("SINGLE_SELECT", "ITERATION"):
        cid = choice_id(fdef, value)
        if cid is None:
            return None, f"no {'option' if kind == 'SINGLE_SELECT' else 'iteration'} '{value}'", ()
        return (SELECT_M if kind == "SINGLE_SELECT" else ITERATION_M), {**common, "o": cid}, ()
    if kind == "DATE":
        return DATE_M, {**common, "d": value}, ()
    if kind == "NUMBER":
        return NUMBER_M, common, ("-F", f"nn={value}")
    return TEXT_M, {**common, "t": value}, ()


def untriaged(snapshot):
    """How many items carry no priority, or None if this board has no priority field."""
    name = resolve_field("priority", snapshot["fields"])
    if name is None:
        return None
    return sum(1 for item in snapshot["items"] if item["fields"].get(name) is None)


# --- commands ---------------------------------------------------------------
def fetch_snapshot(owner, number, owner_type):
    """Fresh read of the whole board -> (contract snapshot, field defs with their ids)."""
    scope = "user" if owner_type == "user" else "organization"
    payload = _graphql(PROJECT_Q.replace("%SCOPE%", scope), "-F", f"n={number}", o=owner)
    project = (payload.get("data", {}).get(scope) or {}).get("projectV2")
    if not project:
        sys.exit(f"project {owner}#{number} not found (check --owner-type)")
    project_id = project["id"]

    fields = build_fields(_graphql(FIELDS_Q, id=project_id)["data"]["node"]["fields"]["nodes"])

    nodes, cursor = [], None
    while True:
        after = {"after": cursor} if cursor else {}
        page = _graphql(ITEMS_Q, id=project_id, **after)["data"]["node"]["items"]
        nodes.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    board = {
        "name": project.get("title"),
        "backend": "github-projects",
        "owner": owner,
        "number": number,
        "id": project_id,
    }
    return build_snapshot(board, fields, nodes), fields


def cmd_export(args):
    snapshot, _ = fetch_snapshot(args.owner, args.number, args.owner_type)
    text = json.dumps(snapshot, indent=1, sort_keys=False)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(text + "\n")
        blank = untriaged(snapshot)
        note = f" ({blank} untriaged)" if blank is not None else ""
        print(f"{len(snapshot['items'])} items{note} -> {args.out}")
    else:
        print(text)
    return 0


def _dependency_row(args, issue, field, value, tag):
    """blocked_by / blocking: not project cells at all — they live on the REST issue graph."""
    if not args.repo:
        print(f"SKIP  {tag}: --repo required for {field}", file=sys.stderr)
        return "skipped"
    rc, out, _ = _gh("api", f"repos/{args.repo}/issues/{value}", "--jq", ".id", check=False)
    if rc != 0:
        print(f"FAIL  {tag}: issue #{value} not found in {args.repo}", file=sys.stderr)
        return "failed"
    if not args.apply:
        print(f"DRY   would POST {field}: #{issue} <- #{value}")
        return "changed"
    rc, _, err = _gh(
        "api", "-X", "POST",
        f"repos/{args.repo}/issues/{issue}/dependencies/{field}",
        "-F", f"issue_id={out.strip()}",
        check=False,
    )
    if rc != 0:
        print(f"FAIL  {tag}: {err.strip()}", file=sys.stderr)
        return "failed"
    print(f"SET   {tag}")
    return "changed"


def cmd_apply(args):
    with open(args.changeset) as handle:
        rows = parse_changeset(handle.read())
    snapshot, fields = fetch_snapshot(args.owner, args.number, args.owner_type)
    project_id = snapshot["board"]["id"]
    items = {item["key"]: item for item in snapshot["items"]}
    tally = {"changed": 0, "unchanged": 0, "skipped": 0, "failed": 0}

    for key, field, value in rows:
        try:
            issue = int(key.lstrip("#"))
        except ValueError:
            print(f"SKIP  row key={key!r}: not an integer", file=sys.stderr)
            tally["skipped"] += 1
            continue
        tag = f"#{issue} {field}={value or '(clear)'}"

        if field in ("blocked_by", "blocking"):
            tally[_dependency_row(args, issue, field, value, tag)] += 1
            continue
        if issue not in items:
            print(f"SKIP  {tag}: not on board", file=sys.stderr)
            tally["skipped"] += 1
            continue
        name = resolve_field(field, fields)
        if not name:
            print(f"SKIP  {tag}: no field matches '{field}'", file=sys.stderr)
            tally["skipped"] += 1
            continue
        fdef = fields[name]
        if fdef["dataType"] not in SETTABLE:
            print(f"SKIP  {tag}: field '{name}' ({fdef['dataType']}) not settable via project API",
                  file=sys.stderr)
            tally["skipped"] += 1
            continue

        current = items[issue]["fields"].get(name)
        if value == "" and current in (None, ""):
            print(f"OK    {tag}: already clear")
            tally["unchanged"] += 1
            continue
        if value and values_equal(current, value):
            print(f"OK    {tag}: unchanged")
            tally["unchanged"] += 1
            continue
        # Resolved before the dry-run branch: a preview that green-lights a write the
        # board will reject is worse than no preview at all.
        query, extra, raw = mutation(fdef, project_id, items[issue]["id"], value)
        if query is None:
            print(f"FAIL  {tag}: {extra}", file=sys.stderr)
            tally["failed"] += 1
            continue
        if not args.apply:
            print(f"DRY   would set {tag} (was {current})")
            tally["changed"] += 1
            continue
        try:
            _graphql(query, *raw, **extra)
        except SystemExit as exc:
            print(f"FAIL  {tag}: {exc}", file=sys.stderr)
            tally["failed"] += 1
            continue
        print(f"SET   {tag} (was {current})")
        tally["changed"] += 1

    verb = "applied" if args.apply else "planned (dry-run)"
    print(
        f"\n{verb}: {tally['changed']} changed · {tally['unchanged']} unchanged · "
        f"{tally['skipped']} skipped · {tally['failed']} failed",
        file=sys.stderr,
    )
    if not args.apply and tally["changed"]:
        print("re-run with --apply to write.", file=sys.stderr)
    # A SKIP is a failure: the changeset asked for a cell that did not get written, and an
    # operator scripting `apply || abort` has to see that. The resolvable rows still applied.
    return 1 if tally["failed"] or tally["skipped"] else 0


def _board_args(parser):
    parser.add_argument("-o", "--owner", required=True, help="user or org login")
    parser.add_argument("-n", "--number", type=int, required=True, help="project number")
    parser.add_argument("--owner-type", choices=["user", "org"], default="user")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="write a contract-shaped snapshot")
    _board_args(export)
    export.add_argument("--out", help="file to write (default: stdout)")
    export.set_defaults(func=cmd_export)
    apply_ = sub.add_parser("apply", help="apply a changeset TSV (dry-run by default)")
    _board_args(apply_)
    apply_.add_argument("--changeset", required=True, help="TSV: key<TAB>field<TAB>value")
    apply_.add_argument("--repo", help="owner/name, required for blocked_by / blocking rows")
    apply_.add_argument("--apply", action="store_true", help="actually write")
    apply_.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
