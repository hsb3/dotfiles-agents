"""Shared fixture: a real git repo plus a real linked worktree.

Every activation-reading hook resolves a linked worktree to its main checkout
when the file it wants is absent at the direct path, and that resolution runs
`git rev-parse --git-common-dir` against a real repository. Faking the layout
(hand-writing a `.git` file) would test our idea of what git writes rather than
what git writes, so this fixture shells out to the real binary and skips when
there is none.

One fixture, five hook test modules: `tracked` files are committed in the main
checkout (so the linked worktree gets its own copy at the committed version)
and `files` are left uncommitted (so they exist only in the main checkout —
the shape a gitignored `.claude/atelier.local.md` or handoff stamp has in
practice).
"""

import os
import shutil
import subprocess
import unittest

# Identity for the fixture's one commit: `git commit` refuses without a
# configured author, and the ambient user config must not leak into a test.
_GIT_IDENTITY = (
    "-c", "user.name=fixture",
    "-c", "user.email=fixture@example.invalid",
    "-c", "commit.gpgsign=false",
)


def require_git():
    """Skip the calling test when there is no `git` on PATH."""
    if shutil.which("git") is None:
        raise unittest.SkipTest("git is not on PATH")


def _git(cwd, *args):
    proc = subprocess.run(
        ["git"] + list(args), cwd=cwd,
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "git {0} failed in {1}: {2}".format(" ".join(args), cwd, proc.stderr.strip())
        )
    return proc.stdout.strip()


def _write(root, relpath, text):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def make_worktree(base_dir, files=None, tracked=None, branch="worker"):
    """Return (main_dir, worktree_dir) for a repo under `base_dir`.

    `tracked`: {relpath: text} written and committed in the main checkout, so
    the linked worktree checks out its own copy at the committed version.
    `files`: {relpath: text} written to the main checkout only and never
    committed, so the worktree has no copy at all.

    `base_dir` is realpath'd first: on macOS a tempdir is reached through a
    symlink, and git reports the resolved path, so an unresolved base would
    make every path comparison in a test spuriously unequal.
    """
    base_dir = os.path.realpath(base_dir)
    main_dir = os.path.join(base_dir, "main")
    worktree_dir = os.path.join(base_dir, "worktree")
    os.makedirs(main_dir, exist_ok=True)

    _git(main_dir, "init", "-q", ".")
    for relpath, text in (tracked or {}).items():
        _write(main_dir, relpath, text)
        _git(main_dir, "add", "--", relpath)
    _git(main_dir, *(_GIT_IDENTITY + ("commit", "-q", "--allow-empty", "-m", "fixture")))

    for relpath, text in (files or {}).items():
        _write(main_dir, relpath, text)

    _git(main_dir, "worktree", "add", "-q", worktree_dir, "-b", branch)
    return main_dir, worktree_dir
