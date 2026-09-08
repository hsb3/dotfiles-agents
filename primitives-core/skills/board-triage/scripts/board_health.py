#!/usr/bin/env python3
"""Decay detector for a task board: has it rotted enough to need a triage pass?

SKILL.md §6 makes a priority band and a grouping value the pass's definition of done, but
nothing measured whether that held. Field-population audits cannot: they check that a cell is
FILLED, not that it DISCRIMINATES. On 2026-09-08 one reported all-clear on a board where 34 of
55 open items shared a single priority band, 16 carried no label, and the real grouping lived
only in title prefixes no query could reach.

Reads the §2 adapter snapshot — never a backend — so it works for kata, Kaneo and GitHub
Projects alike with no adapter change. Open items only; a rank on closed work means nothing.
Exit 0 clean, 1 on any finding, 2 when the snapshot cannot be read.
"""

import argparse
import collections
import json
import re
import sys

UNSET = "(unset)"
PRINT_CAP = 10

# `prefix: text`, lowercase slug only. The trailing space is what keeps `http://x` out.
TITLE_PREFIX = re.compile(r"^([a-z0-9][a-z0-9-]*):\s")

NAMESPACES = ("type:", "status:", "kind:", "area:")
SYNONYMS = {"feat": "feature", "fix": "bug", "chore": "maintenance", "doc": "docs"}


class SnapshotError(Exception):
    """The snapshot could not be read or is not the §2 shape."""


def load_snapshot(path: str | None) -> dict:
    """Parse a snapshot from `path`, or stdin when it is None."""
    try:
        if path is None:
            raw = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
    except OSError as exc:
        raise SnapshotError(f"cannot read snapshot {path!r}: {exc}") from exc
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"snapshot {path or '<stdin>'} is not valid JSON: {exc}") from exc
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("items"), list):
        raise SnapshotError(
            f"snapshot {path or '<stdin>'} is not a board snapshot:"
            " expected an object with an 'items' list (see board-triage SKILL.md §2)"
        )
    return snapshot


def open_items(snapshot: dict) -> list[dict]:
    return [i for i in snapshot["items"] if i.get("state", "open") != "done"]


def priority_of(item: dict) -> str:
    value = (item.get("fields") or {}).get("priority")
    return value.strip() if isinstance(value, str) and value.strip() else UNSET


def title_prefix(title: str) -> str | None:
    match = TITLE_PREFIX.match(title or "")
    return match.group(1) if match else None


def normalize_label(label: str) -> str:
    """Collapse a label to the concept it names, so two spellings of one thing compare equal."""
    name = label.strip().lower()
    for namespace in NAMESPACES:
        if name.startswith(namespace):
            name = name[len(namespace) :]
            break
    name = re.sub(r"[^a-z0-9]", "", name)
    return SYNONYMS.get(name, name)


def vocabulary(snapshot: dict, items: list[dict]) -> tuple[list[str], list[str]]:
    """Labels the board declares, and labels open items actually carry."""
    declared = ((snapshot.get("fields") or {}).get("labels") or {}).get("options") or []
    in_use = {label for item in items for label in (item.get("labels") or [])}
    return sorted({str(d) for d in declared}), sorted(in_use)


def _finding(check: str, severity: str, text: str, affected: list[str], **extra) -> dict:
    return {"check": check, "severity": severity, "finding": text, "affected": affected, **extra}


def check_priority_skew(items: list[dict], threshold: float) -> dict | None:
    """A band holding most of the board carries no information, so nothing sorts by it."""
    distribution = collections.Counter(priority_of(i) for i in items)
    band, count = distribution.most_common(1)[0]
    if count <= threshold * len(items):
        return None
    share = 100 * count / len(items)
    return _finding(
        "priority-skew",
        "fail",
        f"{band} holds {count}/{len(items)} open items ({share:.0f}%)"
        " — a band this crowded cannot rank anything",
        sorted(i["key"] for i in items if priority_of(i) == band),
        distribution=dict(distribution.most_common()),
    )


def check_priority_missing(items: list[dict]) -> dict | None:
    blank = sorted(i["key"] for i in items if priority_of(i) == UNSET)
    if not blank:
        return None
    return _finding(
        "priority-missing",
        "fail",
        f"{len(blank)} open item(s) carry no priority — untriaged, and invisible to any ranking",
        blank,
    )


def check_grouping_missing(items: list[dict]) -> dict | None:
    bare = sorted(i["key"] for i in items if not (i.get("labels") or []))
    if not bare:
        return None
    return _finding(
        "grouping-missing",
        "fail",
        f"{len(bare)} open item(s) carry no label — SKILL.md §6 makes a grouping value"
        " part of a triaged item",
        bare,
    )


