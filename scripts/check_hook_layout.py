#!/usr/bin/env python3
"""Hook-layout check — D6 machine-floor check 4 (entry-gate spec).

The gate ACCEPTS the ratified hook-dir layout and rejects the old flat-handler layout (the H4
fork is resolved). Each hook is a directory holding its handler as `hook.py`:

    hooks/<name>/hook.py            (+ optional config.json / hook.json beside it)

Violations:
  - a `.sh` handler anywhere under a hook root                → old flat-handler style
  - a `hooks-handlers/` directory                            → legacy layout
  - a hook directory (one carrying config.json/hook.json/hook.py) with no `hook.py`
  - a stray `.py` / `.json` file at a hook root, not inside a `<name>/` hook dir

No hooks ship yet (the hook roots hold only `.gitkeep`), so this is vacuously green today; the
fixture in the tests proves it goes red on a wrong-layout hook.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violation.
Usage: python3 scripts/check_hook_layout.py   (run from the repo root)
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_ROOTS = (
    os.path.join(REPO, "hooks"),
    os.path.join(REPO, "primitives-core", "hooks"),
)
HOOK_MARKERS = ("hook.py", "config.json", "hook.json")


def check_root(root, rel_base):
    """Return layout violations for one hook root (absolute path)."""
    problems = []
    if not os.path.isdir(root):
        return problems

    # Tree-wide bans: legacy shell handlers and the old hooks-handlers/ directory.
    for dirpath, dirs, files in os.walk(root):
        for d in dirs:
            if d == "hooks-handlers":
                rel = os.path.relpath(os.path.join(dirpath, d), rel_base)
                problems.append(f"{rel}: legacy hooks-handlers/ layout — use <name>/hook.py")
        for f in files:
            if f.endswith(".sh"):
                rel = os.path.relpath(os.path.join(dirpath, f), rel_base)
                problems.append(f"{rel}: shell handler — hooks use <name>/hook.py (stdlib Python)")

    # Immediate children of the root: each hook must be a <name>/ dir carrying hook.py.
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        rel = os.path.relpath(full, rel_base)
        if os.path.isfile(full):
            if entry == ".gitkeep":
                continue
            if entry.endswith((".py", ".json")):
                problems.append(f"{rel}: hook file at the root — put it in <name>/hook.py")
            continue
        if os.path.isdir(full):
            names = set(os.listdir(full))
            if names & set(HOOK_MARKERS) and "hook.py" not in names:
                problems.append(f"{rel}/: hook dir missing hook.py (ratified layout <name>/hook.py)")
    return problems


def main():
    problems = []
    for root in HOOK_ROOTS:
        problems.extend(check_root(root, REPO))
    problems = sorted(set(problems))
    if problems:
        print(f"✗ hook-layout: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ hook-layout clean — ratified hooks/<name>/hook.py layout")
    return 0


if __name__ == "__main__":
    sys.exit(main())
