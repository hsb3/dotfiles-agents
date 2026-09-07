#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Reconcile the plans README status table against tracker state and the folders on
disk.

The README table is hand-maintained, so it drifts: a plan stays in the ACTIVE section
after its tracked item closes, a folder appears with no row, the row names a different
item than the plan body. This answers "do the table, the tracker, and the disk still
agree?" in one pass over an exported snapshot.

The tracking ref is deliberately backend-agnostic: **the first whitespace- or
punctuation-delimited token that is a key in the snapshot**, in the README's ref column
and in each `plan.md`'s `## Tracking` section alike. No per-backend ref syntax, so a
desk keeps working when the tracker changes underneath it.

Usage (from anywhere):
    python3 _utils/reconcile.py                            # export from the tracker
    python3 _utils/reconcile.py --snapshot snapshot.json   # read an export
    python3 _utils/reconcile.py --json                     # machine-readable drift list

Reads `--status all` by default: an ARCHIVED row can only be checked against a closed
item. Exit 1 when any drift is found, 0 when clean -- so it can gate a wave.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tracker import add_tracker_args, load_snapshot  # noqa: E402

# This script lives in <desk>/_utils/; the plans desk it scans is the parent dir.
PLANS_DIR = Path(__file__).resolve().parent.parent
README = PLANS_DIR / "README.md"

# Section markers in README.md (substring match on the line).
ACTIVE_MARKER = "ACTIVE plans"
ARCHIVED_MARKER = "ARCHIVED ("

# A ref token: alphanumeric, with inner - or _ kept so a hyphenated key survives.
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
# A ref cell that deliberately names nothing, as opposed to naming something unknown.
NO_REF_RE = re.compile(r"^(|-|--|n/?a|none|tbd|\(?no [a-z ]*\)?)$", re.I)
# Words that, when they precede the resolved ref on its line, mean the leading key is
# an epic/relation rather than this plan's own tracking ref -- the convention is that
# the tracking ref comes FIRST. Warn (non-fatal) when it looks violated.
EPIC_SIGNAL = re.compile(r"\b(epic|under|child of|relates?|sibling)\b", re.I)


def first_known_ref(text: str, keys: set[str]) -> str | None:
    """The first token in `text` that is a key in the snapshot, else None.

    A qualified form (`project#key`) resolves to its key, since the sub-parts of a
    token are tried after the token itself.
    """
    for token in TOKEN_RE.findall(text or ""):
        if token in keys:
            return token
        for part in re.split(r"[-_]", token):
            if part in keys:
                return part
    return None


def parse_readme_rows() -> tuple[list[dict], list[dict]]:
    """Return (active_rows, archived_rows). Each row: {plan, cell}."""
    if not README.is_file():
        sys.exit(
            f"no {README.name} at {README} -- run this from a plans desk, where the "
            "scripts live in <desk>/_utils/ beside the desk's own README"
        )
    active: list[dict] = []
    archived: list[dict] = []
    mode: str | None = None
    for line in README.read_text().splitlines():
        if ACTIVE_MARKER in line:
            mode = "active"
            continue
        if ARCHIVED_MARKER in line:
            mode = "archived"
            continue
        if mode is None or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        plan, cell = cells[0], cells[1]
        # Skip the header and separator rows.
        if plan in ("Plan", "Plan (archived path)") or set(plan) <= {"-", " ", ":"}:
            continue
        (active if mode == "active" else archived).append({"plan": plan, "cell": cell})
    return active, archived


def plan_tracking_ref(slug: str, keys: set[str]) -> tuple[str | None, str | None]:
    """(tracking ref, warning) for one plan folder.

    Warn (non-fatal) when the section is missing, names no known key, or the leading
    key looks epic-flagged -- i.e. the parse should be double-checked by a human
    rather than trusted as a mismatch.
    """
    plan_md = PLANS_DIR / slug / "plan.md"
    if not plan_md.is_file():
        return None, "no plan.md"
    text = plan_md.read_text()
    found = re.search(r"^##\s*Tracking\b.*?(?=^##\s|\Z)", text, re.S | re.M)
    if not found:
        return None, "no `## Tracking` section"
    section = found.group(0)
    ref = first_known_ref(section, keys)
    if ref is None:
        return None, "`## Tracking` names no known tracker key"
    before = section[: section.index(ref)]
    if EPIC_SIGNAL.search(before.rsplit("\n", 1)[-1]):
        return ref, f"leading ref {ref} looks epic-flagged; verify it is the tracking ref"
    return ref, None


