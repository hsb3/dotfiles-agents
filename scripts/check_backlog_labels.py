#!/usr/bin/env python3
"""Backlog label-vocabulary guard — keeps `backlog/` labels a closed, two-axis set.

Backlog.md validates `types` and `statuses` against the project config but does NOT
validate `labels`: `backlog task create -l anything-at-all` is accepted silently, and the
config's `labels:` list is only an autocomplete hint. That asymmetry is how this repo
accumulated 17 ad-hoc labels (12 used exactly once, mixing area, plugin name, and kind)
while the two labels actually declared in config went unused. This check supplies the
missing enforcement.

The vocabulary has two axes and only two:

    area    where the work lands       EXACTLY ONE per task
    signal  a scheduling fact that `type` and `status` cannot carry   AT MOST ONE

So a conforming task carries one or two labels, never more, never zero. A task that
appears to need two areas is two tasks; `decision` and `on-hold` are mutually exclusive
by construction (a card parked on purpose is not the card you are awaiting a ruling on).

AREAS/SIGNALS below are the source of truth for the split, because YAML comments cannot
be parsed reliably. Check 1 cross-validates them against `backlog/config.yml`, so editing
either side alone goes red — neither can drift silently.

Scope is the live board (`backlog/tasks/`, `backlog/drafts/`, `backlog/completed/`).
`backlog/archive/` is excluded: archived cards are history, and relabelling history is
noise. Milestones, decisions, and docs carry no labels and are not walked.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violation.
Usage: python3 scripts/check_backlog_labels.py   (run from the repo root)
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(REPO, "backlog", "config.yml")
BOARD_DIRS = ("tasks", "drafts", "completed")

AREAS = frozenset(
    {
        "primitives",  # primitives-core/ sources: skills, agents, hooks, commands
        "assembly",  # plugins/, marketplace.json, bundle composition, the lineup
        "distribution",  # publish, opencode laydown, install scripts, externals
        "gates",  # Makefile, CI workflows, checks, flow.yaml
        "harness",  # harness/ workbench
        "evals",  # evals/ workbench, benchmarks, the extender database
        "governance",  # ADRs, SOPs, backlog conventions, repo docs
    }
)
SIGNALS = frozenset({"decision", "on-hold"})


def parse_config_labels(text):
    """Return the `labels:` values from a Backlog.md config, inline or block form."""
    m = re.search(r"^labels:[ \t]*(.*)$", text, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline.startswith("["):
        body = inline[1:].split("]")[0]
        return [v.strip().strip("\"'") for v in body.split(",") if v.strip()]
    labels = []
    for line in text[m.end():].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^[ \t]+-[ \t]+(.*)$", line)
        if not item:
            break
        labels.append(item.group(1).split("#")[0].strip().strip("\"'"))
    return labels


def parse_task_labels(text):
    """Return the `labels:` values from a task's frontmatter, inline or block form."""
    if not text.startswith("---"):
        return []
    frontmatter = text.split("---", 2)[1] if text.count("---") >= 2 else ""
    return parse_config_labels(frontmatter)


def check_vocabulary(config_text):
    """Check 1: the config's flat label list matches this module's two-axis split."""
    declared = set(parse_config_labels(config_text))
    expected = set(AREAS | SIGNALS)
    if declared == expected:
        return []
    problems = []
    for label in sorted(declared - expected):
        problems.append(
            f"backlog/config.yml declares '{label}', which is in neither AREAS nor "
            f"SIGNALS in scripts/check_backlog_labels.py — add it to one axis or drop it"
        )
    for label in sorted(expected - declared):
        problems.append(
            f"scripts/check_backlog_labels.py knows '{label}' but backlog/config.yml "
            f"does not declare it — the CLI will not offer it"
        )
    return problems


def check_board(board_root, rel_base):
    """Checks 2-4: every card on the board carries one area and at most one signal."""
    problems = []
    for sub in BOARD_DIRS:
        d = os.path.join(board_root, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md") or name == "README.md":
                continue
            full = os.path.join(d, name)
            with open(full, encoding="utf-8") as fh:
                labels = parse_task_labels(fh.read())
            rel = os.path.relpath(full, rel_base)
            unknown = [x for x in labels if x not in AREAS and x not in SIGNALS]
            for label in sorted(set(unknown)):
                problems.append(f"{rel}: unknown label '{label}' — not in backlog/config.yml")
            areas = [x for x in labels if x in AREAS]
            signals = [x for x in labels if x in SIGNALS]
            if len(areas) == 0:
                problems.append(f"{rel}: no area label — every card needs exactly one of {sorted(AREAS)}")
            elif len(areas) > 1:
                problems.append(
                    f"{rel}: {len(areas)} area labels ({', '.join(sorted(areas))}) — "
                    f"exactly one; work spanning two areas is two tasks"
                )
            if len(signals) > 1:
                problems.append(
                    f"{rel}: {len(signals)} signal labels ({', '.join(sorted(signals))}) — at most one"
                )
    return problems


def main():
    if not os.path.isdir(os.path.join(REPO, "backlog")):
        print("✓ backlog-labels — no backlog/ directory, nothing to check")
        return 0
    with open(CONFIG, encoding="utf-8") as fh:
        config_text = fh.read()

    problems = check_vocabulary(config_text)
    problems.extend(check_board(os.path.join(REPO, "backlog"), REPO))

    if problems:
        print(f"✗ backlog-labels: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"✓ backlog-labels clean — closed vocabulary "
        f"({len(AREAS)} area + {len(SIGNALS)} signal), one area per card"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
