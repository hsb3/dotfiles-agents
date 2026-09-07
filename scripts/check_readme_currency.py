#!/usr/bin/env python3
"""README-currency gate — the last change to a unit also touched that unit's README.

`check_readmes.py` proves a README exists and is shaped right. Nothing proved it still
DESCRIBES the thing it sits next to: a skill's body can be rewritten a dozen times while
its README keeps describing the first version, and no gate notices. decision-015 rules
that currency is derived from git with no tracked registry, and that the acknowledgement
is the README being touched in the same change.

The rule, per unit (`primitives-core/skills/<id>/`, `plugins/<id>/` — the two surfaces
that own a README, decision-015 point 5):

  * body commit  = `git log -1` over the unit dir with its own README excluded. Any file
    in the unit counts, not just SKILL.md (decision-015 point 2).
  * README commit = `git log -1` over `<unit>/README.md`.
  * The unit is current when the body commit is an ancestor-or-equal of the README
    commit — i.e. the README was touched in that same commit, or in one that came after
    it. Same-commit is the acknowledgement decision-015 names; a later commit is a
    strictly stronger signal (someone looked at the README after the body moved), so
    rejecting it would be a false positive.

Two scope decisions, both taking the narrowest honest reading:

  * **Plugins are read as their own tracked files only** — `plugin.json`, `hooks.json`,
    the bundle README, and the symlink ENTRIES (a retargeted or added/removed link is a
    change to `plugins/<id>/`). The gate does NOT follow a symlink into
    `primitives-core/`. Under ADR 0017 an assembly is a membership statement, and that is
    what its README documents; a member skill's body change is already answerable by that
    skill's own unit. Following links would make every bundle stale whenever any member
    moved, and the plugin README could not honestly acknowledge it.
  * **Committed history only.** The working tree and the index are not read: "touched in
    the same change" has no meaning before there is a change. Uncommitted work is
    invisible here and lands red on the next run — CI runs on the PR's checkout, which is
    the authoritative one.

The gate is anchored at the commit that added decision-015 (found by pathspec, not by a
recorded SHA): a unit whose last body change predates the ruling is not evaluated, since
32 of 56 units were stale the day the rule landed and a retroactive gate would just be a
mass-touch. Delete the anchor once those are backfilled. No anchor found on disk (a fresh
fixture, or the doc renamed) means full history is evaluated — the strict direction, so a
rename fails loud rather than quietly disabling the gate.

Needs real history: a shallow clone is a hard failure, not a skip, because every unit
would trivially pass in one (`actions/checkout` is depth-1 unless told otherwise).

Stdlib-only, deterministic (git topology, no clocks, sorted output). Exit 0 = clean;
exit 1 = violations (prints every one).
Usage: python3 scripts/check_readme_currency.py [repo-root]   (run from anywhere)
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT_ROOTS = (("skill", "primitives-core/skills"), ("plugin", "plugins"))
ANCHOR_PATHSPEC = "docs/decisions/decision-015*"


def _git(*args):
    """stdout of a git command in REPO, stripped; '' on any failure."""
    proc = subprocess.run(
        ["git", "-C", REPO] + list(args), capture_output=True, text=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _is_ancestor(a, b):
    """True when commit a is b or an ancestor of it."""
    return subprocess.run(
        ["git", "-C", REPO, "merge-base", "--is-ancestor", a, b],
        capture_output=True,
    ).returncode == 0


def _units():
    """(kind, name, repo-relative dir) for every unit that owes a README, sorted."""
    out = []
    for kind, root in UNIT_ROOTS:
        abs_root = os.path.join(REPO, root)
        if not os.path.isdir(abs_root):
            continue
        for name in sorted(os.listdir(abs_root)):
            if not name.startswith(".") and os.path.isdir(os.path.join(abs_root, name)):
                out.append((kind, name, f"{root}/{name}"))
    return out


def problems():
    if not _git("rev-parse", "--git-dir"):
        return [f"{REPO} is not a git repository — currency is derived from history"]
    if _git("rev-parse", "--is-shallow-repository") == "true":
        return [
            "shallow clone: every unit would pass vacuously — fetch full history "
            "(`git fetch --unshallow`, or `fetch-depth: 0` on the CI checkout)"
        ]
    anchor = _git("log", "--diff-filter=A", "-1", "--format=%H", "--", ANCHOR_PATHSPEC)
    out = []
    for kind, name, rel in _units():
        body = _git("log", "-1", "--format=%H", "--", rel, f":(exclude){rel}/README.md")
        if not body:
            continue  # no tracked body — check_readmes.py owns what a unit must contain
        if anchor and _is_ancestor(body, anchor):
            continue  # predates decision-015; not this gate's business
        readme = _git("log", "-1", "--format=%H", "--", f"{rel}/README.md")
        if readme and _is_ancestor(body, readme):
            continue
        out.append(
            f"{kind} '{name}': last change {_git('log', '-1', '--format=%h %s', body)} "
            f"left {rel}/README.md untouched — verify that README against the unit and "
            f"touch it in the same change"
        )
    return out


def main(argv):
    global REPO
    if len(argv) > 1:
        REPO = os.path.abspath(argv[1])
    found = problems()
    if found:
        print(f"✗ README-currency gate: {len(found)} stale unit(s)")
        for p in found:
            print(f"  - {p}")
        return 1
    print(f"✓ README-currency gate clean — {len(_units())} unit(s), each README acknowledged")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
