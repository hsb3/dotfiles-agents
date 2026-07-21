#!/usr/bin/env python3
"""No-repo-coupling gate for harness/ (DESIGN §5).

harness/ is a self-contained uv project whose extraction to its own repo is a
plain directory move — so nothing under harness/agent_harness/ may import from or
reference repo files outside harness/. Candidates and cases are passed as paths at
runtime (--candidate-dir / --cases-dir), never resolved from a sibling directory.

This is the make-reachable, stdlib-only mirror of harness/tests/test_coupling.py
(which needs the uv test lane): `make ci` runs THIS so the invariant is guarded
even in the zero-install marketplace lane. Kept deliberately narrow — it scans the
shipped package only, not tests/ (fixtures legitimately name sibling paths).

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = coupling found.
Usage: python3 scripts/check_harness_coupling.py   (run from the repo root)
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "harness", "agent_harness")

# Substrings that betray a reach outside harness/ — sibling-repo dirs, the
# workbench chassis it was ported from, and absolute-import escapes into repo
# modules. `.claude-plugin` is intentionally NOT here: it is a Claude Code
# structural token the synthetic-plugin wrapper writes, not a repo path.
FORBIDDEN = (
    "primitives-core",
    "dotfiles-agents-workbench",
    "incubator/",
    "scripts/run_eval",
    "import run_eval",
    "from scripts",
    "import scripts",
)

# Import prefixes a harness module must never use (repo packages).
FORBIDDEN_IMPORT_PREFIXES = ("scripts", "tests", "primitives")


def _iter_py(root):
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith(".py"):
                yield os.path.join(dirpath, f)


def check():
    """Return a sorted list of coupling violations under the shipped package."""
    problems = []
    if not os.path.isdir(PKG):
        return [f"{os.path.relpath(PKG, REPO)}: package directory missing"]
    for path in _iter_py(PKG):
        rel = os.path.relpath(path, PKG)
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        text = "".join(lines)
        for token in FORBIDDEN:
            if token in text:
                problems.append(f"{rel}: forbidden reference {token!r}")
        for i, line in enumerate(lines, 1):
            s = line.strip()
            mod = None
            if s.startswith("from ") and "agent_harness" not in s:
                mod = s.split()[1]
            elif s.startswith("import "):
                mod = s.split()[1].split(".")[0]
            if mod and mod.split(".")[0] in FORBIDDEN_IMPORT_PREFIXES:
                problems.append(f"{rel}:{i}: repo-module import {s!r}")
    return sorted(set(problems))


def main():
    problems = check()
    if problems:
        print(f"✗ harness-coupling: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ harness-coupling clean — harness/ imports only itself + stdlib")
    return 0


if __name__ == "__main__":
    sys.exit(main())
