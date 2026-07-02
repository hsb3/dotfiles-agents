#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""board-fields — dump every field of a GitHub Project (v2) with its allowed values.

The ENUM reference for the export -> analyze -> apply loop: the valid field names and,
for single-select / iteration fields, the allowed option values (with their ids). Use it
to write a changeset that only references real fields and real option names, and to grab
field/option ids for hand-written mutations.

Usage:
    ./board-fields.py -o hsb3 -n 8            # human-readable table
    ./board-fields.py -o hsb3 -n 8 --json     # machine-readable

Auth: shells out to `gh` with GITHUB_TOKEN UNSET (avoids the repo-scope shadowing gotcha).
Needs `gh auth refresh -s project`.
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
    out = json.loads(gh(*args))
    if "data" not in out:  # error-only response (rate limit, transient failure)
        sys.exit(f"graphql: no data in response: {out.get('errors') or out}")
    return out


PROJECT_ID_Q = (
    "query($o:String!,$n:Int!){ %SCOPE%(login:$o){ projectV2(number:$n){ id title } } }"
)

# fields(first:50) is an unpaginated practical limit — a board with more fields would
# silently truncate.
FIELDS_Q = """
query($id:ID!){ node(id:$id){ ... on ProjectV2 { fields(first:50){ nodes{
  __typename
  ... on ProjectV2FieldCommon { id name dataType }
  ... on ProjectV2SingleSelectField { id name options { id name } }
  ... on ProjectV2IterationField { id name configuration {
      duration startDate
      iterations { id title startDate }
      completedIterations { id title startDate } } }
}}}}}
"""


def collect(owner: str, number: int, owner_type: str) -> dict:
    scope = "user" if owner_type == "user" else "organization"
    pj = graphql(PROJECT_ID_Q.replace("%SCOPE%", scope), o=owner, n=str(number))
    proj = (pj.get("data", {}).get(scope) or {}).get("projectV2")
    if not proj:
        sys.exit(f"project {owner}#{number} not found (check --owner-type)")
    pid = proj["id"]

    out = {
        "project": {
            "owner": owner,
            "number": number,
            "id": pid,
            "title": proj.get("title"),
        },
        "fields": [],
    }
    for f in graphql(FIELDS_Q, id=pid)["data"]["node"]["fields"]["nodes"]:
        if not f:
            continue
        entry = {
            "name": f.get("name"),
            "id": f.get("id"),
            "dataType": f.get("dataType"),
        }
        if "options" in f:
            entry["options"] = f["options"]  # [{id,name}]
        cfg = f.get("configuration")
        if cfg:
            its = (cfg.get("iterations") or []) + (cfg.get("completedIterations") or [])
            entry["iterations"] = its  # [{id,title,startDate}]
            entry["duration"] = cfg.get("duration")
        out["fields"].append(entry)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Dump GitHub Project v2 fields + allowed values (enum reference)."
    )
    ap.add_argument("-o", "--owner", required=True)
    ap.add_argument("-n", "--number", type=int, required=True)
    ap.add_argument("--owner-type", choices=["user", "org"], default="user")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON")
    args = ap.parse_args()

    data = collect(args.owner, args.number, args.owner_type)
    if args.json:
        print(json.dumps(data, indent=2))
        return

    p = data["project"]
    print(f"{p['title']}  ({p['owner']}#{p['number']})  id={p['id']}\n")
    for f in data["fields"]:
        print(f"• {f['name']}  [{f['dataType']}]  id={f['id']}")
        if f.get("options"):
            for o in f["options"]:
                print(f"      {o['name']:<16} id={o['id']}")
        if f.get("iterations"):
            for it in f["iterations"]:
                print(
                    f"      {it['title']:<16} id={it['id']}  start={it.get('startDate', '')}"
                )
    print(
        f"\n{len(data['fields'])} fields. "
        "Single-select/iteration values above are the only valid changeset values for those fields."
    )


if __name__ == "__main__":
    main()
