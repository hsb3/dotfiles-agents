#!/usr/bin/env python3
"""Migrate a Kata project's labels onto the core vocabulary. Dry run unless APPLY=1.

A board accumulates label vocabulary the way a codebase accumulates dead code: `bug` and
`type:fix` and `type:-fix` all mean one thing, a retired tracker's column names survive as
labels, and a `priority:high` label sits next to the priority FIELD, disagreeing with it.
Past some point no filter is trustworthy, because every filter misses the cards spelled the
other way. This script reads the rename table in `label-map.yaml` beside it and plans the
minimum label delta that puts one project back on the core vocabulary.

    relabel_board.py --project <p>                       # dry run: the plan, nothing written
    APPLY=1 relabel_board.py --project <p>               # the same plan, executed
    relabel_board.py --project <p> --json                # the plan as a machine summary
    relabel_board.py --project <p> --strip-prefixes --areas skills,repo,ci

Four rules, and three of them are refusals:

**Only an affirmative APPLY in the environment writes** — `1`, `true` or `yes`, matched
case-insensitively with surrounding whitespace ignored. Everything else writes nothing:
`0`, an empty value, `2`, `01`, `1x`, a typo, or the variable unset. It is an env var and
not a flag so it cannot be half-typed into a live run, it is decided in exactly one place
(`apply_enabled`), and every mutating call goes through `_kata_write`, which nothing else
reaches. A bulk relabeler is one bad map away from rewriting every open card on a board, so
the default has to be the harmless one and the plan has to be readable before anyone
commits to it.

**A mirror is skipped.** An issue carrying `metadata.github_issue` is owned by the GitHub
sync, which re-applies the upstream labels and title whenever that issue next changes — so
relabeling one is work that gets silently reverted, and the label to fix is upstream, not
here. Mirrors are counted in the summary, never touched.

**A conflicted card is reported, never guessed.** The vocabulary allows exactly one `type:`
and exactly one `area:` per card. Where the plan would leave two of either, the card gets NO
operations at all — not the conflicting one, not the rest. A partial apply would leave the
card in the conflicted state with the evidence of how it got there already deleted, and
picking a winner is exactly the judgment a human is here for. (A card listed under
`prefixes` as promoted can still be vetoed this way; the conflict entry beside it says so.)

**An unmapped label is reported, never touched.** Absence from the map is a real
disposition: a label whose right home is an owner's call stays out of the map on purpose,
and this run counts it so someone can decide. A wrong rename is worse than a gap — it is
invisible in a diff and wrong on every card at once.

**An apply that dies partway says so, loudly and in its own exit code.** `kata` mutates one
label per call, so a failure between the removal and the addition leaves a card with no
type label at all. On the first failing call the run stops, prints every operation that had
already landed and the one that failed, and exits 3 — not 1, because a wrapper has to be
able to tell "there is work to review" from "the board is half-rewritten". Re-running is
the repair: the plan is recomputed from a fresh `kata list`, so the operations that already
landed simply do not appear again.

Exit 0 when there is nothing to do, 1 on a finding or a pending change, 2 when an input
cannot be read (the map, or the board), 3 when an apply aborted partway. Stdlib only, no
install — shells out to the `kata` binary already on PATH.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import subprocess
import sys

# The ratified core vocabulary (owner ruling 2026-09-08). Closed on purpose: a map target
# outside it is a typo, and a typo here mints a fresh bogus label on every card it touches.
CORE_TYPES = ("type:feat", "type:fix", "type:chore")
CORE_NAMES = frozenset(
    CORE_TYPES + ("epic", "decision", "handoff", "meta", "needs-review", "up-next")
)
AREA = re.compile(r"^area:[a-z0-9][a-z0-9-]*$")
RESERVED = ("keep", "drop")

# `prefix: text`, lowercase slug only — same shape board_health.py reports as `grouping-latent`,
# which is where a caller learns a strip pass is worth running. The trailing space keeps a
# `http://x` style title out.
TITLE_PREFIX = re.compile(r"^([a-z0-9][a-z0-9-]*):\s+")

DEFAULT_MAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "label-map.yaml")


class MapError(Exception):
    """The label map could not be read, parsed, or believed."""


class KataError(Exception):
    """A `kata` call failed. Fatal for a read; on a write it aborts the apply (exit 3)."""


# --- the map ----------------------------------------------------------------
def parse_label_map(text: str) -> dict:
    """Flat one-level YAML -> {label: target}. Format and rationale: label-map.yaml's header.

    Deliberately not a YAML library: these scripts are stdlib-only so they run anywhere with
    no install. The dialect is one `key: value` per line, whole-line `#` comments, and a key
    quoted when it contains a colon. Split on the LAST `": "` and strip the quotes, which
    reads `bug: type:fix` and `"kaneo-status:*": drop` alike.

    Every refusal below exists because the silent version is worse: a skipped malformed line
    is a rename that never happens, a duplicate key is a rename nobody can see losing, and an
    unvalidated target is a typo that becomes a new label on every card it touches.
    """
    mapping: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cut = line.rfind(": ")
        if cut < 0:
            raise MapError(f"label map line {lineno}: expected `label: target`, got {raw!r}")
        key, target = line[:cut].strip().strip('"'), line[cut + 2 :].strip()
        if not key:
            raise MapError(f"label map line {lineno}: empty label")
        if key in mapping:
            raise MapError(
                f"label map line {lineno}: duplicate key {key!r}"
                " — the earlier mapping would lose silently"
            )
        if target not in RESERVED and target not in CORE_NAMES and not AREA.match(target):
            raise MapError(
                f"label map line {lineno}: {target!r} is not a core label"
                f" ({', '.join(sorted(CORE_NAMES))}, area:<x>, or {' / '.join(RESERVED)})"
            )
        mapping[key] = target
    return mapping


def load_label_map(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise MapError(f"cannot read label map {path!r}: {exc}") from exc
    return parse_label_map(text)


def resolve(name: str, mapping: dict) -> str | None:
    """A label's disposition: a core target, `keep`, `drop`, or None for unmapped.

    An exact key beats a glob, which is what lets a malformed twin (`area:-infra`) be
    corrected inside a family (`area:*`) the glob otherwise keeps. Between two globs the
    longer prefix wins, so the answer never depends on dict order.
    """
    if name in mapping:
        return mapping[name]
    for key in sorted((k for k in mapping if k.endswith("*")), key=len, reverse=True):
        if name.startswith(key[:-1]):
            return mapping[key]
    return None


# --- the plan (pure: a list of issue dicts in, a report out) -----------------
def plan(issues: list[dict], mapping: dict, areas=(), strip_prefixes: bool = False) -> dict:
    """`kata list --json` issues -> {relabels, drops, unmapped, conflicts, mirrors_skipped}.

    `relabels` is one record per card that has work: `{key, add, remove}`, plus `title` when
    a prefix strip is planned. `drops` and `unmapped` are counts by label. `areas` is the
    consuming project's own area list (`skills` or `area:skills`, either spelling) and is only
    consulted by the strip mode; with no list, nothing is promoted and every prefixed title is
    reported instead — the fail-safe, not a bug.

    No `kata` call happens in here. That is the point: the whole judgment of this script is
    testable against dicts.
    """
    wanted = {str(a).strip().removeprefix("area:") for a in areas if str(a).strip()}
    report: dict = {
        "relabels": [],
        "drops": collections.Counter(),
        "unmapped": collections.Counter(),
        "conflicts": [],
        "mirrors_skipped": 0,
    }
    if strip_prefixes:
        report["prefixes"] = []

    for issue in issues:
        if (issue.get("metadata") or {}).get("github_issue"):
            report["mirrors_skipped"] += 1
            continue

        key = issue["short_id"]
        labels = list(issue.get("labels") or [])
        remove, add = set(), set()
        for label in labels:
            target = resolve(label, mapping)
            if target is None:
                report["unmapped"][label] += 1
                continue
            if target == "keep":
                continue
            remove.add(label)
            if target != "drop":
                add.add(target)

        title = None
        if strip_prefixes:
            match = TITLE_PREFIX.match(issue.get("title") or "")
            if match:
                prefix = match.group(1)
                entry = {"key": key, "prefix": prefix, "promoted": prefix in wanted}
                report["prefixes"].append(entry)
                if entry["promoted"]:
                    stripped = issue["title"][match.end() :].strip()
                    # What is left has to survive being handed to `kata edit --title`. A
                    # title of "skills: --force the thing" strips to an OPTION, and a title
                    # that is only its prefix strips to nothing at all.
                    if not stripped or stripped.startswith("-"):
                        entry["promoted"] = False
                        entry["reason"] = (
                            "the stripped title is empty or starts with '-', which would"
                            " reach `kata edit --title` as an option rather than a title"
                        )
                    else:
                        title = stripped
                        add.add(f"area:{prefix}")

        final = (set(labels) - remove) | add
        conflicted = False
        for family in ("type:", "area:"):
            clash = sorted(n for n in final if n.startswith(family))
            if len(clash) > 1:
                report["conflicts"].append(
                    {"key": key, "kind": family.rstrip(":"), "labels": clash}
                )
                conflicted = True
        if conflicted:
            continue  # no half-fix: the whole card waits for a human

        add -= set(labels)
        if not (add or remove or title):
            continue
        record = {"key": key, "add": sorted(add), "remove": sorted(remove)}
        if title is not None:
            record["title"] = title
        report["relabels"].append(record)
        for label in remove:
            if resolve(label, mapping) == "drop":
                report["drops"][label] += 1

    return report


def operations(records: list[dict]) -> list:
    """Relabel records -> [(kata argv, one-line description)], removals before additions."""
    ops = []
    for record in records:
        key = record["key"]
        for name in record["remove"]:
            ops.append((["label", "rm", key, name], f"{key} -{name}"))
        for name in record["add"]:
            ops.append((["label", "add", key, name], f"{key} +{name}"))
        if "title" in record:
            ops.append((["edit", key, "--title", record["title"]],
                        f"{key} title -> {record['title']!r}"))
    return ops


def findings(report: dict) -> int:
    """Everything a human still has to look at, whether or not a write happened."""
    return (
        len(report["conflicts"])
        + len(report["unmapped"])
        + sum(1 for p in report.get("prefixes", []) if not p["promoted"])
    )


# --- the world --------------------------------------------------------------
def apply_enabled(env=None) -> bool:
    """The one place that decides whether this run may write. See the module docstring."""
    return (env if env is not None else os.environ).get("APPLY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _kata(args, project):
    proc = subprocess.run(
        ["kata", *args, "--project", project, "--json"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise KataError(
            f"kata {' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}"
        )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _kata_write(args, project):
    """Mutations, and the only path to one. `--agent` output; the exit code is the contract."""
    proc = subprocess.run(
        ["kata", *args, "--project", project, "--agent"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise KataError(
            f"kata {' '.join(args)} -> exit {proc.returncode}: {proc.stderr.strip()}"
        )


def apply_all(records: list[dict], project: str):
    """Execute the plan, stopping at the first failure. -> (applied descriptions, error).

    Stopping rather than pressing on is deliberate: the usual cause is the daemon or the
    auth, and every later call would fail the same way while burying the first message.
    """
    ops = operations(records)
    applied = []
    for index, (argv, description) in enumerate(ops):
        try:
            _kata_write(argv, project)
        except KataError as exc:
            remaining = [d for _, d in ops[index:]]
            return applied, (str(exc), remaining)
        applied.append(description)
    return applied, None


def render(project: str, report: dict, open_items: int, applying: bool, applied: int = 0) -> str:
    lines = [
        f"relabel plan — {project} · {open_items} open item(s)"
        f" · {report['mirrors_skipped']} mirror(s) skipped",
        "",
    ]
    if report["relabels"]:
        verb = "applying" if applying else "would change"
        lines.append(f"{verb} {len(report['relabels'])} card(s):")
        for record in report["relabels"]:
            parts = [f"-{n}" for n in record["remove"]] + [f"+{n}" for n in record["add"]]
            if "title" in record:
                parts.append(f"title={record['title']!r}")
            lines.append(f"  {record['key']:<6} {' '.join(parts)}")
        lines.append("")
    if report["conflicts"]:
        lines.append(
            f"conflicts ({len(report['conflicts'])}) — two of one family on a card;"
            " nothing applied to these, resolve by hand:"
        )
        for clash in report["conflicts"]:
            lines.append(f"  {clash['key']:<6} {clash['kind']}: {' '.join(clash['labels'])}")
        lines.append("")
    if report["unmapped"]:
        total = sum(report["unmapped"].values())
        lines.append(
            f"unmapped ({len(report['unmapped'])} label(s), {total} use(s)) — no entry in the"
            " map, left untouched:"
        )
        lines.append(
            "  " + " · ".join(f"{n} {c}" for n, c in report["unmapped"].most_common())
        )
        lines.append("")
    if report.get("prefixes"):
        stuck = [p for p in report["prefixes"] if not p["promoted"]]
        refused = [p for p in stuck if "reason" in p]
        lines.append(
            f"title prefixes ({len(report['prefixes'])}):"
            f" {len(report['prefixes']) - len(stuck)} promoted, {len(stuck)} reported"
        )
        counts = collections.Counter(p["prefix"] for p in stuck if "reason" not in p)
        if counts:
            lines.append(
                "  not in the area list: "
                + " · ".join(f"{n} {c}" for n, c in counts.most_common())
            )
        for entry in refused:
            lines.append(f"  {entry['key']:<6} refused: {entry['reason']}")
        lines.append("")
    if not report["relabels"] and not findings(report):
        lines.append("clean — every open label is already core")
    elif applying:
        planned = len(operations(report["relabels"]))
        lines.append(f"applied {applied} of {planned} operation(s)")
    else:
        lines.append("dry run — set APPLY=1 to write these changes")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migrate one Kata project's labels onto the core vocabulary, using the"
        " rename table in label-map.yaml. DRY RUN unless APPLY is set to 1, true or yes in"
        " the environment (case-insensitive; anything else, including 0 and empty, is a dry"
        " run). Mirrors (metadata.github_issue) are skipped, cards with two type: or two"
        " area: labels are reported rather than guessed, and a label absent from the map is"
        " reported and left alone. Exit 0 nothing to do, 1 on a finding or a pending change,"
        " 2 on an unreadable input (the map or the board), 3 when an apply aborted partway"
        " — which prints every operation that had already landed.",
        epilog="examples: relabel_board.py --project keel   |   APPLY=1 relabel_board.py"
        " --project keel   |   relabel_board.py --project keel --strip-prefixes"
        " --areas skills,repo,ci",
    )
    parser.add_argument("--project", required=True, help="Kata project to read and relabel")
    parser.add_argument(
        "--map",
        default=DEFAULT_MAP,
        metavar="FILE",
        help="label map (default: label-map.yaml beside this script)",
    )
    parser.add_argument(
        "--strip-prefixes",
        action="store_true",
        help="also move a leading `<prefix>: ` off a title onto area:<prefix> — only for a"
        " prefix in --areas; every other prefixed title is reported, not touched",
    )
    parser.add_argument(
        "--areas",
        default="",
        metavar="a,b,c",
        help="this project's area list, comma-separated (`skills` or `area:skills`). It is"
        " the consuming repo's own config, so there is no default: with no list,"
        " --strip-prefixes promotes nothing and reports everything",
    )
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    args = parser.parse_args(argv)

    try:
        mapping = load_label_map(args.map)
    except MapError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        listed = _kata(["list", "--status", "open", "--limit", "0"], args.project)
    except KataError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    issues = listed.get("issues", [])
    report = plan(
        issues,
        mapping,
        areas=[a for a in args.areas.split(",") if a.strip()],
        strip_prefixes=args.strip_prefixes,
    )

    applying = apply_enabled()
    applied, abort = ([], None)
    if applying:
        applied, abort = apply_all(report["relabels"], args.project)

    if args.json:
        print(json.dumps(
            {"project": args.project, "open_items": len(issues), "applied": applied,
             "aborted": abort[0] if abort else None, **report},
            indent=2,
        ))
    else:
        print(render(args.project, report, len(issues), applying, len(applied)))

    if abort:
        reason, remaining = abort
        sys.stdout.flush()  # so the plan is above the abort in a redirected transcript
        print(
            f"\nAPPLY ABORTED after {len(applied)} operation(s): {reason}\n"
            "  applied: " + (" · ".join(applied) or "(none)") + "\n"
            "  not applied: " + " · ".join(remaining) + "\n"
            "  A card can be mid-change — re-run to finish; the plan is recomputed from a"
            " fresh `kata list`, so what already landed will not repeat.",
            file=sys.stderr,
        )
        return 3

    pending = bool(report["relabels"]) and not applying
    return 1 if pending or findings(report) else 0


if __name__ == "__main__":
    sys.exit(main())
