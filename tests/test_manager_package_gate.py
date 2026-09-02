"""Tests for primitives-core/hooks/manager-package-gate/hook.py.

Runs the hook as a subprocess (its real invocation shape: SubagentStop JSON on
stdin, a JSON line on stdout only on a nudge, env-configured log path).
Stdlib-only; fixtures build into a tempdir per test, and the environment passed
to the subprocess is built from scratch with only PATH inherited so a run can
never reach this machine's real ledger root.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "manager-package-gate", "hook.py",
)

_SEQ = itertools.count()


def _agent_id():
    return "agent-mpg-{0}".format(next(_SEQ))


class ManagerPackageGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "manager-package-gate.jsonl")
        # Sandbox the partitioned log root as well as the override: a path
        # resolved from HOME would otherwise append synthetic rows to the
        # ledger this machine actually collects.
        self.xdg = os.path.join(self.tmp.name, "xdg")

    # -- fixtures ------------------------------------------------------

    def _payload(self, agent_type="manager", last_message="", stop_hook_active=False,
                 agent_id=None):
        return {
            "session_id": "session-mpg",
            "transcript_path": os.path.join(self.cwd, "parent.jsonl"),
            "cwd": self.cwd,
            "hook_event_name": "SubagentStop",
            "agent_id": agent_id or _agent_id(),
            "agent_type": agent_type,
            "agent_transcript_path": os.path.join(self.cwd, "agent.jsonl"),
            "last_assistant_message": last_message,
            "stop_hook_active": stop_hook_active,
        }

    def _run_hook(self, payload=None, stdin_text=None, set_log_env=True):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": self.xdg,
            "CLAUDE_PROJECT_DIR": self.cwd,
        }
        if set_log_env:
            env["MANAGER_PACKAGE_GATE_LOG_PATH"] = self.log_path
        if stdin_text is None:
            stdin_text = json.dumps(payload)
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    # -- assertions ----------------------------------------------------

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def _assert_nudged(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        emitted = json.loads(result.stdout)
        self.assertEqual(emitted["decision"], "block")
        return emitted["reason"]

    def _rows(self):
        if not os.path.isfile(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]

    # -- the manager path ----------------------------------------------

    def test_progress_note_is_nudged(self):
        """The #449 field failure: a manager ends its turn on a progress note."""
        result = self._run_hook(self._payload(
            last_message="Review triaged. Both builders are fixing; waiting on them.",
        ))
        reason = self._assert_nudged(result)
        self.assertIn("## Proof package", reason)
        self.assertIn("## Stopped:", reason)

    def test_proof_package_sentinel_passes(self):
        result = self._run_hook(self._payload(
            last_message="## Proof package\n\n1. Criterion one: `make ci` exits 0.",
        ))
        self._assert_silent(result)

    def test_stopped_sentinel_passes(self):
        result = self._run_hook(self._payload(
            last_message="## Stopped: gate failed twice\n\nThe lint gate fails on...",
        ))
        self._assert_silent(result)

    def test_leading_whitespace_before_sentinel_passes(self):
        result = self._run_hook(self._payload(
            last_message="\n\n  ## Proof package\n\nEvidence follows.",
        ))
        self._assert_silent(result)

    def test_plugin_qualified_manager_is_recognised(self):
        result = self._run_hook(self._payload(
            agent_type="atelier:manager",
            last_message="Still waiting on the second builder.",
        ))
        self._assert_nudged(result)

    def test_stop_hook_active_passes(self):
        """One nudge, never a loop: a re-entrant stop is let through."""
        result = self._run_hook(self._payload(
            last_message="Still waiting on the second builder.",
            stop_hook_active=True,
        ))
        self._assert_silent(result)

    # -- everything that is not a manager ------------------------------

    def test_non_manager_passes_silently(self):
        result = self._run_hook(self._payload(
            agent_type="builder",
            last_message="Done, tests green.",
        ))
        self._assert_silent(result)
        self.assertEqual(self._rows(), [])

    def test_manager_substring_is_not_a_manager(self):
        """`code-manager` is a different agent, not this hook's business."""
        result = self._run_hook(self._payload(
            agent_type="atelier:code-manager",
            last_message="Progress note.",
        ))
        self._assert_silent(result)
        self.assertEqual(self._rows(), [])

    # -- fail-open ------------------------------------------------------

    def test_malformed_stdin_exits_zero_silently(self):
        self._assert_silent(self._run_hook(stdin_text="{not json"))

    def test_empty_stdin_exits_zero_silently(self):
        self._assert_silent(self._run_hook(stdin_text=""))

    def test_non_object_stdin_exits_zero_silently(self):
        self._assert_silent(self._run_hook(stdin_text='["a", "list"]'))

    def test_missing_last_message_is_nudged_not_crashed(self):
        payload = self._payload()
        del payload["last_assistant_message"]
        self._assert_nudged(self._run_hook(payload))

    # -- ledger ---------------------------------------------------------

    def test_ledger_row_on_nudge(self):
        agent_id = _agent_id()
        self._run_hook(self._payload(
            agent_type="atelier:manager",
            last_message="Waiting on them.",
            agent_id=agent_id,
        ))
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["stream"], "manager-package-gate")
        self.assertEqual(row["decision"], "nudge")
        self.assertEqual(row["agent_id"], agent_id)
        self.assertEqual(row["agent_type"], "atelier:manager")

    def test_ledger_row_on_pass(self):
        self._run_hook(self._payload(last_message="## Proof package\n\nEvidence."))
        self.assertEqual([r["decision"] for r in self._rows()], ["pass"])

    def test_ledger_row_on_skip(self):
        self._run_hook(self._payload(
            last_message="Waiting on them.", stop_hook_active=True,
        ))
        self.assertEqual([r["decision"] for r in self._rows()], ["skip"])



class SentinelDoctrineTests(unittest.TestCase):
    """The sentinel the hook checks is prescribed in two doctrine files; a
    rename in either would silently disarm the gate, so the literals are read
    from the prose here rather than restated."""

    ROOT = os.path.join(os.path.dirname(__file__), "..", "primitives-core")
    DOCTRINE = (
        os.path.join("agents", "manager.md"),
        os.path.join("skills", "delegation", "references", "manager-brief.md"),
    )

    def test_doctrine_carries_every_sentinel_verbatim(self):
        with open(HOOK_PATH, encoding="utf-8") as fh:
            source = fh.read()
        start = source.index("SENTINELS = (")
        sentinels = eval(source[start + len("SENTINELS = "):source.index(")", start) + 1])
        self.assertEqual(len(sentinels), 2)
        for rel in self.DOCTRINE:
            with open(os.path.join(self.ROOT, rel), encoding="utf-8") as fh:
                prose = fh.read()
            for sentinel in sentinels:
                self.assertIn("`{0}".format(sentinel), prose, "{0} lacks {1!r}".format(rel, sentinel))


if __name__ == "__main__":
    unittest.main()
