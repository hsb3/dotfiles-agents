#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report which OPEN items have NO plan folder on the desk -- the planning backlog.

reconcile.py answers "do the plans on disk agree with the README and tracker state?".
This answers the inverse: "which open work has no plan at all?". An item whose key is
named by some plan's `## Tracking` section is covered; every other open non-epic item
is unplanned and shows up here.

Per an owner decision only NON-TRIVIAL work strictly needs a plan -- trivial bugs and
docs may be waived -- so likely-trivial items are TAGGED rather than auto-excluded;
the owner waives them by judgment.

Folder -> ref mapping is reconcile's (`disk_folders()` + `plan_tracking_ref()`), so
one ref rule governs the whole desk.

Usage (from anywhere):
    python3 _utils/coverage.py                            # export from the tracker
    python3 _utils/coverage.py --snapshot snapshot.json   # read an export
    python3 _utils/coverage.py --json                     # machine-readable backlog
    python3 _utils/coverage.py --changeset changeset.tsv  # propose a `needs-plan` label

`--changeset` writes an apply-ready TSV that the tracker adapter can dry-run and then
apply, which closes the export -> analyze -> apply loop.

Exit 1 when any open non-epic item has no plan, 0 when all are covered.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reconcile  # noqa: E402
from tracker import add_tracker_args, load_snapshot  # noqa: E402

# The label a changeset proposes on uncovered work.
NEEDS_PLAN = "needs-plan"

# A `bug` is tagged maybe-trivial only when its title looks small (no broad scope
# words). Advisory -- the owner makes the actual waive call.
BIG_TITLE_RE = re.compile(
    r"\b(refactor|redesign|migrat|architect|pipeline|engine|epic|overhaul|rewrite)\b",
    re.I,
)


def planned_refs(keys: set[str]) -> set[str]:
    """The tracker keys some plan folder already claims."""
    planned = set()
    for slug in reconcile.disk_folders():
        ref, _warn = reconcile.plan_tracking_ref(slug, keys)
        if ref is not None:
            planned.add(ref)
    return planned


def maybe_trivial(item: dict) -> bool:
    """Advisory tag: a docs item, or a small-looking bug, may be waivable."""
    labels = set(item.get("labels") or [])
    if "documentation" in labels:
        return True
    return "bug" in labels and not BIG_TITLE_RE.search(item.get("title", ""))


def compute(snapshot: dict) -> dict:
    """Open non-epic items with no plan folder, tagged and sorted by key."""
    keys = {i["key"] for i in snapshot["items"]}
    planned = planned_refs(keys)
    non_epic = [
        i for i in snapshot["items"] if i["state"] == "open" and i.get("kind") != "epic"
    ]
    unplanned = [
        {
            "key": item["key"],
            "title": item.get("title", ""),
            "priority": item.get("priority"),
            "labels": sorted(item.get("labels") or []),
            "maybe_trivial": maybe_trivial(item),
        }
        for item in sorted(non_epic, key=lambda i: i["key"])
        if item["key"] not in planned
    ]
    return {
        "planned_count": len(planned),
        "non_epic_count": len(non_epic),
        "unplanned": unplanned,
    }


def changeset_text(unplanned: list[dict]) -> str:
    """An apply-ready TSV: the FULL desired label set per uncovered item."""
    lines = ["key\tfield\tvalue"]
    for row in unplanned:
        labels = sorted(set(row["labels"]) | {NEEDS_PLAN})
        lines.append(f"{row['key']}\tlabels\t{','.join(labels)}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Parse first, so `--help` answers from anywhere -- before the tracker is read."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--changeset",
        help=f"write a TSV proposing a `{NEEDS_PLAN}` label on each uncovered item",
    )
    add_tracker_args(parser)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = compute(load_snapshot(args))
    unplanned = result["unplanned"]

    if args.changeset:
        Path(args.changeset).write_text(changeset_text(unplanned))

    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if unplanned else 0

    total = result["non_epic_count"]
    trivial = sum(1 for row in unplanned if row["maybe_trivial"])
    print(
        f"Plan coverage: {len(unplanned)} of {total} open non-epic items have no plan "
        f"({trivial} tagged maybe-trivial)\n"
    )
    if not unplanned:
        print("Every open non-epic item has a plan folder. The backlog is covered.")
        return 0
    for row in unplanned:
        tag = "[trivial?]" if row["maybe_trivial"] else "          "
        print(f"  {row['key']:<8} {row['priority'] or '--':<3} {tag}  {row['title'][:54]}")
    print(
        f"\n{len(unplanned)} open item(s) have no plan. Draft a plan folder for each "
        "non-trivial one (trivial tags are advisory)."
    )
    if args.changeset:
        print(f"changeset -> {args.changeset}  (dry-run it through the tracker adapter)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
