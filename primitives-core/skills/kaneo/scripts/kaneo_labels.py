#!/usr/bin/env python3
"""Safe label operations against a Kaneo workspace.

A Kaneo label is not one row. Every label name has at most one **definition row**
(`taskId: null`, the workspace palette entry) and one **attachment row** per task
carrying it. Deleting the definition row deletes the whole name-group workspace-wide,
attachments included, and answers `200` while doing it — so a caller reading the status
code learns nothing about how much it just destroyed. Renaming a definition row renames
the group the same way.

That is the whole reason this script exists. `DELETE /label/{id}` is one call either way;
what it cannot do is tell you, first, that the id you hold is a definition row and that N
tasks are about to lose the label. So:

  audit    what the workspace's labels actually look like, including names whose
           attachments have no definition row (a past cascade, or an import that never
           made one)
  delete   refuses a definition-row delete outright unless --cascade is passed, and
           prints the exact attachment count and task ids it would destroy first

Verification is always a re-read, never a status code — see `_verify`.

Env: KANEO_API_URL, KANEO_API_KEY, KANEO_WORKSPACE_ID (or --workspace).
Stdlib only, like everything else in this repo's test lane.
"""

import argparse
import collections
import json
import os
import sys
import urllib.error
import urllib.request


class ApiError(RuntimeError):
    pass


def _call(api, key, method, path, body=None):
    """Return (status, parsed-or-raw). A non-2xx is data here, not an exception: the
    caller decides, because a 400 from this API frequently means "row is already gone"
    rather than "your call was wrong"."""
    request = urllib.request.Request(
        api + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"x-api-key": key, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode(), e.code
    except urllib.error.URLError as e:
        raise ApiError("cannot reach {0}: {1}".format(api, e)) from e
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def fetch_rows(api, key, workspace):
    status, data = _call(api, key, "GET", "/label/workspace/{0}".format(workspace))
    if status != 200:
        raise ApiError("label read failed: HTTP {0} {1}".format(status, data))
    return data if isinstance(data, list) else data.get("data", [])


def group(rows):
    """name -> {"definitions": [row], "attachments": [row]}, in one pass."""
    out = collections.defaultdict(lambda: {"definitions": [], "attachments": []})
    for row in rows:
        bucket = "attachments" if row.get("taskId") else "definitions"
        out[row.get("name")][bucket].append(row)
    return dict(out)


def _verify(api, key, workspace, name):
    """Re-read and report what survives. The API's own status codes are not evidence:
    a definition-row delete returns 200 having destroyed N attachment rows, and a delete
    of an already-gone row returns 400 'Workspace ID could not be determined'. Only a
    fresh read distinguishes those."""
    grouped = group(fetch_rows(api, key, workspace)).get(name)
    if not grouped:
        return 0, 0
    return len(grouped["definitions"]), len(grouped["attachments"])


def cmd_audit(args, api, key):
    grouped = group(fetch_rows(api, key, args.workspace))
    orphans, unused = [], []
    print("{0:<24} {1:>5} {2:>12}".format("label", "defs", "attachments"))
    for name in sorted(grouped, key=lambda n: (n or "")):
        entry = grouped[name]
        definitions, attachments = len(entry["definitions"]), len(entry["attachments"])
        print("{0:<24} {1:>5} {2:>12}".format(name, definitions, attachments))
        if not definitions:
            orphans.append((name, attachments))
        elif not attachments:
            unused.append(name)
    if orphans:
        print("\nattachments with NO definition row (the palette will not offer these,")
        print("and the UI cannot re-attach them — a past cascade, or an import):")
        for name, count in orphans:
            print("  {0} — on {1} task(s)".format(name, count))
    if unused:
        print("\ndefinitions attached to nothing: {0}".format(", ".join(unused)))
    # Orphans are a finding, not a failure: reporting them is the point, and a caller
    # that wants them to fail a gate can read this exit code.
    return 1 if orphans else 0


def cmd_delete(args, api, key):
    grouped = group(fetch_rows(api, key, args.workspace)).get(args.name)
    if not grouped:
        print("no label named {0!r} in this workspace — nothing to do".format(args.name))
        return 0

    definitions, attachments = grouped["definitions"], grouped["attachments"]
    print("{0!r}: {1} definition row(s), {2} attachment(s)".format(
        args.name, len(definitions), len(attachments)))
    for row in attachments:
        print("  attached to task {0}".format(row.get("taskId")))

    if attachments and not args.cascade:
        print(
            "\nREFUSED. Deleting the definition row would take all {0} attachment(s) with\n"
            "it, workspace-wide, and answer 200 while doing so. Re-run with --cascade to\n"
            "accept that, or detach the tasks first.".format(len(attachments))
        )
        return 2

    if args.dry_run:
        print("\n--dry-run: nothing was deleted")
        return 0

    # Attachments first, definition last. The reverse order works by accident — the
    # cascade removes the attachments — but it destroys them without ever naming them,
    # which is exactly the failure this script exists to prevent.
    for row in attachments:
        status, _ = _call(api, key, "DELETE", "/label/{0}".format(row["id"]))
        print("  dropped attachment {0} (HTTP {1})".format(row["id"], status))
    for row in definitions:
        status, _ = _call(api, key, "DELETE", "/label/{0}".format(row["id"]))
        print("  dropped definition {0} (HTTP {1})".format(row["id"], status))

    remaining_definitions, remaining_attachments = _verify(api, key, args.workspace, args.name)
    if remaining_definitions or remaining_attachments:
        print("\nVERIFY FAILED: {0} definition(s) and {1} attachment(s) still present".format(
            remaining_definitions, remaining_attachments))
        return 1
    print("\nverified by re-read: no rows named {0!r} remain".format(args.name))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", default=os.environ.get("KANEO_WORKSPACE_ID", ""))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit", help="label health for the workspace")
    delete = sub.add_parser("delete", help="delete a label name safely")
    delete.add_argument("--name", required=True)
    delete.add_argument("--cascade", action="store_true",
                        help="accept destroying every attachment of this name")
    delete.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    api = os.environ.get("KANEO_API_URL", "").rstrip("/")
    key = os.environ.get("KANEO_API_KEY", "")
    if not api or not key or not args.workspace:
        print("KANEO_API_URL, KANEO_API_KEY and KANEO_WORKSPACE_ID (or --workspace) "
              "are all required", file=sys.stderr)
        return 2
    try:
        return cmd_audit(args, api, key) if args.command == "audit" else cmd_delete(args, api, key)
    except ApiError as e:
        print("kaneo_labels: {0}".format(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
