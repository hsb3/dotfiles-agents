"""Tests for primitives-core/hooks/comment-hygiene-gate/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a JSON
line on stdout only when added comment lines carry history). Fixtures are real
git repos in a tempdir, because the hook's whole input is a git diff; the
environment passed to the subprocess is built from scratch with only PATH
inherited, so a stray CLAUDE_PROJECT_DIR cannot redirect it.
"""

import json
import os
import re
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


DIRTY_JS = "const x = 1  // rollback plan lives in ABC-77, per the review call\n"


REPORTED_FILE = re.compile(r"^  - (\S+) \(\d+\)$", re.M)


class PrDiffFixture(unittest.TestCase):
    """Hermetic git plus the hook's PR-path invocation. No tests of its own."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = os.path.join(self.tmp.name, "home")
        os.makedirs(home)
        gitconfig = os.path.join(home, "gitconfig")
        open(gitconfig, "w").close()
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": home,
            "GIT_CONFIG_GLOBAL": gitconfig,
            "GIT_CONFIG_SYSTEM": gitconfig,
            "GIT_AUTHOR_NAME": "fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            "GIT_TERMINAL_PROMPT": "0",
        }

    def _git(self, repo, *args):
        subprocess.run(
            ("git",) + args, cwd=repo, check=True, env=self.env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _out(self, repo, *args):
        p = subprocess.run(
            ("git",) + args, cwd=repo, check=True, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        return p.stdout.decode().strip()

    def _commit(self, repo, name, body, message):
        with open(os.path.join(repo, name), "w") as fh:
            fh.write(body)
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-qm", message)
        return self._out(repo, "rev-parse", "HEAD")

    def _reviewed(self):
        """Paths the hook reported on, sorted; [] when it reported nothing."""
        payload = {
            "session_id": "s", "cwd": self.repo, "tool_name": "Bash",
            "tool_input": {"command": "gh pr create --fill"},
        }
        p = subprocess.run(
            [sys.executable, HOOK_PATH], input=json.dumps(payload).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env,
        )
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        out = p.stdout.decode().strip()
        if not out:
            return []
        return sorted(REPORTED_FILE.findall(
            json.loads(out)["hookSpecificOutput"]["additionalContext"]
        ))


class MergeBaseRefResolutionTests(PrDiffFixture):
    """A shadowing local ref moves the diff BASE, so the hook reviews the wrong range.

    `git rev-parse` resolves `refs/tags/<name>` and `refs/heads/<name>` before
    `refs/remotes/<name>`, so a local branch or tag literally named `origin/main`
    outranks the tracking ref. Every poison here sits MID-branch: a shadowed base then
    still yields a non-empty diff, so the failure is a silently narrowed review range
    rather than a silent hook, and no later candidate can rescue it by accident.
    """

    WHOLE_BRANCH = ["dirty.js", "more.js"]

    def setUp(self):
        super().setUp()
        origin = os.path.join(self.tmp.name, "origin")
        os.makedirs(origin)
        self._git(origin, "init", "-q", "-b", "main", ".")
        self._commit(origin, "app.js", "const a = 1\n", "base")

        self.repo = os.path.join(self.tmp.name, "work")
        subprocess.run(
            ["git", "clone", "-q", origin, self.repo], check=True, env=self.env, timeout=60
        )
        # Neither commit is pushed, so refs/remotes/origin/main is the true base.
        self.mid = self._commit(self.repo, "dirty.js", DIRTY_JS, "work")
        self._commit(self.repo, "more.js", DIRTY_JS, "more")

    def test_clone_head_points_at_the_tracking_ref(self):
        """Guards the fixture: without it the poisoned cases prove nothing."""
        self.assertEqual(
            self._out(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD"),
            "refs/remotes/origin/main",
        )
        self.assertEqual(self._reviewed(), self.WHOLE_BRANCH)

    def test_local_branch_named_origin_main_does_not_shadow_the_base(self):
        self._git(self.repo, "branch", "origin/main", self.mid)
        self.assertEqual(self._reviewed(), self.WHOLE_BRANCH)

    def test_tag_named_origin_main_does_not_shadow_the_base(self):
        self._git(self.repo, "tag", "origin/main", self.mid)
        self.assertEqual(self._reviewed(), self.WHOLE_BRANCH)

    def test_symbolic_ref_pointing_at_a_local_branch_is_not_trusted(self):
        """`refs/remotes/origin/HEAD` is writable, and full-refname is not remote-tracking.

        Repointed at a local branch it hands the hook a base that resolves fine and is
        simply wrong, so the target is checked for being remote-tracking as well.
        """
        self._git(self.repo, "branch", "poison", self.mid)
        self._git(self.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/heads/poison")
        self.assertEqual(self._reviewed(), self.WHOLE_BRANCH)


class NoRemoteRefResolutionTests(PrDiffFixture):
    """No `origin` remote at all — the fallback candidates must still resolve exactly.

    A full refname is not self-verifying: `git rev-parse refs/remotes/origin/main` falls
    through to rule 4 and yields `refs/heads/refs/remotes/origin/main` when no tracking
    ref of that name exists. The poison sits MID-branch, so a shadowed base still produces
    a non-empty diff — a silently narrowed review range, not a silent hook.
    """

    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.tmp.name, "solo")
        os.makedirs(self.repo)
        self._git(self.repo, "init", "-q", "-b", "main", ".")
        self._commit(self.repo, "app.js", "const a = 1\n", "base")
        self._git(self.repo, "checkout", "-qb", "feature")
        self.mid = self._commit(self.repo, "one.js", DIRTY_JS, "one")
        self._commit(self.repo, "two.js", DIRTY_JS, "two")

    def test_fixture_reviews_the_whole_branch(self):
        self.assertEqual(self._out(self.repo, "remote"), "")
        self.assertEqual(self._reviewed(), ["one.js", "two.js"])

    def test_local_branch_spelled_as_a_full_refname_is_not_used_as_the_base(self):
        self._git(self.repo, "branch", "refs/remotes/origin/main", self.mid)
        self.assertEqual(self._reviewed(), ["one.js", "two.js"])

    def test_tag_named_main_does_not_shadow_the_local_fallback(self):
        """Why the fallback is spelled `refs/heads/main` rather than bare `main`."""
        self._git(self.repo, "tag", "main", self.mid)
        self.assertEqual(self._reviewed(), ["one.js", "two.js"])


if __name__ == "__main__":
    unittest.main()
