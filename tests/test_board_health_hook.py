"""Tests for .claude/hooks/board-health/hook.py.

Two layers, because two different things need proving.

In-process: `verdict()` is the pure decision, taking its subprocess runner and its
`which` probe as parameters, so every failure mode is reachable without a live board
— including an unexpected exception in the middle, which no fixture on disk can
produce.

Subprocess: the hook's real invocation shape (hook JSON on stdin, a SessionStart
JSON envelope on stdout) against stub adapter/checker scripts in a tempdir, because
exit 0 on every path is an acceptance criterion and only a real process has an exit
code.

The invariant this file exists for (card be1q): a run that could not measure must
never read as a clean board. `test_no_failure_case_reads_as_clean` drives that over
every failure scenario from one table rather than restating it per test, so the only
way a new failure path escapes the invariant is by not being added to the table.

Fixtures are tempdirs under tests/; nothing is written under primitives-core/ or
.claude/.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".claude", "hooks", "board-health", "hook.py",
)

SNAPSHOT = json.dumps({
    "board": {"name": "fixture", "backend": "kata"},
    "fields": {"labels": {"options": ["area:docs"]}},
    "items": [{"key": "aaaa", "title": "t", "state": "open", "labels": ["area:docs"],
               "fields": {"priority": "P1"}}],
})

CHECKER_CLEAN_STDOUT = "board health — fixture (kata) · 1 open item(s)\n\nclean — no decay found"
CHECKER_FINDINGS_STDOUT = (
    "board health — fixture (kata) · 9 open item(s)\n\n"
    "FAIL priority-missing: 3 open item(s) carry no priority\n\n"
    "1 finding(s) — run a triage pass"
)

MISSING_FILE_CASES = (
    ("adapter missing", "adapter"),
    ("checker missing", "script"),
    ("vocabulary missing", "vocabulary"),
)


def load_hook():
    spec = importlib.util.spec_from_file_location("board_health_hook", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRun:
    """Stand-in for the hook's subprocess runner: replays queued outcomes in order.

    An outcome that is an exception instance is raised rather than returned, which is
    how the timeout and unexpected-exception cases are driven.
    """

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, argv, timeout, stdin=""):
        self.calls.append((argv, timeout, stdin))
        if not self.outcomes:
            raise AssertionError(f"unexpected extra subprocess call: {argv}")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class BoardHealthHookBase(unittest.TestCase):
    def setUp(self):
        self.hook = load_hook()
        self.tmp = tempfile.TemporaryDirectory(dir=os.path.dirname(__file__))
        self.addCleanup(self.tmp.cleanup)
        self.adapter = os.path.join(self.tmp.name, "kata_board.py")
        self.script = os.path.join(self.tmp.name, "board_health.py")
        self.vocabulary = os.path.join(self.tmp.name, "core-labels.txt")
        self._write(self.adapter, "")
        self._write(self.script, "")
        self._write(self.vocabulary, "area:docs\ntype:feat\n")

    def _write(self, path, text):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _env(self, **extra):
        env = {
            "PATH": os.environ.get("PATH", ""),
            "BOARD_HEALTH_PROJECT": "fixture",
            "BOARD_HEALTH_KATA_BIN": sys.executable,
            "BOARD_HEALTH_ADAPTER": self.adapter,
            "BOARD_HEALTH_SCRIPT": self.script,
            "BOARD_HEALTH_VOCABULARY": self.vocabulary,
        }
        env.update(extra)
        return env

    def _config(self, **extra):
        return self.hook.config(self._env(**extra))

    def _proc(self, returncode, stdout="", stderr=""):
        return self.hook.Proc(returncode, stdout, stderr)


class VerdictTests(BoardHealthHookBase):
    def test_clean_board_reads_clean(self):
        run = FakeRun(self._proc(0, SNAPSHOT), self._proc(0, CHECKER_CLEAN_STDOUT))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.CLEAN_MARKER, line)
        self.assertNotIn(self.hook.UNMEASURED_MARKER, line)

    def test_findings_read_as_findings_and_carry_the_report(self):
        run = FakeRun(self._proc(0, SNAPSHOT), self._proc(1, CHECKER_FINDINGS_STDOUT))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.FINDINGS_MARKER, line)
        self.assertIn("priority-missing", line)
        self.assertNotIn(self.hook.CLEAN_MARKER, line)

    def test_the_snapshot_is_piped_to_the_checker_with_the_vocabulary(self):
        run = FakeRun(self._proc(0, SNAPSHOT), self._proc(0, CHECKER_CLEAN_STDOUT))
        self.hook.verdict(self._config(), run=run)
        export_argv, _, _ = run.calls[0]
        checker_argv, _, checker_stdin = run.calls[1]
        self.assertIn("export", export_argv)
        self.assertIn("fixture", export_argv)
        self.assertIn("--vocabulary", checker_argv)
        self.assertIn(self.vocabulary, checker_argv)
        self.assertEqual(checker_stdin, SNAPSHOT)

    def test_the_export_gets_the_configured_timeout(self):
        run = FakeRun(self._proc(0, SNAPSHOT), self._proc(0, CHECKER_CLEAN_STDOUT))
        self.hook.verdict(self._config(BOARD_HEALTH_TIMEOUT="7"), run=run)
        self.assertEqual(run.calls[0][1], 7.0)


class CouldNotMeasureTests(BoardHealthHookBase):
    """Every failure names WHICH failure it hit: a missing binary and a dead daemon are
    a ten-second and a thirty-minute debug, so one line must not read like the other."""

    def test_missing_kata_binary_names_the_binary(self):
        line = self.hook.verdict(self._config(), run=FakeRun(), which=lambda name: None)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("kata", line)
        self.assertIn("PATH", line)

    def test_export_failure_names_the_daemon(self):
        run = FakeRun(self._proc(1, "", "dial tcp: connection refused"))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("daemon", line)
        self.assertIn("connection refused", line)

    def test_export_timeout_names_the_daemon_and_the_timeout(self):
        run = FakeRun(subprocess.TimeoutExpired(cmd="kata_board.py", timeout=20))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("daemon", line)
        self.assertIn("timed out", line)

    def test_export_that_is_not_a_snapshot_says_so(self):
        run = FakeRun(self._proc(0, "Welcome to kata\n"))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("snapshot", line)

    def test_missing_vocabulary_names_the_declaration(self):
        os.remove(self.vocabulary)
        line = self.hook.verdict(self._config(), run=FakeRun())
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("core-labels.txt", line)
        self.assertIn("BOARD_HEALTH_VOCABULARY", line)

    def test_missing_checker_names_board_health_py(self):
        os.remove(self.script)
        line = self.hook.verdict(self._config(), run=FakeRun())
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("board_health.py", line)

    def test_missing_adapter_names_the_adapter(self):
        os.remove(self.adapter)
        line = self.hook.verdict(self._config(), run=FakeRun())
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("adapter", line)

    def test_checker_exit_two_is_could_not_measure_not_findings(self):
        run = FakeRun(self._proc(0, SNAPSHOT),
                      self._proc(2, "", "snapshot is not a board snapshot"))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertNotIn(self.hook.FINDINGS_MARKER, line)

    def test_unexpected_exception_is_caught_and_named_by_class(self):
        run = FakeRun(self._proc(0, SNAPSHOT), RuntimeError("kaboom"))
        line = self.hook.verdict(self._config(), run=run)
        self.assertIn(self.hook.UNMEASURED_MARKER, line)
        self.assertIn("RuntimeError", line)


class AntiFalseCleanTests(BoardHealthHookBase):
    """The invariant the adversarial reviewer targets, driven from one table."""

    def _failure_scenarios(self):
        return [
            ("kata binary absent",
             dict(run=FakeRun(), which=lambda name: None)),
            ("export exits non-zero",
             dict(run=FakeRun(self._proc(1, "", "connection refused")))),
            ("export times out",
             dict(run=FakeRun(subprocess.TimeoutExpired(cmd="x", timeout=20)))),
            ("export is not JSON",
             dict(run=FakeRun(self._proc(0, "not json")))),
            ("export is JSON but not a board snapshot",
             dict(run=FakeRun(self._proc(0, '{"ok": true}')))),
            ("checker exits 2",
             dict(run=FakeRun(self._proc(0, SNAPSHOT), self._proc(2, "", "bad input")))),
            ("checker exits an unknown code",
             dict(run=FakeRun(self._proc(0, SNAPSHOT), self._proc(9, "", "???")))),
            ("checker times out",
             dict(run=FakeRun(self._proc(0, SNAPSHOT),
                              subprocess.TimeoutExpired(cmd="x", timeout=20)))),
            ("unexpected exception",
             dict(run=FakeRun(ValueError("boom")))),
        ]

    def _failure_lines(self):
        """(case name, verdict line) for every way this hook can fail to measure."""
        for name, kwargs in self._failure_scenarios():
            yield name, self.hook.verdict(self._config(), **kwargs)
        for name, attr in MISSING_FILE_CASES:
            self.setUp()
            os.remove(getattr(self, attr))
            yield name, self.hook.verdict(self._config(), run=FakeRun())

    def test_every_failure_case_says_could_not_measure(self):
        for name, line in self._failure_lines():
            with self.subTest(case=name):
                self.assertIn(self.hook.UNMEASURED_MARKER, line)

    def test_no_failure_case_reads_as_clean(self):
        for name, line in self._failure_lines():
            with self.subTest(case=name):
                self.assertNotIn(self.hook.CLEAN_MARKER, line)
                self.assertNotIn(self.hook.FINDINGS_MARKER, line)

    def test_no_failure_case_is_silent(self):
        for name, line in self._failure_lines():
            with self.subTest(case=name):
                self.assertTrue(line.strip(), "a failure produced no verdict line at all")


class ConfigTests(BoardHealthHookBase):
    def test_defaults_land_under_the_repo_root(self):
        cfg = self.hook.config({"CLAUDE_PROJECT_DIR": "/tmp/fake-root"})
        self.assertEqual(cfg.project, "dotfiles-agents")
        self.assertEqual(cfg.kata_bin, "kata")
        self.assertTrue(cfg.script.startswith("/tmp/fake-root"))
        self.assertTrue(cfg.script.endswith("board_health.py"))
        self.assertTrue(cfg.vocabulary.endswith("core-labels.txt"))
        self.assertTrue(cfg.adapter.endswith("kata_board.py"))

    def test_blank_and_unparseable_values_fall_back_to_the_defaults(self):
        cfg = self.hook.config({"CLAUDE_PROJECT_DIR": "/tmp/fake-root",
                                "BOARD_HEALTH_PROJECT": "   ",
                                "BOARD_HEALTH_TIMEOUT": "soon"})
        self.assertEqual(cfg.project, "dotfiles-agents")
        self.assertGreater(cfg.timeout, 0)


class EndToEndTests(BoardHealthHookBase):
    """The real invocation: hook JSON on stdin, SessionStart envelope out, exit 0."""

    ADAPTER_OK = "import sys; sys.stdout.write(%r)" % SNAPSHOT
    ADAPTER_FAIL = "import sys; sys.stderr.write('connection refused'); sys.exit(1)"
    CHECKER_CLEAN = "import sys; sys.stdin.read(); print(%r); sys.exit(0)" % CHECKER_CLEAN_STDOUT
    CHECKER_FINDINGS = (
        "import sys; sys.stdin.read(); print(%r); sys.exit(1)" % CHECKER_FINDINGS_STDOUT)
    CHECKER_UNREADABLE = (
        "import sys; sys.stdin.read(); sys.stderr.write('bad snapshot'); sys.exit(2)")

    def _run_hook(self, **env):
        payload = json.dumps({"session_id": "t", "hook_event_name": "SessionStart",
                              "source": "startup", "cwd": self.tmp.name})
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input=payload, text=True, capture_output=True,
            env=self._env(**env), cwd=self.tmp.name, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        block = json.loads(proc.stdout)["hookSpecificOutput"]
        self.assertEqual(block["hookEventName"], "SessionStart")
        return block["additionalContext"]

    def test_clean_board_end_to_end(self):
        self._write(self.adapter, self.ADAPTER_OK)
        self._write(self.script, self.CHECKER_CLEAN)
        self.assertIn(self.hook.CLEAN_MARKER, self._run_hook())

    def test_findings_exit_zero_end_to_end(self):
        self._write(self.adapter, self.ADAPTER_OK)
        self._write(self.script, self.CHECKER_FINDINGS)
        context = self._run_hook()
        self.assertIn(self.hook.FINDINGS_MARKER, context)
        self.assertIn("priority-missing", context)

    def test_missing_kata_binary_end_to_end(self):
        context = self._run_hook(BOARD_HEALTH_KATA_BIN="definitely-not-a-real-binary")
        self.assertIn(self.hook.UNMEASURED_MARKER, context)
        self.assertNotIn(self.hook.CLEAN_MARKER, context)

    def test_dead_daemon_end_to_end(self):
        self._write(self.adapter, self.ADAPTER_FAIL)
        context = self._run_hook()
        self.assertIn(self.hook.UNMEASURED_MARKER, context)
        self.assertIn("daemon", context)

    def test_missing_vocabulary_end_to_end(self):
        os.remove(self.vocabulary)
        context = self._run_hook()
        self.assertIn(self.hook.UNMEASURED_MARKER, context)
        self.assertIn("core-labels.txt", context)

    def test_checker_exit_two_end_to_end(self):
        self._write(self.adapter, self.ADAPTER_OK)
        self._write(self.script, self.CHECKER_UNREADABLE)
        context = self._run_hook()
        self.assertIn(self.hook.UNMEASURED_MARKER, context)
        self.assertNotIn(self.hook.CLEAN_MARKER, context)

    def test_a_garbage_payload_still_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input="not json", text=True, capture_output=True,
            env=self._env(BOARD_HEALTH_KATA_BIN="definitely-not-a-real-binary"),
            cwd=self.tmp.name, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(self.hook.UNMEASURED_MARKER, proc.stdout)


if __name__ == "__main__":
    unittest.main()
