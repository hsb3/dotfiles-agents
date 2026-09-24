"""Tests for the delegation skill's `trace_check.py` -- report-only subagent leak detection.

A reviewer/scout must only read and report; any file it leaves behind in the checkout
(an empty scratch file, a stray symlink) is a leak nothing else catches. Every test
builds a throwaway git repo in a tempdir (never under `primitives-core/`) and drives
the CLI in process via `main()`.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "primitives-core", "skills", "delegation", "scripts")
sys.path.insert(0, SCRIPTS)

import trace_check  # noqa: E402


def write(path, data):
    with open(path, "w") as handle:
        handle.write(data)
    return path


def git(repo, *args):
    subprocess.run(["git", "-C", repo] + list(args), check=True, capture_output=True)


def init_repo(repo):
    """A committed README plus an ignored `ignored_dir/` holding one already-ignored file."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    write(os.path.join(repo, "README.md"), "hi\n")
    os.makedirs(os.path.join(repo, "ignored_dir"))
    write(os.path.join(repo, "ignored_dir", "existing.txt"), "already there\n")
    write(os.path.join(repo, ".gitignore"), "ignored_dir/\n")
    git(repo, "add", "README.md", ".gitignore")
    git(repo, "commit", "-q", "-m", "init")


def run(argv):
    """Drive the CLI in process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = trace_check.main(argv=argv, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


class Trace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        init_repo(self.repo)
        self.snap = os.path.join(self.tmp.name, "snap.json")

    def snapshot(self):
        code, out, err = run(["snapshot", self.repo, self.snap])
        self.assertEqual(0, code, err)
        return code, out, err

    def test_clean_tree_exits_zero(self):
        self.snapshot()
        code, out, err = run(["check", self.repo, self.snap])
        self.assertEqual(0, code, err)
        self.assertEqual("", out)

    def test_new_untracked_file_is_named(self):
        self.snapshot()
        write(os.path.join(self.repo, "afile"), "")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? afile\n", out)

    def test_new_symlink_is_named(self):
        self.snapshot()
        os.symlink("/etc", os.path.join(self.repo, "lnk"))
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? lnk\n", out)

    def test_new_file_inside_already_ignored_dir_is_named_individually(self):
        # Proves --ignored=traditional + -uall lists files inside an ignored dir
        # individually rather than collapsing to the directory.
        self.snapshot()
        write(os.path.join(self.repo, "ignored_dir", "new_leak.txt"), "leak\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("!! ignored_dir/new_leak.txt\n", out)

    def test_preexisting_untracked_file_at_snapshot_time_is_not_reported(self):
        write(os.path.join(self.repo, "pre.txt"), "already here\n")
        self.snapshot()
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(0, code, out)
        self.assertEqual("", out)

    def test_modified_tracked_file_is_named(self):
        self.snapshot()
        write(os.path.join(self.repo, "README.md"), "changed\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual(" M README.md\n", out)

    def test_snapshot_path_inside_repo_is_refused(self):
        inside = os.path.join(self.repo, "snap.json")
        code, _, err = run(["snapshot", self.repo, inside])
        self.assertEqual(2, code)
        self.assertIn(self.repo, err)
        self.assertFalse(os.path.exists(inside))

    def test_snapshot_with_subdir_as_repo_is_refused(self):
        # <repo> given as a subdirectory of the checkout must not defeat the
        # inside-the-tree refusal -- git resolves the real toplevel regardless.
        subdir = os.path.join(self.repo, "ignored_dir")
        inside = os.path.join(self.repo, "snap.json")
        code, _, err = run(["snapshot", subdir, inside])
        self.assertEqual(2, code)
        self.assertFalse(os.path.exists(inside))

    def test_snapshot_missing_parent_dir_exits_two(self):
        missing = os.path.join(self.tmp.name, "nope", "snap.json")
        code, _, err = run(["snapshot", self.repo, missing])
        self.assertEqual(2, code)
        self.assertNotEqual("", err)
        self.assertFalse(os.path.exists(missing))

    def test_not_a_repo_exits_two(self):
        not_a_repo = os.path.join(self.tmp.name, "plain")
        os.makedirs(not_a_repo)
        code, _, err = run(["snapshot", not_a_repo, self.snap])
        self.assertEqual(2, code)
        self.assertNotEqual("", err)

    def test_check_with_missing_snapshot_exits_two(self):
        code, _, err = run(["check", self.repo, os.path.join(self.tmp.name, "nope.json")])
        self.assertEqual(2, code)
        self.assertIn("nope.json", err)

    def test_path_with_space_round_trips(self):
        self.snapshot()
        write(os.path.join(self.repo, "a leak.txt"), "x\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? a leak.txt\n", out)

    def test_path_with_newline_round_trips(self):
        self.snapshot()
        name = "leak\nfile.txt"
        write(os.path.join(self.repo, name), "x\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? leak\nfile.txt\n", out)

    def test_snapshot_entries_are_written_sorted(self):
        # git already tends to hand back sorted entries, so lock the write path's own
        # sort in against a canned unsorted list -- this fails if `sorted()` is dropped.
        unsorted = [["??", "zeta.txt"], ["??", "alpha.txt"]]
        original = trace_check.git_entries
        trace_check.git_entries = lambda repo: (unsorted, None)
        try:
            code, _, _ = run(["snapshot", self.repo, self.snap])
        finally:
            trace_check.git_entries = original
        self.assertEqual(0, code)
        with open(self.snap) as handle:
            data = json.load(handle)
        self.assertEqual(sorted(unsorted), data["entries"])

    def test_deleted_untracked_file_is_reported_gone(self):
        write(os.path.join(self.repo, "pre.txt"), "already here\n")
        self.snapshot()
        os.remove(os.path.join(self.repo, "pre.txt"))
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("gone ?? pre.txt\n", out)

    def test_commit_changes_head_is_reported(self):
        self.snapshot()
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "empty")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertTrue(out.startswith("head "), out)
        self.assertIn(" -> ", out)

    def test_stash_push_changes_stash_is_reported(self):
        # Fixture repo only -- never touches the real checkout's stash stack.
        write(os.path.join(self.repo, "leak.txt"), "x\n")
        self.snapshot()
        write(os.path.join(self.repo, "stashme.txt"), "x\n")
        git(self.repo, "stash", "push", "-u", "-m", "trace-check-test")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertIn("stash ", out)
        self.assertIn(" -> ", out)

    def test_check_refuses_when_toplevel_differs(self):
        self.snapshot()
        other = os.path.join(self.tmp.name, "other")
        os.makedirs(other)
        init_repo(other)
        code, _, err = run(["check", other, self.snap])
        self.assertEqual(2, code)
        self.assertNotEqual("", err)

    def test_malformed_snapshot_missing_entries_key_exits_two(self):
        write(self.snap, json.dumps({"toplevel": self.repo, "head": None, "stash": None}))
        code, _, err = run(["check", self.repo, self.snap])
        self.assertEqual(2, code)
        self.assertNotEqual("", err)

    def test_malformed_snapshot_entries_not_a_list_exits_two(self):
        write(
            self.snap,
            json.dumps({"toplevel": self.repo, "head": None, "stash": None, "entries": "??"}),
        )
        code, _, err = run(["check", self.repo, self.snap])
        self.assertEqual(2, code)
        self.assertNotEqual("", err)

    def test_new_file_inside_untracked_dir_is_named_individually(self):
        self.snapshot()
        newdir = os.path.join(self.repo, "newdir")
        os.makedirs(newdir)
        write(os.path.join(newdir, "leak.txt"), "x\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? newdir/leak.txt\n", out)

    def test_trailing_space_round_trips(self):
        self.snapshot()
        write(os.path.join(self.repo, "trailing.txt "), "x\n")
        code, out, _ = run(["check", self.repo, self.snap])
        self.assertEqual(1, code)
        self.assertEqual("?? trailing.txt \n", out)


class ParseStatusZ(unittest.TestCase):
    def test_rename_record_consumes_origin_path_and_keeps_destination(self):
        raw = b"R  new.txt\x00old.txt\x00?? extra.txt\x00"
        got = trace_check.parse_status_z(raw)
        self.assertEqual([["R ", "new.txt"], ["??", "extra.txt"]], got)

    def test_worktree_rename_in_second_column_consumes_origin_path(self):
        # Index unchanged, worktree renamed: code[0] is a space, code[1] is 'R'.
        raw = b" R new.txt\x00old.txt\x00?? extra.txt\x00"
        got = trace_check.parse_status_z(raw)
        self.assertEqual([[" R", "new.txt"], ["??", "extra.txt"]], got)


if __name__ == "__main__":
    unittest.main()
