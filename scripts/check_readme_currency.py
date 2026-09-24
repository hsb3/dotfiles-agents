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

  * **A plugin's body is its own tracked files** — `plugin.json`, `hooks.json`, and the
    symlink ENTRIES (retargeting or adding a link is a change to `plugins/<id>/`). Links
    are NOT followed into `primitives-core/`: under decision-030 an assembly is a membership
    statement, which is what its README documents, and a member skill's body change is
    already answerable on that skill's own unit. Following them would make every bundle
    stale whenever any member moved.
  * **Committed history only.** The working tree and the index are not read: "touched in
    the same change" has no meaning before there is a change. Uncommitted work is
    invisible here and lands red on the next run — CI runs on the PR's checkout, which is
    the authoritative one.

One exemption, for a plugin only: a **version bump inherited from the shared `hooks/_lib`**.
Editing `_lib` moves the dereferenced bytes of every plugin that links it, so the version-bump
guard makes each one bump — and each bump is a manifest commit that would otherwise demand a
README edit with nothing true to say. The unit passes when every body commit since its README
was last touched changed only `"version"` lines in the unit's `plugin.json` manifests, AND every
path the unit reaches through its links that changed between that README commit and HEAD lies
under its `hooks/_lib` link (and at least one did). HEAD, not the bump: nothing forces a second
bump for a member change that lands after the first, so a hook edit committed or merged in after
it counts — and in CI, HEAD is the PR merge ref, so a member change already on the base branch
counts too; the failure names that path. A member hook's change, any other manifest edit, or a
bump with nothing behind it still trips the gate. A removed `version` is not a bump here (the
version-bump guard rejects it too). Link targets are read from the checkout, not per commit.

The README side DOES follow a link (a standalone plugin points at its member skill's
README): history for the link entry or for its in-repo target counts, since the file a
reader opens is the target, and editing the entry alone could never clear the unit.

Needs real history: a shallow clone is a hard failure, not a skip, because every unit
would trivially pass in one (`actions/checkout` is depth-1 unless told otherwise).

Stdlib-only, deterministic (git topology, no clocks, sorted output). Exit 0 = clean;
exit 1 = violations (prints every one).
Usage: python3 scripts/check_readme_currency.py [repo-root]   (run from anywhere)
"""

import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT_ROOTS = (("skill", "primitives-core/skills"), ("plugin", "plugins"))
LIB_LINK = "hooks/_lib"


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


def _readme_pathspecs(rel):
    """The unit's README, plus its in-repo target when that README is a symlink."""
    link = f"{rel}/README.md"
    # realpath both sides: on macOS /tmp is itself a symlink, and a half-resolved
    # comparison reads every fixture's link as pointing outside the repo.
    target = os.path.relpath(
        os.path.realpath(os.path.join(REPO, link)), os.path.realpath(REPO)
    )
    return [link] if target == link or target.startswith("..") else [link, target]


def _version_only(commit, rel):
    """True when a single-parent commit changed the unit (README aside) only in the
    top-level `version` of its `plugin.json` manifests. Parsed, not diffed by line:
    another key sharing the version's line is a real manifest change."""
    if len(_git("rev-list", "--parents", "-n1", commit).split()) != 2:
        return False
    files = _git("diff", "--name-only", commit + "^", commit,
                 "--", rel, f":(exclude){rel}/README.md").splitlines()
    if not files or not all(os.path.basename(p) == "plugin.json" for p in files):
        return False
    for path in files:
        try:
            old, new = (json.loads(_git("show", f"{c}:{path}")) for c in (commit + "^", commit))
        except ValueError:
            return False
        if not (isinstance(old, dict) and isinstance(new, dict)):
            return False
        if not isinstance(new.get("version"), str) or not new["version"]:
            return False
        if old.pop("version", None) == new.pop("version", None) or old != new:
            return False
    return True


def _linked_changes(rel, base, head):
    """(paths the unit reaches through its links that changed base..head, the
    target of its hooks/_lib link or None)."""
    root, unit = os.path.realpath(REPO), os.path.join(REPO, rel)
    targets, lib = [], None
    for dirpath, dirnames, filenames in os.walk(unit):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            if not os.path.islink(path):
                continue
            target = os.path.relpath(os.path.realpath(path), root)
            if target.startswith(".."):
                continue
            targets.append(target)
            if os.path.relpath(path, unit) == LIB_LINK:
                lib = target
    changed = [p for p in _git("diff", "--name-only", base, head).splitlines()
               if any(p == t or p.startswith(t + "/") for t in targets)]
    return changed, lib


def _not_lib(changed, lib):
    return [p for p in changed if not (lib and p.startswith(lib + "/"))]


def _inherited_bump(rel, readme, body):
    """The one exemption (module docstring): every body commit since the README
    was touched is a version-only bump, carried by a hooks/_lib-only change. The
    linked range runs to HEAD, not to the bump: a member change committed or
    merged in after the bump forces no second bump, so it has to count here."""
    commits = _git("log", "--format=%H", f"{readme}..{body}",
                   "--", rel, f":(exclude){rel}/README.md").split()
    if not commits or not all(_version_only(c, rel) for c in commits):
        return False
    changed, lib = _linked_changes(rel, readme, "HEAD")
    return lib is not None and bool(changed) and not _not_lib(changed, lib)


def audit():
    """(problems, evaluated, skipped) — skipped = a unit with no tracked body."""
    if not _git("rev-parse", "--git-dir"):
        return [f"{REPO} is not a git repository — currency is derived from history"], 0, 0
    if _git("rev-parse", "--is-shallow-repository") == "true":
        return [
            "shallow clone: every unit would pass vacuously — fetch full history "
            "(`git fetch --unshallow`, or `fetch-depth: 0` on the CI checkout)"
        ], 0, 0
    out, evaluated, skipped = [], 0, 0
    for kind, name, rel in _units():
        body = _git("log", "-1", "--format=%H", "--", rel, f":(exclude){rel}/README.md")
        if not body:  # no tracked body — check_readmes.py owns what a unit must contain
            skipped += 1
            continue
        evaluated += 1
        readme = _git("log", "-1", "--format=%H", "--", *_readme_pathspecs(rel))
        if readme and _is_ancestor(body, readme):
            continue
        if readme and kind == "plugin" and _inherited_bump(rel, readme, body):
            continue
        # Why, when the change is not the one the author made: on a merge ref a
        # member change from the base branch ships under this unit's bump too.
        shipped = _not_lib(*_linked_changes(rel, readme, "HEAD")) if readme and kind == "plugin" else []
        out.append(
            f"{kind} '{name}': last change {_git('log', '-1', '--format=%h %s', body)} "
            f"left {rel}/README.md untouched — verify that README against the unit and "
            f"touch it in the same change"
            + (f" (it also ships {shipped[0]}, changed since the README)" if shipped else "")
        )
    return out, evaluated, skipped


def problems():
    return audit()[0]


def main(argv):
    global REPO
    if len(argv) > 1:
        REPO = os.path.abspath(argv[1])
    found, evaluated, skipped = audit()
    if found:
        print(f"✗ README-currency gate: {len(found)} problem(s)")
        for p in found:
            print(f"  - {p}")
        return 1
    print(
        f"✓ README-currency gate clean — {evaluated} unit(s) evaluated, {skipped} not "
        "(no tracked body)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
