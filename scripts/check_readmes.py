#!/usr/bin/env python3
"""Per-unit README gate — every skill and every plugin documents itself.

Two surfaces ship to a human reader: `primitives-core/skills/<name>/README.md` (what the
skill is, when it fires, which bundle carries it) and `plugins/<id>/README.md` (the bundle's
front page, linked from the root catalog). Neither is generated, so neither appears unless
someone writes it — a new skill lands documented only by its own `description`, which is a
router string for the model, not an explanation for a person.

Skills are the surface with no other cover. A missing `plugins/<id>/README.md` already turns
`scripts/check_catalog.py` red, because the root catalog row links to it and that guard
resolves every relative link against disk; the plugin half here is deliberate redundancy, so
the invariant is stated where someone would grep for it rather than being an emergent
property of a link check. A missing skill README was invisible to every gate until this one.

Three checks per unit:

  1. `README.md` exists (symlinks are followed — standalone plugin READMEs are symlinks to
     the member skill's README under ADR 0017, and a dangling one is a missing README).
  2. It is non-empty once whitespace is stripped. An empty file passes an existence check
     and documents nothing.
  3. Its first non-blank line is an ATX H1 (`# `). Every README in the tree already opens
     this way; the catalog and the diagram guard both read plugin READMEs as rendered
     markdown, and a body with no title renders headless.

Deliberately NOT covered: whether the prose is any good, whether the `## Install` line names
the bundle that actually ships the skill, section structure, or length. Flat primitives
(`agents/`, `commands/`) are exempt by convention — they are single `.md` files documented by
one family README per directory, which `scripts/check_roster.py` already treats as
non-primitives.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_readmes.py   (run from anywhere)
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO, "primitives-core", "skills")
PLUGINS_DIR = os.path.join(REPO, "plugins")


def _units():
    """(label, absolute dir) for every unit that owes a README, sorted and deterministic."""
    out = []
    for kind, root in (("skill", SKILLS_DIR), ("plugin", PLUGINS_DIR)):
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if os.path.isdir(path) and not name.startswith("."):
                out.append((kind, name, path))
    return out


def problems():
    out = []
    for kind, name, path in _units():
        readme = os.path.join(path, "README.md")
        rel = os.path.relpath(readme, REPO)
        if not os.path.isfile(readme):
            out.append(f"{kind} '{name}': no README.md at {rel}")
            continue
        try:
            with open(readme, encoding="utf-8") as fh:
                body = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            out.append(f"{kind} '{name}': {rel} is unreadable ({exc})")
            continue
        if not body.strip():
            out.append(f"{kind} '{name}': {rel} is empty")
            continue
        first = next(line for line in body.splitlines() if line.strip())
        if not first.startswith("# "):
            out.append(f"{kind} '{name}': {rel} does not open with an H1 — first line is {first.strip()!r}")
    return out


def main():
    found = problems()
    if found:
        print(f"✗ README gate: {len(found)} problem(s)")
        for p in found:
            print(f"  - {p}")
        return 1
    n = len(_units())
    print(f"✓ README gate clean — {n} unit(s), each with a titled README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
