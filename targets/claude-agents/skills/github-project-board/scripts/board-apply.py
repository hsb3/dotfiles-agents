#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""board-apply — apply a changeset to a GitHub Project (v2). DRY-RUN by default.

The WRITE half of the export -> analyze -> apply loop. Reads a TSV changeset
(one row per cell to change), re-pulls a fresh snapshot, and writes ONLY the cells
that differ from current. Idempotent: re-running is free. Nothing is written unless
you pass --apply.

Changeset TSV (tab-separated, header required):
    issue   field       value
    671     priority    P1
    671     impact      High
    334     target      2026-06-18
    127     blocked_by  126           # native dependency (needs --repo)
    503     iteration   Sprint 2
    42      effort                    # empty value => clear the field

field is matched case-insensitively against the board's field names; value for a
single-select is the OPTION NAME (resolved to its id here). `blocked_by` is a
pseudo-field routed to the REST dependencies endpoint.

Usage:
    ./board-apply.py -o hsb3 -n 8 --changeset triage-batch2.tsv            # dry-run
    ./board-apply.py -o hsb3 -n 8 --changeset triage-batch2.tsv --apply
    ./board-apply.py -o hsb3 -n 8 --changeset edges.tsv --repo hsb3/ra-platform --apply

Auth: shells out to `gh` with GITHUB_TOKEN UNSET. Needs `gh auth refresh -s project`.
Exit code is non-zero if any change failed.
"""

from __future__ import annotations
import argparse, csv, json, os, subprocess, sys

# Field dataTypes that updateProjectV2ItemFieldValue can write. Built-ins like
# Labels / Milestone / Assignees are issue-native, not settable via the project API.
SETTABLE = {"SINGLE_SELECT", "TEXT", "NUMBER", "DATE", "ITERATION"}


def resolve_field(token: str, fields: dict) -> str | None:
    """Match a changeset field token against the board's LIVE field names (case-insensitive,
    space/underscore-insensitive). Works for any current or future field — no hardcoded list."""

    def norm(s: str) -> str:
        return s.lower().replace("_", "").replace(" ", "")

    want = norm(token)
    for name in fields:
        if norm(name) == want:
            return name
    return None


def fv_scalar(fv: dict):
    """One fieldValue node -> its scalar. Key-presence, not truthiness: "" and 0 are real values."""
    for k in ("name", "text", "date", "title", "number"):
        if k in fv and fv[k] is not None:
            return fv[k]
    return None


def values_equal(current, val: str) -> bool:
    """Changeset string vs live value: case-insensitive text match, with a numeric
    fallback so a NUMBER field holding 3.0 matches the changeset's "3"."""
    if current is None:
        return False
    if str(current).lower() == val.lower():
        return True
    try:
        return float(current) == float(val)
    except (TypeError, ValueError):
        return False


def gh(*args: str, check: bool = True) -> tuple[int, str, str]:
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
    r = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        sys.exit(f"gh {' '.join(args[:2])} failed:\n{r.stderr.strip()}")
    return r.returncode, r.stdout, r.stderr


def graphql(query: str, *raw: str, **fvars: str) -> dict:
    args = ["api", "graphql", "-f", "query=" + query]
    for k, v in fvars.items():
        args += ["-f", f"{k}={v}"]
    args += list(raw)  # e.g. "-F", "n=3"
    out = json.loads(gh(*args)[1])
    if "data" not in out:  # error-only response (rate limit, transient failure)
        sys.exit(f"graphql: no data in response: {out.get('errors') or out}")
    return out