def check_grouping_latent(items: list[dict], labels: list[str], threshold: float) -> dict | None:
    """A grouping convention living in title prefixes is real, and no filter can reach it."""
    prefixed = [(i, title_prefix(i.get("title") or "")) for i in items]
    prefixed = [(i, p) for i, p in prefixed if p]
    if len(prefixed) < threshold * len(items):
        return None
    reachable = set()
    for label in labels:
        name = label.strip().lower()
        reachable.add(name)
        if ":" in name:
            reachable.add(name.split(":", 1)[1])
    counts = collections.Counter(p for _, p in prefixed)
    uncovered = {p for p in counts if p not in reachable}
    if len(counts) - len(uncovered) >= len(counts) / 2:
        return None
    share = 100 * len(prefixed) / len(items)
    return _finding(
        "grouping-latent",
        "warn",
        f"{len(prefixed)}/{len(items)} open items ({share:.0f}%) group themselves by title"
        f" prefix, but {len(uncovered)}/{len(counts)} of those prefixes are not labels"
        " — promote them so the grouping becomes queryable",
        sorted(i["key"] for i, p in prefixed if p in uncovered),
        prefixes=dict(counts.most_common()),
    )


def check_vocabulary_fossils(declared: list[str], in_use: list[str]) -> dict | None:
    """A declared label no open item carries makes the picker offer a vocabulary that lies."""
    used = {label.strip().lower() for label in in_use}
    fossils = sorted(d for d in declared if d.strip().lower() not in used)
    if not fossils:
        return None
    return _finding(
        "vocabulary-fossils",
        "warn",
        f"{len(fossils)} declared label(s) appear on no open item — retired vocabulary"
        " still offered by the picker",
        fossils,
    )


def check_vocabulary_collision(labels: list[str]) -> dict | None:
    """Two spellings of one concept split it across two filters, so neither is complete."""
    by_concept: dict[str, set[str]] = collections.defaultdict(set)
    for label in labels:
        by_concept[normalize_label(label)].add(label)
    groups = [sorted(names) for _, names in sorted(by_concept.items()) if len(names) > 1]
    if not groups:
        return None
    return _finding(
        "vocabulary-collision",
        "warn",
        f"{len(groups)} concept(s) are split across two label spellings"
        " — a filter on either one misses half the items",
        sorted({name for group in groups for name in group}),
        groups=groups,
    )


def analyze(snapshot: dict, skew_threshold: float = 0.5, prefix_threshold: float = 0.4) -> list:
    items = open_items(snapshot)
    if not items:
        return []
    declared, in_use = vocabulary(snapshot, items)
    every = sorted(set(declared) | set(in_use))
    found = [
        check_priority_skew(items, skew_threshold),
        check_priority_missing(items),
        check_grouping_missing(items),
        check_grouping_latent(items, every, prefix_threshold),
        check_vocabulary_fossils(declared, in_use),
        check_vocabulary_collision(every),
    ]
    return [f for f in found if f]


def render(snapshot: dict, findings: list[dict], count: int) -> str:
    board = snapshot.get("board") or {}
    header = f"board health — {board.get('name', '?')} ({board.get('backend', '?')})"
    lines = [f"{header} · {count} open item(s)", ""]
    if not findings:
        lines.append("clean — no decay found by any of the 6 checks")
        return "\n".join(lines)
    for found in findings:
        lines.append(f"{found['severity'].upper():4} {found['check']}: {found['finding']}")
        for key, label in (("distribution", "bands"), ("prefixes", "prefixes")):
            if key in found:
                pairs = " · ".join(f"{k} {v}" for k, v in found[key].items())
                lines.append(f"     {label}: {pairs}")
        if "groups" in found:
            pairs = " · ".join(" = ".join(g) for g in found["groups"])
            lines.append(f"     collisions: {pairs}")
        shown = found["affected"][:PRINT_CAP]
        extra = len(found["affected"]) - len(shown)
        lines.append("     " + " ".join(shown) + (f" +{extra} more" if extra else ""))
        lines.append("")
    verdict = "run a triage pass" if any(f["severity"] == "fail" for f in findings) else "hygiene"
    lines.append(f"{len(findings)} finding(s) — {verdict}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decay checks over a board-triage snapshot (SKILL.md §2). "
        "Exit 0 clean, 1 on any finding, 2 on an unreadable snapshot.",
    )
    parser.add_argument("snapshot", nargs="?", help="snapshot JSON path (default: stdin)")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument(
        "--skew-threshold",
        type=float,
        default=0.5,
        help="priority-skew fires above this share in one band (default: 0.5)",
    )
    parser.add_argument(
        "--prefix-threshold",
        type=float,
        default=0.4,
        help="grouping-latent needs at least this share prefixed (default: 0.4)",
    )
    args = parser.parse_args(argv)

    try:
        snapshot = load_snapshot(args.snapshot)
    except SnapshotError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    findings = analyze(snapshot, args.skew_threshold, args.prefix_threshold)
    count = len(open_items(snapshot))
    if args.json:
        print(json.dumps({"board": snapshot.get("board"), "open_items": count,
                          "findings": findings}, indent=2))
    else:
        print(render(snapshot, findings, count))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
