"""Tests for scripts/check_flow.py -- the flow.yaml <-> tree drift guard.

Focused on tracked_top_level(): git ls-files applies default path quoting to any
tracked path containing non-ASCII or otherwise "unusual" bytes (wraps the whole
path in double quotes, octal-escapes the offending bytes). Naive newline-split
parsing of that output corrupts the top-level path (e.g. a leading `"`), which
made check_flow.py falsely report homeless top-level paths. Regression coverage
builds a throwaway git repo in a tempdir, stages paths with such bytes, and
asserts tracked_top_level() returns the real, unquoted top-level name.
Stdlib-only.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import check_flow as F  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True,
                    capture_output=True, text=True)


def _init_repo():
    repo = tempfile.mkdtemp()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    return repo


def _stage(repo, relpath, content="x\n"):
    full = os.path.join(repo, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    _git(repo, "add", relpath)


class TrackedTopLevel(unittest.TestCase):
    def _tracked(self, repo):
        old_repo = F.REPO
        F.REPO = repo
        try:
            return F.tracked_top_level()
        finally:
            F.REPO = old_repo

    def test_plain_ascii_path_is_unaffected(self):
        repo = _init_repo()
        _stage(repo, "backlog/tasks/task-001.md")
        self.assertEqual(self._tracked(repo), {"backlog"})

    def test_em_dash_in_path_does_not_corrupt_top_level(self):
        # Mirrors the real fixture: an em dash (U+2014) inside a tracked filename
        # under backlog/tasks/. Git's default quoting would octal-escape the
        # em dash and wrap the whole relpath in double quotes on `git ls-files`
        # (no -z); a naive split("/", 1)[0] then yields `"backlog`, not `backlog`.
        repo = _init_repo()
        _stage(repo, "backlog/tasks/task-040 - a—b.md")
        self.assertEqual(self._tracked(repo), {"backlog"})

    def test_accented_character_in_path_does_not_corrupt_top_level(self):
        repo = _init_repo()
        _stage(repo, "docs/café.md")
        self.assertEqual(self._tracked(repo), {"docs"})

    def test_literal_double_quote_in_filename_does_not_corrupt_top_level(self):
        # Git always escapes a literal double-quote byte in a path (regardless of
        # core.quotePath), which also triggers the whole-path double-quote wrapping.
        repo = _init_repo()
        _stage(repo, 'workbench/weird"name.md')
        self.assertEqual(self._tracked(repo), {"workbench"})

    def test_multiple_top_level_dirs_all_recovered(self):
        repo = _init_repo()
        _stage(repo, "backlog/tasks/task-040 - a—b.md")
        _stage(repo, "scripts/check_flow.py", content="pass\n")
        _stage(repo, "flow.yaml", content="nodes:\n")
        self.assertEqual(self._tracked(repo), {"backlog", "scripts", "flow.yaml"})


if __name__ == "__main__":
    unittest.main()
