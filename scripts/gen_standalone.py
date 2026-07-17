#!/usr/bin/env python3
"""gen_standalone.py — Claude Code one-skill plugin wrappers for the standalone catalog (D4).

Claude Code installs a skill by installing a *plugin* that contains it. To let a catalogued
skill ship on its own (`/plugin install <skill>@dotfiles-agents` pulling ONLY that skill), we
generate a one-skill plugin per catalog entry: `.claude-plugin/plugin.json` (name == skill id)
plus `skills/<skill>/` copied verbatim from primitives-core — the same single source the
bundles are built from, so the wrapped body is byte-identical to source.

Wired into the committed build at D4: `scripts/gen_marketplace.py` calls `build_standalone()`
to emit each wrapper into `plugins/<skill-id>/` and merges `standalone_entries()` into the one
`.claude-plugin/marketplace.json`, so a standalone `private-fork` plugin resolves as a one-skill
install alongside the bundles. A standalone wrapper's plugin name is the skill id; the catalog
guard (check_skill_catalog.py) enforces that it never clashes with a bundle id.

Stand-alone entry points (used by tests + as an independent invariant guard):
  python3 scripts/gen_standalone.py --out DIR   emit wrappers under DIR/<id>/
  python3 scripts/gen_standalone.py --check      build to a temp dir + assert invariants

Invariants asserted by --check (and by the unit tests):
  - exactly one skill folder per wrapper (a wrapper exposes only its own skill).
  - the plugin name equals the skill id.
  - every wrapped skill body is byte-identical to primitives-core/skills/<id>/.

Stdlib-only, deterministic (stable ordering, no clocks), so it never false-fails a drift check.
"""

import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import check_skill_catalog as C  # noqa: E402
from check_roster import parse_roster  # noqa: E402

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")
DEFAULT_VERSION = "0.0.1"


def _unquote(v):
    v = (v or "").strip()
    if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
        return v[1:-1]
    return v


def author():
    """The marketplace owner, read from plugins.yaml (the single authorship data surface) so a
    standalone wrapper's author matches the bundles' — no hardcoded name in the generator."""
    name = ""
    in_owner = False
    with open(PLUGINS_YAML, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if re.match(r"^owner:\s*$", line):
                in_owner = True
                continue
            if re.match(r"^\S", line):
                in_owner = False
                continue
            if in_owner:
                m = re.match(r"^  name:\s*(.*)$", line)
                if m:
                    name = _unquote(m.group(1))
    return {"name": name}


def catalog_claude_entries():
    """Return the catalog entries whose clients include claude-code (the ones we wrap), joined
    to their roster entry: a list of (catalog_entry, roster_entry), sorted by skill id."""
    roster = {e["id"]: e for e in parse_roster(C.ROSTER)}
    out = []
    for entry in C.parse_catalog(C.CATALOG):
        if "claude-code" not in entry.get("clients", []):
            continue
        r = roster.get(entry["id"])
        if r is not None:
            out.append((entry, r))
    return sorted(out, key=lambda x: x[0]["id"])


def plugin_manifest(skill_id, roster_entry):
    """The `.claude-plugin/plugin.json` payload for a one-skill wrapper (name == skill id)."""
    return {
        "name": skill_id,
        "description": _unquote(roster_entry.get("summary", "")),
        "version": DEFAULT_VERSION,
        "author": author(),
    }


def write_wrapper(out_root, catalog_entry, roster_entry):
    """Emit one wrapper under out_root/<id>/ and return its path."""
    skill_id = catalog_entry["id"]
    proot = os.path.join(out_root, skill_id)
    os.makedirs(os.path.join(proot, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(proot, ".claude-plugin", "plugin.json"), "w") as fh:
        json.dump(plugin_manifest(skill_id, roster_entry), fh, indent=2, sort_keys=True)
        fh.write("\n")
    src = os.path.join(REPO, roster_entry["source"])
    shutil.copytree(src, os.path.join(proot, "skills", skill_id), ignore=IGNORE)
    return proot


def build_standalone(out_root):
    """Emit every claude-code standalone wrapper under out_root/<id>/. Returns list of ids."""
    ids = []
    for catalog_entry, roster_entry in catalog_claude_entries():
        write_wrapper(out_root, catalog_entry, roster_entry)
        ids.append(catalog_entry["id"])
    return ids


def standalone_entries():
    """Marketplace plugin entries for each standalone wrapper (source ./plugins/<id>), sorted
    by id — merged into marketplace.json by gen_marketplace so `<id>@dotfiles-agents` resolves."""
    a = author()
    out = []
    for catalog_entry, roster_entry in catalog_claude_entries():
        sid = catalog_entry["id"]
        out.append(
            {
                "name": sid,
                "source": f"./plugins/{sid}",
                "description": _unquote(roster_entry.get("summary", "")),
                "version": DEFAULT_VERSION,
                "author": a,
            }
        )
    return out


def _dircmp_identical(a, b):
    """True iff dir trees a and b are byte-identical (recursive, ignoring nothing)."""
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(
        _dircmp_identical(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs
    )


def verify_wrappers(out_root, ids):
    """Assert the invariants over freshly-built wrappers. Returns a list of problems."""
    problems = []
    for skill_id in ids:
        proot = os.path.join(out_root, skill_id)
        skills_dir = os.path.join(proot, "skills")
        contents = sorted(os.listdir(skills_dir)) if os.path.isdir(skills_dir) else []
        if contents != [skill_id]:
            problems.append(
                f"[{skill_id}] wrapper exposes {contents}, expected exactly ['{skill_id}']"
            )
            continue
        with open(os.path.join(proot, ".claude-plugin", "plugin.json")) as fh:
            manifest = json.load(fh)
        if manifest.get("name") != skill_id:
            problems.append(f"[{skill_id}] plugin name {manifest.get('name')!r} != skill id")
        src = os.path.join(REPO, "primitives-core", "skills", skill_id)
        if not _dircmp_identical(src, os.path.join(skills_dir, skill_id)):
            problems.append(
                f"[{skill_id}] wrapped body is NOT byte-identical to primitives-core source"
            )
    return problems


def main(argv=None):
    p = argparse.ArgumentParser(prog="gen_standalone.py", description=__doc__.split("\n")[0])
    p.add_argument("--out", metavar="DIR", help="emit wrappers under DIR (created if absent)")
    p.add_argument("--check", action="store_true", help="build to a temp dir and assert invariants")
    args = p.parse_args(argv)

    if args.check or not args.out:
        tmp = tempfile.mkdtemp(prefix="gen-standalone-check-")
        try:
            ids = build_standalone(tmp)
            problems = verify_wrappers(tmp, ids)
            if problems:
                print(f"✗ standalone wrappers: {len(problems)} problem(s)")
                for pr in problems:
                    print(f"  - {pr}")
                return 1
            print(f"✓ standalone wrappers OK — {len(ids)} one-skill plugin(s), all byte-identical to source")
            return 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    os.makedirs(args.out, exist_ok=True)
    ids = build_standalone(args.out)
    print(f"✓ emitted {len(ids)} standalone wrapper(s) under {args.out}: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
