#!/usr/bin/env python3
"""Symlink-assembly lint — the drift-guard successor for the pointer-based marketplace (ADR 0017).

`plugins/<id>/` are thin symlink assemblies over `primitives-core/`; the root
`.claude-plugin/marketplace.json` lists each plugin by relative source path. Claude Code
dereferences in-repo symlinks at install time but SILENTLY SKIPS any symlink whose target
resolves outside the marketplace repo — a broken or escaping link ships a silently
incomplete plugin. This lint makes that failure mode loud:

  1. every symlink under plugins/ resolves to an existing path INSIDE the repo;
  2. every plugin entry in the root marketplace.json points (via a relative ./ source)
     at an existing plugin dir that carries .claude-plugin/plugin.json;
  3. every plugins/<id>/ dir is listed in the root marketplace.json (no orphan assemblies).

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_symlinks.py   (run from anywhere)
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(REPO, "plugins")
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")


def symlink_problems():
    problems = []
    repo_real = os.path.realpath(REPO)
    for dirpath, dirs, files in os.walk(PLUGINS_DIR):
        for name in sorted(dirs + files):
            fp = os.path.join(dirpath, name)
            if not os.path.islink(fp):
                continue
            rel = os.path.relpath(fp, REPO)
            target = os.path.realpath(fp)
            if not os.path.exists(target):
                problems.append(f"{rel}: broken symlink (target does not exist)")
            elif os.path.commonpath([repo_real, target]) != repo_real:
                problems.append(
                    f"{rel}: target escapes the repo ({target}) — Claude Code silently "
                    "skips out-of-marketplace symlinks at install"
                )
    return problems


def marketplace_problems():
    problems = []
    if not os.path.isfile(MARKETPLACE):
        return [".claude-plugin/marketplace.json: missing at the repo root"]
    with open(MARKETPLACE, encoding="utf-8") as fh:
        market = json.load(fh)
    listed = set()
    for entry in market.get("plugins", []):
        name = entry.get("name", "?")
        source = entry.get("source", "")
        if not source.startswith("./"):
            problems.append(f"marketplace.json[{name}]: source {source!r} is not a relative ./ path")
            continue
        pdir = os.path.join(REPO, source[2:])
        listed.add(os.path.normpath(pdir))
        if not os.path.isdir(pdir):
            problems.append(f"marketplace.json[{name}]: source dir {source} does not exist")
        elif not os.path.isfile(os.path.join(pdir, ".claude-plugin", "plugin.json")):
            problems.append(f"marketplace.json[{name}]: {source} has no .claude-plugin/plugin.json")
    if os.path.isdir(PLUGINS_DIR):
        for d in sorted(os.listdir(PLUGINS_DIR)):
            pdir = os.path.normpath(os.path.join(PLUGINS_DIR, d))
            if os.path.isdir(pdir) and pdir not in listed:
                problems.append(f"plugins/{d}: assembly not listed in .claude-plugin/marketplace.json")
    return problems


def main():
    if not os.path.isdir(PLUGINS_DIR):
        print("✗ symlink lint: plugins/ does not exist")
        return 1
    problems = symlink_problems() + marketplace_problems()
    if problems:
        print(f"✗ symlink lint: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    n_links = sum(
        1
        for dirpath, dirs, files in os.walk(PLUGINS_DIR)
        for name in dirs + files
        if os.path.islink(os.path.join(dirpath, name))
    )
    n_plugins = sum(1 for d in os.listdir(PLUGINS_DIR) if os.path.isdir(os.path.join(PLUGINS_DIR, d)))
    print(
        f"✓ symlink assemblies clean — {n_plugins} plugin(s), {n_links} symlink(s) all "
        "resolve in-repo; marketplace.json entries and assemblies match 1:1"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
