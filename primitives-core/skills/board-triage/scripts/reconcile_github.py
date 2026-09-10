#!/usr/bin/env python3
"""Reconcile GitHub issues against a Kata project; dry-run unless --apply.

Run from the GitHub checkout linked to this board. --project overrides Kata's
checkout selection; gh uses its normal repository selection. See the Kata adapter
reference for the import-only sync and mirror ownership rules.
"""

import argparse
import json
import subprocess
import sys


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"{cmd[0]} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout


def board(project):
    """github_issue number -> (short_id, status, title) for every card that has a mirror."""
    cmd = ["kata", "list", "--status", "all", "--limit", "0"]
    if project:
        cmd += ["--project", project]
    data = json.loads(run([*cmd, "--json"]))
    out = {}
    for i in data["issues"] or []:
        num = (i.get("metadata") or {}).get("github_issue")
        if num:
            out[str(num).rsplit("/", 1)[-1]] = (i["short_id"], i["status"], i["title"])
    return out


def issues(state):
    cmd = ["gh", "issue", "list", "--state", state, "--limit", "500", "--json", "number,title"]
    return {str(x["number"]): x["title"] for x in json.loads(run(cmd))}


def close(num, ref, title):
    body = f"Closed on the kata board as `{ref}` — {title}\n\nReconciled by board-desk's `reconcile_github.py`; the board is the system of record."
    run(["gh", "issue", "close", num, "--comment", body])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Kata project (default: Kata's checkout selection)")
    parser.add_argument("--apply", action="store_true", help="close stale GitHub mirrors")
    args = parser.parse_args()
    apply = args.apply
    cards, open_gh = board(args.project), issues("open")

    stale, tracked, untracked = [], [], []
    for num, gh_title in sorted(open_gh.items(), key=lambda kv: int(kv[0])):
        card = cards.get(num)
        if card is None:
            untracked.append((num, gh_title))
        elif card[1] == "closed":
            stale.append((num, card))
        else:
            tracked.append(num)

    closed_gh = issues("closed")
    reverse = [
        (num, ref) for num, (ref, status, _) in cards.items()
        if status == "open" and num in closed_gh
    ]

    print(f"open GitHub issues: {len(open_gh)}   tracked: {len(tracked)}   "
          f"stale mirrors: {len(stale)}   untracked: {len(untracked)}")

    if stale:
        print(f"\nstale mirrors — card closed, issue still open ({len(stale)}):")
        for num, (ref, _, title) in stale:
            print(f"  #{num:<5} {ref}  {title[:66]}")
            if apply:
                close(num, ref, title)
        print(f"\n{'closed ' + str(len(stale)) + ' issue(s).' if apply else 'dry run — rerun with --apply to close these.'}")

    if untracked:
        print(f"\nuntracked — inbound intake with no board card ({len(untracked)}):")
        for num, title in untracked:
            print(f"  #{num:<5} {title[:72]}")
        print("  File each on the board (kata create ... --meta github_issue=<N>), then rerun.")

    if reverse:
        print(f"\nreverse drift — card open, mirror closed ({len(reverse)}) — informational:")
        for num, ref in reverse:
            print(f"  {ref} -> #{num}")

    return 0 if apply or not (stale or untracked) else 1


if __name__ == "__main__":
    sys.exit(main())