def disk_folders() -> set[str]:
    return {p.name for p in PLANS_DIR.iterdir() if p.is_dir() and (p / "plan.md").is_file()}


def resolve_row(cell: str, keys: set[str]) -> tuple[str | None, str | None]:
    """(ref, why-not). `why-not` is 'none' when the cell claims nothing and 'unknown'
    when it claims something the tracker has never heard of."""
    ref = first_known_ref(cell, keys)
    if ref:
        return ref, None
    stripped = re.sub(r"[`*]", "", cell).strip()
    return None, ("none" if NO_REF_RE.match(stripped) else "unknown")


def run(snapshot: dict) -> dict:
    active, archived = parse_readme_rows()
    states = {i["key"]: i["state"] for i in snapshot["items"]}
    keys = set(states)
    folders = disk_folders()
    drift: list[dict] = []
    warns: list[dict] = []
    ok: list[str] = []

    active_slugs = {row["plan"] for row in active}

    for row in active:
        slug = row["plan"]
        ref, why = resolve_row(row["cell"], keys)
        # 1. the tracked item should be open
        if ref is None and why == "none":
            drift.append(
                {"kind": "active-no-issue", "plan": slug, "detail": "ACTIVE row names no ref"}
            )
        elif ref is None:
            drift.append(
                {
                    "kind": "issue-missing",
                    "plan": slug,
                    "detail": f"ACTIVE row names no item the tracker knows: {row['cell']}",
                }
            )
        elif states[ref] == "closed":
            drift.append(
                {
                    "kind": "active-but-closed",
                    "plan": slug,
                    "ref": ref,
                    "detail": f"{ref} is CLOSED -> human decision: reopen the item "
                    "(criteria unmet) OR archive the plan (done)",
                }
            )
        else:
            ok.append(f"{slug:<30} {ref} open")
        # 2. folder must exist on disk
        if slug not in folders:
            drift.append(
                {
                    "kind": "row-no-folder",
                    "plan": slug,
                    "detail": "ACTIVE row has no plan folder on disk",
                }
            )
        # 3. README ref vs the plan.md Tracking ref
        body, warn = plan_tracking_ref(slug, keys)
        if warn:
            warns.append({"plan": slug, "detail": warn})
        if ref and body and body != ref:
            drift.append(
                {
                    "kind": "body-mismatch",
                    "plan": slug,
                    "ref": ref,
                    "detail": f"README says {ref}, plan.md says {body}",
                }
            )

    for row in archived:
        slug = row["plan"]
        ref, why = resolve_row(row["cell"], keys)
        if ref is None and why == "none":
            continue  # 'enablement (no ref)', 'repo hygiene' -- nothing to check
        if ref is None:
            drift.append(
                {
                    "kind": "issue-missing",
                    "plan": slug,
                    "detail": f"ARCHIVED row names no item the tracker knows: {row['cell']}",
                }
            )
        elif states[ref] == "open":
            drift.append(
                {
                    "kind": "archived-but-open",
                    "plan": slug,
                    "ref": ref,
                    "detail": f"{ref} is open but the plan is archived",
                }
            )

    # 4. disk folders with no ACTIVE row
    for slug in sorted(folders - active_slugs):
        drift.append(
            {
                "kind": "folder-no-row",
                "plan": slug,
                "detail": "plan folder on disk has no ACTIVE README row",
            }
        )

    return {
        "ok": ok,
        "drift": drift,
        "warns": warns,
        "counts": {
            "active": len(active),
            "archived": len(archived),
            "folders": len(folders),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    """Parse first, so `--help` answers from anywhere -- before the tracker is read."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    add_tracker_args(parser, default_status="all")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = run(load_snapshot(args))
    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if result["drift"] else 0

    counts = result["counts"]
    print(
        f"Reconcile {README} vs the tracker  ({counts['active']} active rows, "
        f"{counts['archived']} archived, {counts['folders']} folders)\n"
    )
    for line in result["ok"]:
        print(f"  OK   {line}")
    for warn in result["warns"]:
        print(f"  WARN {warn['plan']}: {warn['detail']}")
    if not result["drift"]:
        print("\nNo drift. The README table agrees with tracker state and disk.")
        return 0
    print(f"\n{len(result['drift'])} drift item(s):")
    for item in result["drift"]:
        print(f"  DRIFT [{item['kind']}] {item['plan']}: {item['detail']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
