"""Run core — timeout path, unsupported skip, workspace lifecycle, subprocess,
preconditions recording (task-22 gap 2), --keep-workspaces (task-22 gap 3).

The timeout and skip tests use stub adapters (no live CLI): a stub that invokes
`sleep` proves a hung child is killed and produces an error row, and a stub whose
injection is unsupported proves the explicit skip row (no subprocess runs).
"""

import glob
import json
import os
import signal
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness import preconditions as preconditions_mod  # noqa: E402
from agent_harness.adapters.base import Adapter, Injection, NormalizedRecord  # noqa: E402
from agent_harness.adapters.claude import ClaudeAdapter  # noqa: E402
from agent_harness.adapters.opencode import OpencodeAdapter  # noqa: E402
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
            campaign="",
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

    def test_timeout_kills_owned_descendant_and_keeps_partial_output(self):
        pid_path = os.path.join(self.tmp, "descendant.pid")
        survivor_path = os.path.join(self.tmp, "descendant-survived")
        child_pid = []

        def cleanup_child():
            if not child_pid:
                return
            try:
                os.kill(child_pid[0], signal.SIGKILL)
            except ProcessLookupError:
                pass

        self.addCleanup(cleanup_child)
        child_code = (
            f"import time; time.sleep(2); open({survivor_path!r}, 'w').close(); "
            "time.sleep(30)"
        )
        code = (
            "import subprocess, sys, time; "
            f"child = subprocess.Popen([sys.executable, '-c', {child_code!r}], "
            "stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL); "
            f"open({pid_path!r}, 'w').write(str(child.pid)); "
            "print('partial transcript', flush=True); time.sleep(30)"
        )
        t0 = time.monotonic()
        result = _run_subprocess(
            [sys.executable, "-c", code], self.tmp, dict(os.environ), 1,
            os.path.join(self.tmp, "timeout.log"),
        )
        elapsed = time.monotonic() - t0
        with open(pid_path, encoding="utf-8") as fh:
            child_pid.append(int(fh.read()))
        self.assertTrue(result.timed_out)
        self.assertIn("partial transcript", result.raw)
        self.assertLess(elapsed, 5, "timeout waited for a descendant")
        time.sleep(2)
        self.assertFalse(os.path.exists(survivor_path), "descendant survived timeout")


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
    def test_repeated_same_tick_trials_keep_distinct_transcripts(self):
        args = self._args(keep_workspaces=True)
        adapter = _CmdAdapter(["/bin/echo", "one"])
        with mock.patch("agent_harness.core.time.strftime", return_value="fixed"):
            first = run_trial(
                adapter, "cand", "skill", "/x", self._case(), "with", 0, args
            )
            adapter._argv[-1] = "two"
            second = run_trial(
                adapter, "cand", "skill", "/x", self._case(), "with", 0, args
            )
        self.assertNotEqual(first["log_path"], second["log_path"])
        with open(first["log_path"], encoding="utf-8") as fh:
            self.assertIn("one", fh.read())
        with open(second["log_path"], encoding="utf-8") as fh:
            self.assertIn("two", fh.read())

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
        # Campaign + log_path + token fields present (tokens None for a stub).
        self.assertEqual(row["campaign"], "")
        self.assertIsNotNone(row["log_path"])
        self.assertTrue(row["log_path"].endswith(".log"))
        for tf in ("input_tokens", "output_tokens", "cache_read_tokens",
                   "cache_creation_tokens"):
            self.assertIn(tf, row)
            self.assertIsNone(row[tf])

    def test_campaign_flows_into_row_and_skip_row(self):
        adapter = _CmdAdapter(["true"])
        row = run_trial(
            adapter, "cand", "skill", "/x", self._case(), "with", 0,
            self._args(campaign="skillfix"),
        )
        self.assertEqual(row["campaign"], "skillfix")
        # A skip row (unsupported inject) also carries the campaign + null log_path.
        skip = run_trial(
            _UnsupportedAdapter(), "cand", "weird", "/x", self._case(), "with", 0,
            self._args(campaign="skillfix"),
        )
        self.assertEqual(skip["campaign"], "skillfix")
        self.assertIsNone(skip["log_path"])


class TestKeepWorkspacesOnDisk(CoreTestBase):
    """--keep-workspaces (cli.py:79-83, core.py:219-221 pre-existing behavior):
    a passing trial's workspace survives on disk WITH the flag and is actually
    removed from disk WITHOUT it (not just a None/not-None row field check —
    strengthens test_core.py:166-190 with a real filesystem assertion)."""

    def _run_with_spy(self, keep_workspaces):
        import unittest.mock as mock

        captured = {}
        orig_mkdtemp = tempfile.mkdtemp

        def spy_mkdtemp(*a, **kw):
            path = orig_mkdtemp(*a, **kw)
            captured["tmp"] = path
            return path

        adapter = _CmdAdapter(["true"])
        case = self._case()
        with mock.patch("tempfile.mkdtemp", side_effect=spy_mkdtemp):
            row = run_trial(
                adapter, "cand", "skill", "/x", case, "with", 0,
                self._args(keep_workspaces=keep_workspaces),
            )
        return row, captured["tmp"]

    def test_workspace_survives_on_disk_with_keep_workspaces(self):
        row, tmp = self._run_with_spy(keep_workspaces=True)
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertTrue(row["passed"])
        self.assertIsNotNone(row["workspace"])
        self.assertTrue(os.path.isdir(tmp), "run tmpdir was removed despite --keep-workspaces")
        self.assertTrue(os.path.isdir(row["workspace"]))

    def test_workspace_removed_without_keep_workspaces(self):
        row, tmp = self._run_with_spy(keep_workspaces=False)
        self.assertTrue(row["passed"])
        self.assertIsNone(row["workspace"])
        self.assertFalse(os.path.exists(tmp), "run tmpdir survived without --keep-workspaces")


