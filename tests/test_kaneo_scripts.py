"""Unit tests for the kaneo skill's diagnostic scripts.

Pure-function coverage only — no network. The API-touching paths were exercised live
against a scratch project on the real instance (see DFA-245); what is worth pinning here
is the row grouping and the revert heuristic, because both encode a defect model that is
easy to get subtly wrong and impossible to notice when it is.
"""

import importlib.util
import os
import subprocess
import unittest

SCRIPTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "primitives-core", "skills", "kaneo", "scripts",
)


def _load(name):
    """Import by path — these ship as scripts inside a skill, not as an installed package."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LABELS = _load("kaneo_labels")
DRIFT = _load("kaneo_status_drift")


def _definition(name):
    return {"id": name + "-def", "name": name, "taskId": None}


def _attachment(name, task):
    return {"id": "{0}-{1}".format(name, task), "name": name, "taskId": task}


class LabelGrouping(unittest.TestCase):
    """A label name is a group of rows, not a row. Everything the helper refuses to do
    depends on telling the definition row apart from its attachments."""

    def test_definition_and_attachments_are_split_by_task_id(self):
        grouped = LABELS.group([_definition("bug"), _attachment("bug", "t1"),
                                _attachment("bug", "t2")])
        self.assertEqual(len(grouped["bug"]["definitions"]), 1)
        self.assertEqual(len(grouped["bug"]["attachments"]), 2)

    def test_attachments_with_no_definition_are_visible_as_such(self):
        """The live workspace carries two of these (`owner-gated`, `upstream`): labels on
        tasks that the palette no longer offers. The audit exists to surface them."""
        grouped = LABELS.group([_attachment("upstream", "t1")])
        self.assertEqual(grouped["upstream"]["definitions"], [])
        self.assertEqual(len(grouped["upstream"]["attachments"]), 1)

    def test_names_do_not_bleed_into_each_other(self):
        grouped = LABELS.group([_definition("bug"), _attachment("chore", "t1")])
        self.assertEqual(grouped["bug"]["attachments"], [])
        self.assertEqual(grouped["chore"]["definitions"], [])


def _change(new, old, user=None, at="2026-08-17T20:00:00.000Z"):
    return {"type": "status_changed", "userId": user, "createdAt": at,
            "eventData": {"newStatus": new, "oldStatus": old}}


class RevertDetection(unittest.TestCase):
    """The endpoint returns newest-first; `reverts` reverses it, so every fixture here is
    written newest-first too — getting that backwards silently finds nothing."""

    def test_unattributed_write_that_undoes_the_previous_one_is_drift(self):
        activity = [
            _change("in-review", "in-progress", user=None, at="2026-08-17T20:00:03.000Z"),
            _change("in-progress", "in-review", user="u1", at="2026-08-17T20:00:00.000Z"),
        ]
        hits = DRIFT.reverts(activity)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["reverted_to"], "in-review")
        self.assertEqual(hits[0]["gap_seconds"], 3)

    def test_a_person_moving_a_task_back_is_not_drift(self):
        """Same shape, but attributed — someone changed their mind, which is allowed."""
        activity = [
            _change("in-review", "in-progress", user="u1", at="2026-08-17T20:00:03.000Z"),
            _change("in-progress", "in-review", user="u1", at="2026-08-17T20:00:00.000Z"),
        ]
        self.assertEqual(DRIFT.reverts(activity), [])

    def test_healthy_github_pipeline_is_not_drift(self):
        """push -> in-progress, PR -> in-review, merge -> done. All unattributed, all
        forward. A detector that fires on this is noise and gets ignored."""
        activity = [
            _change("done", "in-review", at="2026-08-17T20:00:20.000Z"),
            _change("in-review", "in-progress", at="2026-08-17T20:00:10.000Z"),
            _change("in-progress", "to-do", at="2026-08-17T20:00:00.000Z"),
        ]
        self.assertEqual(DRIFT.reverts(activity), [])

    def test_a_revert_outside_the_window_is_left_alone(self):
        activity = [
            _change("in-review", "in-progress", user=None, at="2026-08-17T23:00:00.000Z"),
            _change("in-progress", "in-review", user="u1", at="2026-08-17T20:00:00.000Z"),
        ]
        self.assertEqual(DRIFT.reverts(activity, window_seconds=120), [])

    def test_non_status_activity_is_ignored(self):
        activity = [{"type": "comment", "userId": None, "createdAt": "2026-08-17T20:00:00.000Z"}]
        self.assertEqual(DRIFT.reverts(activity), [])

    def test_unparseable_timestamps_do_not_crash_or_silently_drop(self):
        """A gap that cannot be computed must not be treated as 'outside the window' —
        that would turn a parse failure into a clean bill of health."""
        activity = [
            _change("in-review", "in-progress", user=None, at="not-a-date"),
            _change("in-progress", "in-review", user="u1", at="also-not-a-date"),
        ]
        hits = DRIFT.reverts(activity)
        self.assertEqual(len(hits), 1)
        self.assertIsNone(hits[0]["gap_seconds"])


USAGE = "usage: MINT_KEY=<agent-api-key> mint-mcp-token.sh <base-url>"


class MintTokenUsage(unittest.TestCase):
    """Both refusals happen before the first curl, so nothing here touches an instance.

    The script's documented contract is `... > token.txt`: a usage error that reached
    stdout, or that exited 0, would leave a file holding an error message where a token
    should be and only fail much later, in whatever reads it.
    """

    def _run(self, args, env_extra=None):
        env = {k: v for k, v in os.environ.items() if k != "MINT_KEY"}
        env.update(env_extra or {})
        return subprocess.run(
            ["/bin/bash", os.path.join(SCRIPTS, "mint-mcp-token.sh"), *args],
            capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=30,
        )

    def test_no_base_url_is_refused(self):
        # A key is supplied so only the missing-URL guard can be what refuses.
        result = self._run([], {"MINT_KEY": "not-a-real-key"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn(USAGE, result.stderr)
        self.assertEqual("", result.stdout)

    def test_missing_mint_key_is_refused(self):
        result = self._run(["https://kaneo.example.invalid"])
        self.assertNotEqual(0, result.returncode)
        self.assertIn(USAGE, result.stderr)
        self.assertEqual("", result.stdout, "no network step ran")


if __name__ == "__main__":
    unittest.main()
