#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""board-export — compact snapshot of a GitHub Project (v2), no issue bodies.

The READ half of the export -> analyze -> apply loop. Emits one JSON file holding
the project's fields (with option ids), iteration buckets, and every item with its
current field values + light context (labels, milestone, parent). Deliberately
omits issue bodies so the output stays small enough to hand to an analyst / agent.

Usage:
    ./board-export.py --owner hsb3 --number 8 --out board-snapshot.json
    ./board-export.py -o hsb3 -n 8                 # prints to stdout

Auth: shells out to `gh` with GITHUB_TOKEN UNSET (a repo-scoped GITHUB_TOKEN shadows
the project-scoped keyring login -> INSUFFICIENT_SCOPES). Needs `gh auth refresh -s project`.
"""

from __future__ import annotations
import argparse, json, os, subprocess, sys


def gh(*args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    r = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args[:2])} failed:\n{r.stderr.strip()}")
    return r.stdout


def graphql(query: str, **fvars: str) -> dict:
    args = ["api", "graphql", "-f", "query=" + query]
    for k, v in fvars.items():
        args += ["-f", f"{k}={v}"]
    return json.loads(gh(*args))


PROJECT_ID_Q = """
query($o:String!,$n:Int!){ %SCOPE%(login:$o){ projectV2(number:$n){ id title } } }
"""

# fields(first:50) and fieldValues(first:30) are unpaginated practical limits — a board
# with more fields, or an item with more field values, would silently truncate.
FIELDS_Q = """
query($id:ID!){ node(id:$id){ ... on ProjectV2 { fields(first:50){ nodes{
  __typename
  ... on ProjectV2FieldCommon { id name dataType }
  ... on ProjectV2SingleSelectField { id name options { id name } }
  ... on ProjectV2IterationField { id name configuration {
      iterations { id title startDate } completedIterations { id title startDate } } }
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
        ... on Issue { number title state url repository{ nameWithOwner }
          labels(first:20){ nodes{ name } } milestone{ title } parent{ number } }
        ... on PullRequest { number title state url repository{ nameWithOwner }
          labels(first:20){ nodes{ name } } milestone{ title } }
        ... on DraftIssue { title }
      }
      fieldValues(first:30){ nodes{
        __typename
        ... on ProjectV2ItemFieldSingleSelectValue { name optionId field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldTextValue   { text   field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldNumberValue { number field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldDateValue   { date   field{ ... on ProjectV2FieldCommon{ name } } }
        ... on ProjectV2ItemFieldIterationValue { title iterationId field{ ... on ProjectV2FieldCommon{ name } } }
      }}
    }
  }
}}}
"""


# Field dataTypes that carry a per-item value an agent can read/write.
OPERATING = {"SINGLE_SELECT", "TEXT", "NUMBER", "DATE", "ITERATION"}


def field_value(node: dict):
    """Normalize one fieldValue node to a scalar (option name / text / number / date / iteration title)."""
    t = node.get("__typename", "")
    if t.endswith("SingleSelectValue"):
        return node.get("name")
    if t.endswith("TextValue"):
        return node.get("text")
    if t.endswith("NumberValue"):
        return node.get("number")
    if t.endswith("DateValue"):
        return node.get("date")
    if t.endswith("IterationValue"):
        return node.get("title")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Compact GitHub Project v2 snapshot (no bodies)."
    )
    ap.add_argument("-o", "--owner", required=True, help="user or org login")
    ap.add_argument("-n", "--number", type=int, required=True, help="project number")
    ap.add_argument("--owner-type", choices=["user", "org"], default="user")
    ap.add_argument("--out", help="output JSON path (default: stdout)")
    args = ap.parse_args()

    scope = "user" if args.owner_type == "user" else "organization"
    pj = graphql(
        PROJECT_ID_Q.replace("%SCOPE%", scope), o=args.owner, n=str(args.number)
    )
    proj = (pj.get("data", {}).get(scope) or {}).get("projectV2")
    if not proj:
        sys.exit(f"project {args.owner}#{args.number} not found (check --owner-type)")
    pid = proj["id"]

    fields = []
    for f in graphql(FIELDS_Q, id=pid)["data"]["node"]["fields"]["nodes"]:
        if not f:
            continue
        entry = {
            "name": f.get("name"),
            "id": f.get("id"),
            "dataType": f.get("dataType"),
        }
        if "options" in f:
            entry["options"] = f["options"]
        if "configuration" in f and f["configuration"]:
            entry["iterations"] = (f["configuration"].get("iterations") or []) + (
                f["configuration"].get("completedIterations") or []
            )
        fields.append(entry)

    # Every operating field becomes a column on every item (null when unset) so the
    # snapshot is a complete grid — blanks are visible for triage/diffing.
    op_fields = [f["name"] for f in fields if f.get("dataType") in OPERATING]

    items, cursor = [], None
    while True:
        after = {"after": cursor} if cursor else {}
        page = graphql(ITEMS_Q, id=pid, **after)["data"]["node"]["items"]
        for it in page["nodes"]:
            c = it.get("content") or {}
            if c.get("number") is None:  # skip draft issues
                continue
            vals = {name: None for name in op_fields}
            for fv in it.get("fieldValues", {}).get("nodes", []):
                fld = (fv.get("field") or {}).get("name")
                if fld in vals:
                    vals[fld] = field_value(fv)
            items.append(
                {
                    "number": c["number"],
                    "item_id": it["id"],
                    "title": c.get("title"),
                    "state": c.get("state"),
                    "repo": (c.get("repository") or {}).get("nameWithOwner"),
                    "labels": [
                        l["name"] for l in (c.get("labels", {}) or {}).get("nodes", [])
                    ],
                    "milestone": (c.get("milestone") or {}).get("title"),
                    "parent": (c.get("parent") or {}).get("number"),
                    "fields": vals,
                }
            )
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    out = {
        "project": {
            "owner": args.owner,
            "owner_type": args.owner_type,
            "number": args.number,
            "id": pid,
            "title": proj.get("title"),
        },
        "fields": fields,
        "items": items,
    }
    text = json.dumps(out, indent=2)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(
            f"wrote {args.out}: {len(items)} items, {len(fields)} fields",
            file=sys.stderr,
        )
    else:
        print(text)


if __name__ == "__main__":
    main()