class TestPreconditionsRecording(CoreTestBase):
    """Runtime self-installs / environment preconditions reach the trial record
    (task-22 gap 2): the row's ``preconditions`` field and the per-trial log
    file's leading ``#`` comment line."""

    def test_row_carries_preconditions_with_self_install_detected(self):
        adapter = _CmdAdapter(["/bin/echo", "npx playwright install chromium"])
        case = self._case()
        row = run_trial(adapter, "cand", "skill", "/x", case, "with", 0, self._args())
        self.assertIn("preconditions", row)
        precond = row["preconditions"]
        self.assertEqual(precond["harness"], "stub-cmd")
        self.assertEqual(precond["model"], "default")
        self.assertIn("self_installs", precond)
        self.assertTrue(
            any("playwright install" in s for s in precond["self_installs"]),
            precond["self_installs"],
        )

    def test_skip_row_is_schema_complete_with_preconditions(self):
        skip = run_trial(
            _UnsupportedAdapter(), "cand", "weird", "/x", self._case(), "with", 0,
            self._args(),
        )
        from agent_harness.core import ROW_FIELDS

        self.assertEqual(set(skip), set(ROW_FIELDS))
        self.assertIn("preconditions", skip)
        self.assertIsNotNone(skip["preconditions"])
        self.assertEqual(skip["preconditions"]["self_installs"], [])
        self.assertEqual(skip["preconditions"]["harness"], "stub-unsup")

    def test_log_file_on_disk_starts_with_preconditions_header(self):
        adapter = _CmdAdapter(["/bin/echo", "npm install foo"])
        case = self._case()
        args = self._args(keep_workspaces=True)
        run_trial(adapter, "cand", "skill", "/x", case, "with", 0, args)
        logs = glob.glob(os.path.join(args.runs_dir, "*.log"))
        self.assertEqual(len(logs), 1)
        with open(logs[0], encoding="utf-8") as fh:
            first_line = fh.readline()
        self.assertTrue(first_line.startswith("# preconditions: "))
        payload = json.loads(first_line[len("# preconditions: "):])
        self.assertIn("self_installs", payload)
        self.assertTrue(any("npm install" in s for s in payload["self_installs"]))

    def test_row_fields_and_row_keys_stay_in_sync(self):
        from agent_harness.core import ROW_FIELDS

        adapter = _CmdAdapter(["true"])
        row = run_trial(adapter, "cand", "skill", "/x", self._case(), "with", 0, self._args())
        self.assertEqual(set(row), set(ROW_FIELDS))
        self.assertIn("preconditions", ROW_FIELDS)


class TestPreconditionsHeaderLogParseTolerance(unittest.TestCase):
    """A `# preconditions: {...json...}` header line ahead of the raw transcript
    must not break either adapter's `parse_log` (both skip non-JSON lines:
    claude.py:185-189, opencode.py:300-309) — assert real events still fold."""

    def test_claude_parse_log_tolerates_preconditions_header(self):
        precond = {"harness": "claude", "self_installs": ["npm install foo"]}
        header = preconditions_mod.render_header(precond)
        events = [
            json.dumps({
                "type": "system", "subtype": "init",
                "plugins": [{"name": "eval-x"}], "plugin_errors": [],
            }),
            json.dumps({
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {}}]},
            }),
            json.dumps({
                "type": "result", "result": "done", "total_cost_usd": 0.1,
                "duration_ms": 10, "num_turns": 1, "usage": {"input_tokens": 5},
            }),
        ]
        raw = header + "\n" + "\n".join(events)
        rec = ClaudeAdapter().parse_log(raw)
        self.assertEqual(rec.result, "done")
        self.assertTrue(rec.skill_used)
        self.assertEqual([p["name"] for p in rec.plugins], ["eval-x"])
        self.assertEqual(rec.input_tokens, 5)

    def test_opencode_parse_log_tolerates_preconditions_header(self):
        precond = {"harness": "opencode", "self_installs": []}
        header = preconditions_mod.render_header(precond)

        def _ev(etype, part, ts):
            return json.dumps(
                {"type": etype, "timestamp": ts, "sessionID": "s", "part": part}
            )

        events = [
            _ev("step_start", {"type": "step-start"}, 1000),
            _ev("tool_use", {"type": "tool", "tool": "write"}, 1200),
            _ev(
                "step_finish",
                {"type": "step-finish", "reason": "stop", "cost": 0.02},
                1500,
            ),
        ]
        raw = header + "\n" + "\n".join(events)
        rec = OpencodeAdapter().parse_log(raw)
        self.assertEqual(rec.tool_names, ["write"])
        self.assertAlmostEqual(rec.cost_usd, 0.02)
        self.assertEqual(rec.num_turns, 1)


if __name__ == "__main__":
    unittest.main()