def load_snapshot(owner: str, number: int, owner_type: str):
    scope = "user" if owner_type == "user" else "organization"
    pj = graphql(
        "query($o:String!,$n:Int!){ %s(login:$o){ projectV2(number:$n){ id } } }"
        % scope,
        o=owner,
        n=str(number),
    )
    proj = (pj.get("data", {}).get(scope) or {}).get("projectV2")
    if not proj:
        sys.exit(f"project {owner}#{number} not found")
    pid = proj["id"]

    fields = {}
    # first:50 / first:30 below are unpaginated practical limits — a board with more
    # fields, or an item with more field values, would silently truncate.
    fq = """query($id:ID!){ node(id:$id){ ... on ProjectV2 { fields(first:50){ nodes{
      __typename
      ... on ProjectV2FieldCommon{ id name dataType }
      ... on ProjectV2SingleSelectField{ id name options{ id name } }
      ... on ProjectV2IterationField{ id name configuration{ iterations{ id title } completedIterations{ id title } } }
    }}}}}"""
    for f in graphql(fq, id=pid)["data"]["node"]["fields"]["nodes"]:
        if not f:
            continue
        fields[f["name"]] = {
            "id": f["id"],
            "dataType": f.get("dataType"),
            "options": {o["name"].lower(): o["id"] for o in f.get("options", [])},
            "iterations": {
                it["title"].lower(): it["id"]
                for it in (
                    (f.get("configuration") or {}).get("iterations", [])
                    + (f.get("configuration") or {}).get("completedIterations", [])
                )
            }
            if f.get("configuration")
            else {},
        }

    items, cursor = {}, None
    iq = """query($id:ID!,$after:String){ node(id:$id){ ... on ProjectV2 { items(first:100, after:$after){
      pageInfo{ hasNextPage endCursor }
      nodes{ id content{ __typename ... on Issue{ number } ... on PullRequest{ number } }
        fieldValues(first:30){ nodes{ __typename
          ... on ProjectV2ItemFieldSingleSelectValue{ name field{ ... on ProjectV2FieldCommon{ name } } }
          ... on ProjectV2ItemFieldTextValue{ text field{ ... on ProjectV2FieldCommon{ name } } }
          ... on ProjectV2ItemFieldNumberValue{ number field{ ... on ProjectV2FieldCommon{ name } } }
          ... on ProjectV2ItemFieldDateValue{ date field{ ... on ProjectV2FieldCommon{ name } } }
          ... on ProjectV2ItemFieldIterationValue{ title field{ ... on ProjectV2FieldCommon{ name } } }
        }}
      } } }}}"""
    while True:
        extra = ["-f", f"after={cursor}"] if cursor else []
        page = graphql(iq, *extra, id=pid)["data"]["node"]["items"]
        for it in page["nodes"]:
            num = (it.get("content") or {}).get("number")
            if num is None:
                continue
            cur_vals = {}
            for fv in it["fieldValues"]["nodes"]:
                fn = (fv.get("field") or {}).get("name")
                if not fn:
                    continue
                cur_vals[fn] = fv_scalar(fv)
            items[num] = {"item_id": it["id"], "values": cur_vals}
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return pid, fields, items


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Apply a changeset to a GitHub Project v2 (dry-run default)."
    )
    ap.add_argument("-o", "--owner", required=True)
    ap.add_argument("-n", "--number", type=int, required=True)
    ap.add_argument("--owner-type", choices=["user", "org"], default="user")
    ap.add_argument("--changeset", required=True, help="TSV: issue<TAB>field<TAB>value")
    ap.add_argument("--repo", help="owner/name for blocked_by rows (REST dependencies)")
    ap.add_argument(
        "--apply", action="store_true", help="actually write (default: dry-run)"
    )
    args = ap.parse_args()

    rows = []
    with open(args.changeset) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            if r.get("issue"):
                rows.append(r)

    pid, fields, items = load_snapshot(args.owner, args.number, args.owner_type)
    changed = unchanged = skipped = failed = 0

    for r in rows:
        try:
            issue = int(r["issue"])
        except ValueError:
            print(f"SKIP  row issue={r['issue']!r}: not an integer")
            skipped += 1
            continue
        fld = r["field"].lower()
        val = r["value"]
        tag = f"#{issue} {fld}={val or '(clear)'}"

        if fld in ("blocked_by", "blocking"):
            if not args.repo:
                print(f"SKIP  {tag}: --repo required for {fld}")
                skipped += 1
                continue
            rc, out, _ = gh(
                "api", f"repos/{args.repo}/issues/{val}", "--jq", ".id", check=False
            )
            if rc != 0:
                print(f"FAIL  {tag}: blocker #{val} not found")
                failed += 1
                continue
            blocker_id = out.strip()
            if not args.apply:
                print(f"DRY   would POST {fld}: #{issue} <- #{val}")
                changed += 1
                continue
            rc, _, err = gh(
                "api",
                "-X",
                "POST",
                f"repos/{args.repo}/issues/{issue}/dependencies/{fld}",
                "-F",
                f"issue_id={blocker_id}",
                check=False,
            )
            if rc == 0:
                print(f"SET   {tag}")
                changed += 1
            else:
                print(f"FAIL  {tag}: {err.strip()}")
                failed += 1
            continue

        if issue not in items:
            print(f"SKIP  {tag}: not on board")
            skipped += 1
            continue
        fname = resolve_field(fld, fields)
        if not fname:
            print(f"SKIP  {tag}: no field matches '{r['field']}'")
            skipped += 1
            continue
        fdef = fields[fname]
        if fdef["dataType"] not in SETTABLE:
            print(
                f"SKIP  {tag}: field '{fname}' ({fdef['dataType']}) not settable via project API"
            )
            skipped += 1
            continue
        item_id = items[issue]["item_id"]
        current = items[issue]["values"].get(fname)

        # idempotent skip
        if val == "" and current in (None, ""):
            print(f"OK    {tag}: already clear")
            unchanged += 1
            continue
        if val and values_equal(current, val):
            print(f"OK    {tag}: unchanged")
            unchanged += 1
            continue

        if not args.apply:
            print(f"DRY   would set {tag} (was {current})")
            changed += 1
            continue

        try:
            if val == "":
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!){clearProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f}){projectV2Item{id}}}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                )
            elif fdef["dataType"] == "SINGLE_SELECT":
                oid = fdef["options"].get(val.lower())
                if not oid:
                    print(f"FAIL  {tag}: no option '{val}'")
                    failed += 1
                    continue
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){projectV2Item{id}}}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                    o=oid,
                )
            elif fdef["dataType"] == "ITERATION":
                iid = fdef["iterations"].get(val.lower())
                if not iid:
                    print(f"FAIL  {tag}: no iteration '{val}'")
                    failed += 1
                    continue
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{iterationId:$o}}){projectV2Item{id}}}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                    o=iid,
                )
            elif fdef["dataType"] == "DATE":
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!,$d:Date!){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{date:$d}}){projectV2Item{id}}}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                    d=val,
                )
            elif fdef["dataType"] == "NUMBER":
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!,$nn:Float!){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{number:$nn}}){projectV2Item{id}}}",
                    "-F",
                    f"nn={val}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                )
            else:  # TEXT and anything else
                graphql(
                    "mutation($p:ID!,$i:ID!,$f:ID!,$t:String!){updateProjectV2ItemFieldValue(input:{projectId:$p,itemId:$i,fieldId:$f,value:{text:$t}}){projectV2Item{id}}}",
                    p=pid,
                    i=item_id,
                    f=fdef["id"],
                    t=val,
                )
            print(f"SET   {tag} (was {current})")
            changed += 1
        except SystemExit as e:
            print(f"FAIL  {tag}: {e}")
            failed += 1

    verb = "applied" if args.apply else "planned (dry-run)"
    print(
        f"\n{verb}: {changed} changed · {unchanged} unchanged · {skipped} skipped · {failed} failed",
        file=sys.stderr,
    )
    if not args.apply and changed:
        print("re-run with --apply to write.", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
