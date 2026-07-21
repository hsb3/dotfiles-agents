"""Grading — the pass rule (adapter-routed), check.py runner, workspace digest."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.adapters.base import NormalizedRecord  # noqa: E402
from agent_harness.adapters.claude import ClaudeAdapter  # noqa: E402
from agent_harness.grading import (  # noqa: E402
    run_check,
    trial_passed,
    workspace_digest,
)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# success() is exit-code-only for claude and needs no CLI, so a real adapter
# instance is the cleanest way to exercise the adapter-routed pass rule.
ADAPTER = ClaudeAdapter()


class TestPassRule(unittest.TestCase):
    def test_clean_run_all_grades_pass(self):
        rec = NormalizedRecord(plugin_errors=[])
        grades = [{"id": "a", "passed": True, "evidence": "x"}]
        self.assertTrue(trial_passed(ADAPTER, 0, rec, [], grades, "with"))

    def test_nonzero_exit_fails(self):
        self.assertFalse(trial_passed(ADAPTER, 1, NormalizedRecord(), [], [], "with"))

    def test_no_grades_passes_on_clean_exit(self):
        self.assertTrue(trial_passed(ADAPTER, 0, NormalizedRecord(), [], [], "with"))

    def test_plugin_errors_fail_with_config_only(self):
        rec = NormalizedRecord(plugin_errors=[{"message": "boom"}])
        self.assertFalse(trial_passed(ADAPTER, 0, rec, [], [], "with"))
        self.assertTrue(trial_passed(ADAPTER, 0, rec, [], [], "baseline"))

    def test_any_failed_grade_fails(self):
        rec = NormalizedRecord(plugin_errors=[])
        grades = [
            {"id": "a", "passed": True, "evidence": "x"},
            {"id": "b", "passed": False, "evidence": "unknown: y"},
        ]
        self.assertFalse(trial_passed(ADAPTER, 0, rec, [], grades, "with"))

    def test_checks_and_grades_combined(self):
        rec = NormalizedRecord(plugin_errors=[])
        checks = [{"id": "c1", "passed": True, "evidence": "ok"}]
        grades = [{"id": "g1", "passed": True, "evidence": "ok"}]
        self.assertTrue(trial_passed(ADAPTER, 0, rec, checks, grades, "with"))
        checks_bad = [{"id": "c1", "passed": False, "evidence": "no"}]
        self.assertFalse(trial_passed(ADAPTER, 0, rec, checks_bad, grades, "with"))


class TestRunCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_absent_check_returns_empty(self):
        self.assertEqual(run_check(self.tmp, self.tmp), [])

    def test_check_runs_in_workspace(self):
        case_dir = os.path.join(self.tmp, "case")
        ws = os.path.join(self.tmp, "ws")
        os.makedirs(ws)
        _write(os.path.join(ws, "target.txt"), "hi")
        _write(
            os.path.join(case_dir, "check.py"),
            "import json, os\n"
            "print(json.dumps([{'id':'c1','passed':os.path.isfile('target.txt'),"
            "'evidence':'in ws'}]))\n",
        )
        grades = run_check(case_dir, ws)
        self.assertEqual(grades, [{"id": "c1", "passed": True, "evidence": "in ws"}])

    def test_malformed_check_becomes_failed_grade(self):
        case_dir = os.path.join(self.tmp, "case")
        _write(os.path.join(case_dir, "check.py"), "print('not json')\n")
        grades = run_check(case_dir, self.tmp)
        self.assertEqual(len(grades), 1)
        self.assertFalse(grades[0]["passed"])
        self.assertEqual(grades[0]["id"], "check.py")


class TestWorkspaceDigest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_lists_files_with_sizes(self):
        _write(os.path.join(self.tmp, "a.txt"), "hello")
        _write(os.path.join(self.tmp, "sub", "b.py"), "x = 1\n")
        digest = workspace_digest(self.tmp)
        self.assertIn("a.txt (5B)", digest)
        self.assertIn(os.path.join("sub", "b.py"), digest)

    def test_empty_workspace(self):
        self.assertEqual(workspace_digest(self.tmp), "(empty)")

    def test_cap_truncates(self):
        for i in range(5):
            _write(os.path.join(self.tmp, f"f{i}.txt"), "x")
        digest = workspace_digest(self.tmp, cap=2)
        self.assertIn("... and 3 more", digest)


if __name__ == "__main__":
    unittest.main()
