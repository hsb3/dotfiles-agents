"""Run core — timeout path, unsupported skip, workspace lifecycle, subprocess.

The timeout and skip tests use stub adapters (no live CLI): a stub that invokes
`sleep` proves a hung child is killed and produces an error row, and a stub whose
injection is unsupported proves the explicit skip row (no subprocess runs).
"""

import os
import shutil
import sys
import tempfile
import time
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.adapters.base import Adapter, Injection, NormalizedRecord  # noqa: E402
from agent_harness.core import _run_subprocess, run_trial  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class _StubAdapter(Adapter):
    """Base stub: honest exit codes, empty parse, configurable injection/argv."""

    name = "stub"

    def preflight(self):
        return "ok"

    def cli_version(self):
        return "stub-0"

    def inject(self, kind, candidate_dir, tmpdir):
        return Injection([], [], True)

    def invocation(self, prompt, workspace, model, injection):
        return (["true"], dict(os.environ))

    def parse_log(self, raw):
        return NormalizedRecord()

    def success(self, returncode, record):
        return returncode == 0


class _SleepAdapter(_StubAdapter):
    name = "stub-sleep"

    def __init__(self, seconds=30):
        self.seconds = seconds

    def invocation(self, prompt, workspace, model, injection):
        return (["sleep", str(self.seconds)], dict(os.environ))


class _UnsupportedAdapter(_StubAdapter):
    name = "stub-unsup"

    def inject(self, kind, candidate_dir, tmpdir):
        return Injection([], [], False)

    def invocation(self, prompt, workspace, model, injection):
        raise AssertionError("invocation must NOT run for an unsupported injection")


class _CmdAdapter(_StubAdapter):
    name = "stub-cmd"

    def __init__(self, argv):
        self._argv = argv

    def invocation(self, prompt, workspace, model, injection):
        return (list(self._argv), dict(os.environ))


class CoreTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _args(self, **over):
        ns = types.SimpleNamespace(
            model=None,
            trials=1,
            configs="with",
            case=None,
            timeout=1,
            allow_bash=False,
            keep_workspaces=False,
            grader_model="grader",
            cases_dir=self.tmp,
            results=os.path.join(self.tmp, "results.jsonl"),
            runs_dir=os.path.join(self.tmp, "runs"),
        )
        for k, v in over.items():
            setattr(ns, k, v)
        return ns

    def _case(self, prompt="do it", assertions=None, with_fixture=False):
        d = os.path.join(self.tmp, "casedir")
        os.makedirs(d, exist_ok=True)
        if with_fixture:
            _write(os.path.join(d, "fixture", "seed.txt"), "seeded")
        return {
            "id": "casedir",
            "dir": d,
            "prompt": prompt,
            "assertions": assertions or [],
        }


class TestTimeout(CoreTestBase):
    def test_hung_child_produces_error_row_within_timeout(self):
        adapter = _SleepAdapter(seconds=30)
        case = self._case(prompt="sleep please")
        args = self._args(timeout=1)
        t0 = time.time()
        row = run_trial(adapter, "cand", "skill", "/no/such/candidate", case, "with", 0, args)
        elapsed = time.time() - t0
        self.assertEqual(row["exit_code"], -1)
        self.assertIn("timeout", row["error"])
        self.assertFalse(row["passed"])
        self.assertLess(elapsed, 20, "child was not killed near the 1s timeout")

    def test_run_subprocess_timeout_flag_and_normal_exit(self):
        log = os.path.join(self.tmp, "t.log")
        pr = _run_subprocess(["sleep", "5"], self.tmp, dict(os.environ), 1, log)
        self.assertTrue(pr.timed_out)
        self.assertEqual(pr.returncode, -1)
        self.assertIn("timeout", pr.error)
        ok = _run_subprocess(["true"], self.tmp, dict(os.environ), 10, log)
        self.assertFalse(ok.timed_out)
        self.assertEqual(ok.returncode, 0)
        self.assertIsNone(ok.error)


class TestUnsupportedSkip(CoreTestBase):
    def test_unsupported_injection_yields_skip_row_without_running(self):
        adapter = _UnsupportedAdapter()
        case = self._case()
        row = run_trial(adapter, "cand", "weird-kind", "/x", case, "with", 0, self._args())
        self.assertIsNone(row["passed"])
        self.assertTrue(row["error"].startswith("unsupported"))
        self.assertIsNone(row["exit_code"])
        self.assertIsNone(row["workspace"])

    def test_baseline_config_is_always_supported(self):
        # baseline omits injection entirely, so an unsupported inject() is never
        # consulted — the run proceeds.
        adapter = _UnsupportedAdapter()
        case = self._case()
        # invocation would raise; override to a harmless command for baseline.
        adapter.invocation = lambda p, w, m, i: (["true"], dict(os.environ))
        row = run_trial(adapter, "cand", "weird-kind", "/x", case, "baseline", 0, self._args())
        self.assertIsNotNone(row["passed"])
        self.assertEqual(row["exit_code"], 0)


class TestWorkspaceLifecycle(CoreTestBase):
    def test_fixture_copied_and_kept_when_requested(self):
        adapter = _CmdAdapter(["true"])  # passes -> would clean up, but keep is on
        case = self._case(with_fixture=True)
        row = run_trial(
            adapter, "cand", "skill", "/x", case, "with", 0,
            self._args(keep_workspaces=True),
        )
        self.assertTrue(row["passed"])
        self.assertIsNotNone(row["workspace"])
        self.assertTrue(os.path.isfile(os.path.join(row["workspace"], "seed.txt")))

    def test_failed_trial_keeps_workspace(self):
        adapter = _CmdAdapter(["false"])  # nonzero exit -> fail -> keep
        case = self._case()
        row = run_trial(adapter, "cand", "skill", "/x", case, "with", 0, self._args())
        self.assertFalse(row["passed"])
        self.assertIsNotNone(row["workspace"])
        self.assertTrue(os.path.isdir(row["workspace"]))

    def test_passing_trial_cleans_workspace(self):
        adapter = _CmdAdapter(["true"])
        case = self._case()
        row = run_trial(adapter, "cand", "skill", "/x", case, "with", 0, self._args())
        self.assertTrue(row["passed"])
        self.assertIsNone(row["workspace"])

    def test_row_has_full_schema(self):
        from agent_harness.core import ROW_FIELDS

        adapter = _CmdAdapter(["true"])
        case = self._case()
        row = run_trial(adapter, "cand", "skill", "/x", case, "with", 0, self._args())
        self.assertEqual(set(row), set(ROW_FIELDS))
        self.assertEqual(row["harness"], "stub-cmd")
        self.assertEqual(row["model"], "default")


if __name__ == "__main__":
    unittest.main()
