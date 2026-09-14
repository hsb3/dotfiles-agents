#!/usr/bin/env python3
"""Symlink-assembly lint — the drift-guard successor for the pointer-based marketplace (decision-030).

`plugins/<id>/` are thin symlink assemblies over `primitives-core/`; the root
`.claude-plugin/marketplace.json` lists each plugin by relative source path. Claude Code
dereferences in-repo symlinks at install time but SILENTLY SKIPS any symlink whose target
resolves outside the marketplace repo — a broken or escaping link ships a silently
incomplete plugin. This lint makes that failure mode loud:

  1. every symlink under plugins/ resolves to an existing path INSIDE the repo;
  2. every plugin entry in the root marketplace.json points (via a relative ./ source)
     at an existing plugin dir that carries .claude-plugin/plugin.json;
  3. every plugins/<id>/ dir is listed in the root marketplace.json (no orphan assemblies);
  4. every STANDALONE plugin symlinks README.md to its own skill's README (decision-030 /
     flow.yaml's plugin-assemblies node). The standalone/bundle line is drawn mechanically:
     a plugin whose assembly contains exactly one skill and no agents, hooks, or commands
     is a STANDALONE — its README.md must be a symlink to
     primitives-core/skills/<skill-id>/README.md, so the docs travel with the source
     instead of drifting from it. Any plugin with more than one skill, or any agent, hook,
     or command, is a BUNDLE — a command is a shipped surface beyond the one skill, so it
     takes the assembly off the standalone path (decision-010). Bundle READMEs are
     hand-authored regular files and this check does not touch them.

     NOTE — this rule is a FORWARD GUARD, kept regardless of how many assemblies are
     currently standalone: main()'s success line reports that count at runtime (never
     hardcode it here — a hardcoded count is exactly the kind of claim that drifts from
     the gate). It stays exercised by synthetic fixtures in tests/test_check_symlinks.py
     even when the real lineup has zero standalone subjects.

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


def _named_entries(dirpath):
    """Non-hidden entry names directly under dirpath, or [] if it doesn't exist."""
    if not os.path.isdir(dirpath):
        return []
    return sorted(e for e in os.listdir(dirpath) if not e.startswith("."))


def is_standalone(pdir):
    """A plugin is standalone iff its assembly has exactly one skill and no agents, hooks,
    or commands."""
    skills = _named_entries(os.path.join(pdir, "skills"))
    return (
        len(skills) == 1
        and not _named_entries(os.path.join(pdir, "agents"))
        and not _named_entries(os.path.join(pdir, "hooks"))
        and not _named_entries(os.path.join(pdir, "commands"))
    )


def readme_problems():
    """README.md convention for standalone plugins — see the module docstring for the rule."""
    problems = []
    if not os.path.isdir(PLUGINS_DIR):
        return problems
    for d in sorted(os.listdir(PLUGINS_DIR)):
        pdir = os.path.join(PLUGINS_DIR, d)
        if not os.path.isdir(pdir) or not is_standalone(pdir):
            continue  # bundles may hand-author README.md as a regular file
        skill_id = _named_entries(os.path.join(pdir, "skills"))[0]
        readme = os.path.join(pdir, "README.md")
        rel = os.path.relpath(readme, REPO)
        expected_rel = f"primitives-core/skills/{skill_id}/README.md"
        if not os.path.lexists(readme):
            problems.append(
                f"{rel}: missing — standalone plugin (1 skill, no agents/hooks/commands) "
                f"must symlink README.md to {expected_rel}"
            )
        elif not os.path.islink(readme):
            problems.append(
                f"{rel}: regular file — standalone plugins must symlink README.md to "
                f"the skill's own README ({expected_rel}); only bundle assemblies "
                "(>1 skill, or any agent/hook/command) may hand-author README.md"
            )
        else:
            actual = os.path.realpath(readme)
            expected = os.path.realpath(os.path.join(REPO, expected_rel))
            if not os.path.exists(actual):
                problems.append(f"{rel}: dangling symlink — expected target {expected_rel} does not exist")
            elif actual != expected:
                problems.append(f"{rel}: symlink target {actual!r} does not match the expected {expected_rel}")
    return problems


def main():
    if not os.path.isdir(PLUGINS_DIR):
        print("✗ symlink lint: plugins/ does not exist")
        return 1
    problems = symlink_problems() + marketplace_problems() + readme_problems()
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
    n_standalone = sum(
        1
        for d in os.listdir(PLUGINS_DIR)
        if os.path.isdir(os.path.join(PLUGINS_DIR, d)) and is_standalone(os.path.join(PLUGINS_DIR, d))
    )
    print(
        f"✓ symlink assemblies clean — {n_plugins} plugin(s) ({n_standalone} standalone), "
        f"{n_links} symlink(s) all resolve in-repo; marketplace.json entries and assemblies "
        "match 1:1"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
