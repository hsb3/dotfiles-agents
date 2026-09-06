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

Five checks per unit:

  1. `README.md` exists (symlinks are followed — standalone plugin READMEs are symlinks to
     the member skill's README under ADR 0017, and a dangling one is a missing README).
  2. It is non-empty once whitespace is stripped. An empty file passes an existence check
     and documents nothing.
  3. Its first non-blank line is an ATX H1 (`# `). Every README in the tree already opens
     this way; the catalog and the diagram guard both read plugin READMEs as rendered
     markdown, and a body with no title renders headless.

  4. (skills) The `## Install` block names exactly the plugins that ship the skill. The set
     named by `claude plugin install <id>@dotfiles-agents` lines must equal the set of
     `plugins/*/skills/<skill>` entries on disk — derived live, never recorded. This is the
     one line a reader copies and runs; measured 2026-08-22 it was wrong for 34 of 42 skills.
  5. (plugins) Every member the assembly ships — `skills/<id>`, `agents/<id>.md`,
     `commands/<id>.md`, `hooks/<id>/` — is named in the plugin README, as `` `<id>` `` or
     as its H1. A member can otherwise ship in a bundle and appear in no table (measured
     2026-09-06: solo-skills shipped 36 skills and listed 29).

Deliberately NOT covered: whether the prose is any good, section structure, or length. Flat primitives
(`agents/`, `commands/`) are exempt by convention — they are single `.md` files documented by
one family README per directory, which `scripts/check_roster.py` already treats as
non-primitives.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_readmes.py   (run from anywhere)
"""

import os
import re
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


INSTALL_RE = re.compile(r"claude plugin install ([A-Za-z0-9_.-]+)@dotfiles-agents")


def _shipping_plugins(skill):
    """Plugin ids whose assembly carries `skills/<skill>`, derived from disk."""
    if not os.path.isdir(PLUGINS_DIR):
        return set()
    return {
        p for p in os.listdir(PLUGINS_DIR)
        if not p.startswith(".") and os.path.exists(os.path.join(PLUGINS_DIR, p, "skills", skill))
    }


def _members(plugin_dir):
    """Member ids an assembly ships: skill/hook dirs, agent/command file stems."""
    ids = set()
    for sub in ("skills", "hooks"):
        d = os.path.join(plugin_dir, sub)
        if os.path.isdir(d):
            ids |= {n for n in os.listdir(d) if os.path.isdir(os.path.join(d, n)) and not n.startswith(("_", "."))}
    for sub in ("agents", "commands"):
        d = os.path.join(plugin_dir, sub)
        if os.path.isdir(d):
            ids |= {n[:-3] for n in os.listdir(d) if n.endswith(".md") and n != "README.md"}
    return ids


def _named(member, body):
    return re.search(r"(?:`|/|^# )" + re.escape(member) + r"(?:`|/|\.md|\s|$)", body, re.MULTILINE) is not None


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
        if kind == "skill":
            named, ships = set(INSTALL_RE.findall(body)), _shipping_plugins(name)
            if named != ships:
                out.append(
                    f"{kind} '{name}': {rel} install block names {sorted(named)} but the skill ships in "
                    f"{sorted(ships)} — list exactly the plugins whose assembly carries it"
                )
        else:
            for member in sorted(_members(path) - {name}):
                if not _named(member, body):
                    out.append(f"{kind} '{name}': {rel} never names shipped member `{member}`")
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
