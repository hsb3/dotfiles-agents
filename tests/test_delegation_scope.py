"""Tests for the delegation skill's `scope.py` — brief-scope measurement.

The helper answers one question before any work happens: how big is the owned-file
list this brief hands a worker. Every test builds its fixtures in a tempdir, never
under `primitives-core/`, and drives the CLI in process by handing `main()` its own
argv, stdin and streams, so nothing here depends on the host's cwd or the real repo.

The measurement contract these tests pin: a figure that could not be taken is never
silently folded into the totals. An entry that is a glob, a missing path, a directory
or an unreadable file lands in `unresolved`, the totals report only what was actually
read, and the CLI exits 1 so a dispatcher reads the figure as a floor rather than a
total.
"""

import io
import json
import os
import stat
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "primitives-core", "skills", "delegation", "scripts")
sys.path.insert(0, SCRIPTS)

import scope  # noqa: E402


def write(path, data):
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as handle:
        handle.write(data)
    return path


def run(argv, stdin=""):
    """Drive the CLI in process. Returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = scope.main(argv=argv, stdin=io.StringIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


class Measure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_counts_files_bytes_and_lines(self):
        a = write(self.path("a.md"), "one\ntwo\n")
        b = write(self.path("b.py"), "x = 1\n")
        got = scope.measure([a, b])
        self.assertEqual(2, got["files"])
        self.assertEqual(14, got["bytes"])
        self.assertEqual(3, got["lines"])
        self.assertEqual([], got["unresolved"])

    def test_final_line_without_newline_still_counts(self):
        a = write(self.path("a.md"), "one\ntwo")
        self.assertEqual(2, scope.measure([a])["lines"])

    def test_empty_list_is_a_zero_figure_not_an_error(self):
        self.assertEqual(
            {"files": 0, "bytes": 0, "lines": 0, "binary": 0, "unresolved": []},
            scope.measure([]),
        )

    def test_missing_path_is_unresolved_and_uncounted(self):
        got = scope.measure([self.path("nope.md")])
        self.assertEqual(0, got["files"])
        self.assertEqual(0, got["bytes"])
        self.assertEqual([{"path": self.path("nope.md"), "reason": "missing"}],
                         got["unresolved"])

    def test_directory_is_unresolved_and_never_walked(self):
        sub = self.path("sub")
        os.mkdir(sub)
        write(os.path.join(sub, "buried.md"), "hidden\n")
        got = scope.measure([sub])
        self.assertEqual(0, got["files"])
        self.assertEqual(0, got["bytes"])
        self.assertEqual([{"path": sub, "reason": "directory"}], got["unresolved"])

    def test_glob_is_reported_and_never_expanded(self):
        write(self.path("a.md"), "one\n")
        write(self.path("b.md"), "two\n")
        pattern = self.path("*.md")
        got = scope.measure([pattern])
        self.assertEqual(0, got["files"])
        self.assertEqual(0, got["bytes"])
        self.assertEqual([{"path": pattern, "reason": "glob"}], got["unresolved"])

    def test_a_real_file_whose_name_holds_a_magic_char_is_measured(self):
        real = write(self.path("a[1].md"), "one\n")
        got = scope.measure([real])
        self.assertEqual(1, got["files"])
        self.assertEqual([], got["unresolved"])

    def test_binary_counts_toward_files_and_bytes_but_not_lines(self):
        blob = write(self.path("logo.png"), b"\x89PNG\x00\x00\x00\x0d\n\n")
        text = write(self.path("a.md"), "one\n")
        got = scope.measure([blob, text])
        self.assertEqual(2, got["files"])
        self.assertEqual(1, got["binary"])
        self.assertEqual(14, got["bytes"])
        self.assertEqual(1, got["lines"])

    def test_duplicate_entries_are_counted_once(self):
        a = write(self.path("a.md"), "one\n")
        got = scope.measure([a, a])
        self.assertEqual(1, got["files"])
        self.assertEqual(4, got["bytes"])

    def test_symlink_is_measured_as_its_target(self):
        target = write(self.path("real.md"), "one\ntwo\n")
        link = self.path("link.md")
        os.symlink(target, link)
        got = scope.measure([link])
        self.assertEqual(1, got["files"])
        self.assertEqual(8, got["bytes"])
        self.assertEqual([], got["unresolved"])

    def test_broken_symlink_is_missing(self):
        link = self.path("link.md")
        os.symlink(self.path("gone.md"), link)
        self.assertEqual([{"path": link, "reason": "missing"}],
                         scope.measure([link])["unresolved"])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root reads everything")
    def test_unreadable_file_is_unresolved(self):
        a = write(self.path("a.md"), "one\n")
        os.chmod(a, 0)
        self.addCleanup(os.chmod, a, stat.S_IRUSR | stat.S_IWUSR)
        got = scope.measure([a])
        self.assertEqual(0, got["files"])
        self.assertEqual([{"path": a, "reason": "unreadable"}], got["unresolved"])

    def test_unresolved_order_follows_input_order(self):
        first, second = self.path("z-missing.md"), self.path("a-*.md")
        got = scope.measure([first, second])
        self.assertEqual([first, second], [u["path"] for u in got["unresolved"]])


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.a = write(os.path.join(self.dir, "a.md"), "one\ntwo\n")
        self.b = write(os.path.join(self.dir, "b.py"), "x = 1\n")

    def test_paths_on_argv_print_the_figure_and_exit_zero(self):
        code, out, err = run([self.a, self.b])
        self.assertEqual(0, code, err)
        self.assertEqual("", err)
        self.assertEqual(
            ["files 2", "bytes 14", "lines 3", "binary 0", "unresolved 0"],
            out.strip().splitlines(),
        )

    def test_json_output_carries_the_same_figure(self):
        code, out, _ = run(["--json", self.a, self.b])
        self.assertEqual(0, code)
        self.assertEqual(
            {"files": 2, "bytes": 14, "lines": 3, "binary": 0, "unresolved": []},
            json.loads(out),
        )

    def test_paths_on_stdin_when_argv_is_empty(self):
        code, out, _ = run(["--json"], stdin="%s\n\n%s\n" % (self.a, self.b))
        self.assertEqual(0, code)
        self.assertEqual(2, json.loads(out)["files"])

    def test_unresolved_entry_exits_one_and_is_named(self):
        missing = os.path.join(self.dir, "nope.md")
        code, out, _ = run([self.a, missing])
        self.assertEqual(1, code)
        self.assertIn("unresolved 1", out)
        self.assertIn("missing  %s" % missing, out)
        self.assertIn("files 1", out)

    def test_no_paths_at_all_is_a_usage_error(self):
        code, out, err = run([])
        self.assertEqual(2, code)
        self.assertEqual("", out)
        self.assertIn("no paths", err)

    def test_output_is_deterministic(self):
        first = run(["--json", self.a, self.b])
        second = run(["--json", self.b, self.a])
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
