"""Tests for primitives-core/hooks/config-custody/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on deny, env-configured knobs) against a
hand-written .claude/atelier.local.md activation file. Stdlib-only; fixtures
build into a tempdir per test, and the environment passed to the subprocess
is built from scratch with only PATH inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

# Sibling helper: `tests/` is on sys.path under `discover -s tests` but not
# under `-t .`, so prime the path the same way the hooks prime `_lib`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import make_worktree, require_git  # noqa: E402

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "config-custody", "hook.py",
)

_SEQ = itertools.count()


def _session_id():
    return f"custody-session-{next(_SEQ)}"


def _last_log_row(log_path):
    with open(log_path, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    return json.loads(lines[-1])


class ConfigCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "config-custody.jsonl")
        # Sandbox the partitioned log root for every subprocess in this class.
        # Without it a run that sets no path override resolves the real
        # ~/.local/share/agent-logs and appends synthetic rows to the ledger
        # this machine actually collects.
        self.xdg = os.path.join(self.tmp.name, "xdg")
        self.default_log_path = os.path.join(
            self.xdg, "agent-logs", "claude-code", "atelier", "config-custody.jsonl",
        )

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, mode=None, patterns=None, raw_text=None, project_dir=None):
        project_dir = project_dir or self.cwd
        claude_dir = os.path.join(project_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if mode is not None:
                lines.append("enforce: {0}".format(mode))
            if patterns:
                lines.append("protected:")
                lines.extend("  - {0}".format(p) for p in patterns)
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _payload(self, file_path=None, notebook_path=None, agent_id="agent-1",
                 cwd=None, tool_name="Edit", session_id=None):
        tool_input = {}
        if file_path is not None:
            tool_input["file_path"] = file_path
        if notebook_path is not None:
            tool_input["notebook_path"] = notebook_path
        payload = {
            "session_id": session_id or _session_id(),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": self.cwd if cwd is None else cwd,
        }
        if agent_id is not None:
            payload["agent_id"] = agent_id
            payload["agent_type"] = "builder"
        return payload

    def _run_hook(self, payload, set_log_env=True, log_path=None, stdin_text=None):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": self.xdg,
        }
        if set_log_env:
            env["ATELIER_CUSTODY_LOG_PATH"] = log_path if log_path is not None else self.log_path
        stdin_text = json.dumps(payload) if stdin_text is None else stdin_text
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _assert_denied(self, result):
        self.assertEqual(result.returncode, 0)
        hso = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        return hso

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    # -- tests -----------------------------------------------------------

    def test_strict_subagent_protected_path_denies(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        hso = self._assert_denied(self._run_hook(self._payload(file_path="Makefile")))
        self.assertIn("protected pattern 'Makefile'", hso["permissionDecisionReason"])

    def test_strict_main_session_never_restricted(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        payload = self._payload(file_path="Makefile", agent_id=None)
        self._assert_silent(self._run_hook(payload))

    def test_advisory_logs_without_denying(self):
        self._write_activation(mode="advisory", patterns=["Makefile"])
        log_path = os.path.join(self.tmp.name, "logs", "advisory.jsonl")
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile"), log_path=log_path))
        row = _last_log_row(log_path)
        self.assertFalse(row["denied"])
        self.assertEqual(row["mode"], "advisory")

    def test_off_and_absent_activation_are_both_silent(self):
        # (a) explicit enforce: off
        self._write_activation(mode="off", patterns=["Makefile"])
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile")))

        # (b) activation file absent entirely (fresh project dir)
        bare_cwd = os.path.join(self.tmp.name, "bare")
        os.makedirs(bare_cwd, exist_ok=True)
        payload = self._payload(file_path="Makefile", cwd=bare_cwd)
        self._assert_silent(self._run_hook(payload))

    def test_garbage_activation_file_fails_open(self):
        self._write_activation(raw_text="not even yaml, just noise\n")
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile")))

    def test_glob_star_crosses_separators(self):
        self._write_activation(mode="strict", patterns=["configs/*"])
        payload = self._payload(file_path="configs/deep/nested/app.yaml")
        self._assert_denied(self._run_hook(payload))

    def test_absolute_path_vs_relative_pattern_and_outside_project(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        abs_path = os.path.join(self.cwd, "Makefile")
        self._assert_denied(self._run_hook(self._payload(file_path=abs_path)))
        self._assert_silent(self._run_hook(self._payload(file_path="/etc/hosts")))

    def test_notebook_edit_notebook_path_protected(self):
        self._write_activation(mode="strict", patterns=["notebooks/*"])
        payload = self._payload(
            notebook_path="notebooks/analysis.ipynb", tool_name="NotebookEdit",
        )
        self._assert_denied(self._run_hook(payload))

    def test_malformed_stdin_fails_open(self):
        result = self._run_hook(None, set_log_env=False, stdin_text="not json")
        self._assert_silent(result)

    def test_no_stray_writes_outside_configured_log_path(self):
        """With no path override the ledger goes to the partitioned root, and
        the project tree keeps exactly the file the test put there."""
        activation_path = self._write_activation(mode="strict", patterns=["Makefile"])
        result = self._run_hook(self._payload(file_path="Makefile"), set_log_env=False)
        self._assert_denied(result)

        found = set()
        for root, _dirs, files in os.walk(self.cwd):
            for name in files:
                found.add(os.path.relpath(os.path.join(root, name), self.cwd))
        self.assertEqual(found, {os.path.relpath(activation_path, self.cwd)})
        self.assertTrue(
            os.path.isfile(self.default_log_path),
            "row did not land in the partitioned root",
        )

    def test_default_row_carries_the_identity_envelope(self):
        """Envelope is asserted on a real written row, not on a literal."""
        self._write_activation(mode="strict", patterns=["Makefile"])
        self._assert_denied(
            self._run_hook(self._payload(file_path="Makefile"), set_log_env=False)
        )
        row = _last_log_row(self.default_log_path)
        self.assertEqual(row["stream"], "config-custody")
        self.assertEqual(row["plugin"], "atelier")
        self.assertEqual(row["harness"], "claude-code")
        self.assertEqual(row["v"], 1)
        self.assertEqual(row["project"], self.cwd)
        self.assertRegex(row["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        # payload survives alongside the envelope
        self.assertEqual(row["path"], "Makefile")
        self.assertTrue(row["denied"])


    # -- worktree resolution ---------------------------------------------

    def test_linked_worktree_follows_main_checkout_activation(self):
        """A subagent working in a linked worktree is still bound by the
        custody file that lives, gitignored, in the main checkout."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base,
            files={".claude/atelier.local.md": "---\nenforce: strict\nprotected:\n  - Makefile\n---\n"},
        )
        self.assertFalse(
            os.path.exists(os.path.join(worktree_dir, ".claude", "atelier.local.md")),
            "fixture leaked the activation file into the worktree",
        )

        payload = self._payload(file_path="Makefile", cwd=worktree_dir)
        hso = self._assert_denied(self._run_hook(payload))
        self.assertIn("protected pattern 'Makefile'", hso["permissionDecisionReason"])

        # Control: resolution imports the patterns, not a blanket denial.
        self._assert_silent(
            self._run_hook(self._payload(file_path="notes.md", cwd=worktree_dir))
        )
        # Control: the main checkout itself is unaffected.
        self._assert_denied(
            self._run_hook(self._payload(file_path="Makefile", cwd=main_dir))
        )

    def test_worktrees_own_tracked_activation_wins(self):
        """Resolution is lazy: a tracked activation file is read at the
        version committed on the worktree's branch, not at the main
        checkout's working-tree version."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base,
            tracked={".claude/atelier.local.md": "---\nenforce: off\nprotected:\n  - Makefile\n---\n"},
        )
        # Main checkout arms custody after the commit the worktree branched from.
        self._write_activation(mode="strict", patterns=["Makefile"], project_dir=main_dir)

        self._assert_denied(self._run_hook(self._payload(file_path="Makefile", cwd=main_dir)))
        self._assert_silent(
            self._run_hook(self._payload(file_path="Makefile", cwd=worktree_dir))
        )

    def test_non_worktree_cwd_without_git_is_unchanged(self):
        """A plain directory that is not a repo resolves to itself: absent
        activation file stays absent, no deny, no crash."""
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain, exist_ok=True)
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile", cwd=plain)))


if __name__ == "__main__":
    unittest.main()
