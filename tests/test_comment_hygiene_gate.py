"""Tests for primitives-core/hooks/comment-hygiene-gate/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a JSON
line on stdout only when added comment lines carry history). Fixtures are real
git repos in a tempdir, because the hook's whole input is a git diff; the
environment passed to the subprocess is built from scratch with only PATH
inherited, so a stray CLAUDE_PROJECT_DIR cannot redirect it.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "comment-hygiene-gate", "hook.py",
)

DIRTY = """function pay(a) {
  // fixed in issue 94, see CI run 31458505007 (2026-08-10)
  // OTUI-114: owner directive said we retry twice here
  return a * 2 // this used to be a no-op
}
"""

CLEAN = """function pay(a) {
  // Per-account, not global: the request path re-enters under load.
  return a * 2
}
"""


class CommentHygieneGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        self._git("init", "-q", "-b", "main", ".")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "T")
        self._write("app.js", "function pay(a) {\n  return a\n}\n")
        self._git("add", "-A")
        self._git("commit", "-qm", "base")

    def _git(self, *args):
        subprocess.run(("git",) + args, cwd=self.repo, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _write(self, name, body):
        with open(os.path.join(self.repo, name), "w", encoding="utf-8") as fh:
            fh.write(body)

    def _run(self, command, cwd=None):
        payload = {
            "session_id": "s", "cwd": cwd if cwd is not None else self.repo,
            "tool_name": "Bash", "tool_input": {"command": command},
        }
        p = subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", "")},
        )
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        return p.stdout.decode().strip()

    def _stage(self, body):
        self._write("app.js", body)
        self._git("add", "-A")

    # -- fires ---------------------------------------------------------

    def test_flags_history_in_staged_diff_on_commit(self):
        self._stage(DIRTY)
        out = json.loads(self._run("git commit -m 'feat: retry'"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])
        self.assertIn("app.js", ctx)
        self.assertIn("comment-hygiene", ctx)
        self.assertIn("3 added comment line", ctx)

    def test_flags_branch_diff_on_pr_create(self):
        self._git("checkout", "-qb", "feature")
        self._stage("x = 1  // rollback plan lives in ABC-77, per the review call\n")
        self._git("commit", "-qm", "work")
        out = json.loads(self._run("gh pr create --fill"))
        self.assertIn("attribution", out["hookSpecificOutput"]["additionalContext"])

    # -- silent --------------------------------------------------------

    def test_silent_on_clean_staged_diff(self):
        self._stage(CLEAN)
        self.assertEqual(self._run("git commit -m 'feat: retry'"), "")

    def test_silent_on_non_landing_command(self):
        self._stage(DIRTY)
        self.assertEqual(self._run("rg -n retry src/"), "")

    def test_silent_outside_a_git_repo(self):
        outside = os.path.join(self.tmp.name, "plain")
        os.makedirs(outside)
        self.assertEqual(self._run("git commit -m x", cwd=outside), "")

    def test_silent_on_malformed_payload(self):
        p = subprocess.run([sys.executable, HOOK_PATH], input=b"not json",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={"PATH": os.environ.get("PATH", "")})
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout.decode().strip(), "")

    def test_silent_on_prose_files(self):
        """A tracker card is where history BELONGS — scanning it inverts the rule.

        The path deliberately contains spaces: git appends a tab to the diff's
        `+++ b/<path>` header for those, so a suffix check reads the extension
        only if the tab is stripped first.
        """
        self._write(
            "task-058 - a card.md",
            "## Shape — owner ruling 2026-08-09\n\nCloses #291, see TASK-032.\n",
        )
        self._git("add", "-A")
        self.assertEqual(self._run("git commit -m docs"), "")

    def test_flags_history_in_yaml_and_reports_a_clean_path(self):
        self._write("ci workflow.yml", "steps:\n  # Version-bump gate (TASK-032): pinned\n")
        self._git("add", "-A")
        ctx = json.loads(self._run("git commit -m ci"))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("board reference", ctx)
        self.assertIn("ci workflow.yml (1)", ctx)

    def test_silent_on_markers_inside_string_literals(self):
        """`#` in a quoted string is code, not a comment."""
        self._stage(
            'const msg = "fixed in #291 on 2026-08-10"\n'
            "const sql = '-- TASK-032 per the owner call'\n"
        )
        self.assertEqual(self._run("git commit -m x"), "")

    def test_silent_on_css_hex_colours_and_custom_properties(self):
        """`#` names a colour in CSS and `--x` is a custom property, not a comment."""
        self._write("theme.css", ":root {\n  --text: #141413;\n  color: #141413;\n}\n")
        self._git("add", "-A")
        self.assertEqual(self._run("git commit -m style"), "")

    def test_silent_on_url_scheme_slashes(self):
        """`//` in a URL is not a comment opener, and NOTICE/LICENSE are prose."""
        self._write("deps.properties", "docs=http://example.com/TASK-032/2026-08-10\n")
        self._write("NOTICE", "Licensed under http://www.apache.org/licenses/LICENSE-2.0\n")
        self._git("add", "-A")
        self.assertEqual(self._run("git commit -m deps"), "")

    def test_still_flags_a_real_comment_in_each_language_family(self):
        self._write("a.py", "x = 1  # rollback plan lives in ABC-77\n")
        self._write("b.go", "var x = 1  // owner directive: retry twice\n")
        self._write("c.sql", "select 1  -- superseded 2026-08-10\n")
        self._git("add", "-A")
        ctx = json.loads(self._run("git commit -m x"))["hookSpecificOutput"]["additionalContext"]
        for f in ("a.py", "b.go", "c.sql"):
            self.assertIn(f, ctx)

    def test_version_like_tokens_are_not_board_refs(self):
        self._stage("const enc = 'x'  // UTF-8 only, SHA-256 digest, see CVE-2024-1234\n")
        self.assertEqual(self._run("git commit -m x"), "")


if __name__ == "__main__":
    unittest.main()
