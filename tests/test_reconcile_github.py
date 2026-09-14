"""Reconciliation decisions and CLI selection, with no live subprocesses."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "primitives-core/skills/board-triage/scripts/reconcile_github.py"
spec = importlib.util.spec_from_file_location("reconcile_github", SCRIPT)
reconcile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconcile)


class Reconcile(unittest.TestCase):
    def invoke(self, args, cards, opened, closed=()):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[:2] == ["kata", "list"]:
                data = {"issues": cards}
            elif cmd[:3] == ["gh", "issue", "list"]:
                numbers = opened if cmd[cmd.index("--state") + 1] == "open" else closed
                data = [{"number": n, "title": f"Issue {n}"} for n in numbers]
            elif cmd[:3] == ["gh", "issue", "close"]:
                data = {}
            else:
                self.fail(f"Unexpected command: {cmd}")
            return mock.Mock(returncode=0, stdout=json.dumps(data), stderr="")

        output = io.StringIO()
        with mock.patch.object(reconcile.subprocess, "run", side_effect=run), \
                mock.patch.object(sys, "argv", [str(SCRIPT), *args]), \
                contextlib.redirect_stdout(output):
            code = reconcile.main()
        return code, output.getvalue(), calls

    def test_project_and_classification_with_explicit_apply_only(self):
        cards = [
            {"short_id": "live", "status": "open", "title": "Live", "metadata": {"github_issue": 1}},
            {"short_id": "done", "status": "closed", "title": "Done", "metadata": {"github_issue": "https://github.com/example/demo/issues/2"}},
            {"short_id": "back", "status": "open", "title": "Back", "metadata": {"github_issue": 4}},
            {"short_id": "native", "status": "open", "title": "Native", "metadata": None},
        ]
        for apply in (False, True):
            with self.subTest(apply=apply):
                args = ["--project", "demo"] + (["--apply"] if apply else [])
                code, output, calls = self.invoke(args, cards, [3, 2, 1], [4])
                self.assertEqual(code, 0 if apply else 1)
                self.assertIn("tracked: 1   stale mirrors: 1   untracked: 1", output)
                self.assertIn("back -> #4", output)
                self.assertEqual(calls[0], ["kata", "list", "--status", "all", "--limit", "0", "--project", "demo", "--json"])
                writes = [cmd for cmd in calls if cmd[:3] == ["gh", "issue", "close"]]
                self.assertEqual(len(writes), int(apply))
                if apply:
                    self.assertEqual(writes[0][3:5], ["2", "--comment"])
                    self.assertIn("`done`", writes[0][5])
                else:
                    self.assertIn("dry run", output)

    def test_omitted_project_uses_kata_checkout_selection_and_empty_board(self):
        code, _, calls = self.invoke([], None, [])
        self.assertEqual(code, 0)
        self.assertNotIn("--project", calls[0])
        self.assertEqual(len(calls), 3)

    def test_unknown_option_rejected_before_any_commands(self):
        with mock.patch.object(reconcile.subprocess, "run") as run, \
                mock.patch.object(sys, "argv", [str(SCRIPT), "--aply"]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            reconcile.main()
        self.assertEqual(exc.exception.code, 2)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
