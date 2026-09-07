#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Audit every OPEN item's body against the desk's task-authoring bar.

Answers "is this tracker item actually buildable as written?":

  - a normal item needs an **acceptance-criteria** heading AND a
    **dependencies/gates** heading;
  - an **epic** (an item with children, or one labelled `epic`) needs a
    **close-when** heading, its acceptance equivalent.

The bar is the authoring bar, not any one tracker's issue template -- heading
matching is tolerant ("Acceptance", "Definition of done", "Depends on" all count), so
this checks the load-bearing sections rather than exact wording.

Usage (from anywhere):
    python3 _utils/conformance.py                            # export from the tracker
    python3 _utils/conformance.py --snapshot snapshot.json   # read an export
    python3 _utils/conformance.py --json                     # machine-readable

Exit 1 when any open item is non-conformant, 0 when all conform.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tracker import add_tracker_args, load_snapshot  # noqa: E402

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
AC_RE = re.compile(r"accept|definition of done|done when", re.I)
GATE_RE = re.compile(r"gate|depend", re.I)
CLOSE_RE = re.compile(r"close when|close criteria", re.I)


def audit_item(item: dict) -> list[str]:
    """The list of missing required sections ([] = conformant)."""
    headings = HEADING_RE.findall(item.get("body") or "")
    if not headings:
        return ["no headings / no required sections"]
    blob = "\n".join(headings)
    if item.get("kind") == "epic":
        return [] if CLOSE_RE.search(blob) else ["Close when (epic acceptance)"]
    missing = []
    if not AC_RE.search(blob):
        missing.append("Acceptance criteria")
    if not GATE_RE.search(blob):
        missing.append("Dependencies & gates")
    return missing


def severity(missing: list[str], epic: bool) -> str:
    """Triage band. Missing acceptance criteria (or any structure at all) is the hard
    requirement -> CRITICAL; an epic with no close-condition -> EPIC; having AC but
    lacking only the gates checklist -> MINOR."""
    if any("Acceptance" in m or "no headings" in m for m in missing):
        return "CRITICAL"
    if epic:
        return "EPIC"
    return "MINOR"


def run(snapshot: dict) -> dict:
    items = [i for i in snapshot["items"] if i["state"] == "open"]
    bad: list[dict] = []
    for item in sorted(items, key=lambda i: i["key"]):
        missing = audit_item(item)
        if missing:
            epic = item.get("kind") == "epic"
            bad.append(
                {
                    "key": item["key"],
                    "title": item.get("title", ""),
                    "epic": epic,
                    "missing": missing,
                    "severity": severity(missing, epic),
                }
            )
    return {"total": len(items), "bad": bad}


def build_parser() -> argparse.ArgumentParser:
    """Parse first, so `--help` answers from anywhere -- before the tracker is read."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    add_tracker_args(parser)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = run(load_snapshot(args))
    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if result["bad"] else 0

    total, bad = result["total"], result["bad"]
    rate = 100 * (total - len(bad)) / total if total else 100
    print(
        f"Task-authoring conformance: {total - len(bad)}/{total} open items "
        f"conform ({rate:.0f}%)\n"
    )
    if not bad:
        print("Every open item carries its required sections.")
        return 0
    bands = {
        "CRITICAL": "no meaningful acceptance criteria (the hard requirement)",
        "EPIC": "epic missing a close-condition",
        "MINOR": "has acceptance criteria; missing only the dependencies/gates section",
    }
    for band, blurb in bands.items():
        rows = [b for b in bad if b["severity"] == band]
        if not rows:
            continue
        print(f"{band} - {blurb}  ({len(rows)})")
        for row in rows:
            print(
                f"  {row['key']:<8} missing: {', '.join(row['missing'])}"
                f"  -  {row['title'][:50]}"
            )
        print()
    print(f"{len(bad)} non-conformant. Rewrite each body to the authoring bar, then re-run.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
