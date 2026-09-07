"""Tests for scripts/check_labels.py — the closed GitHub label vocabulary.

Offline by design: the gate reads the live label set through `gh`, `make ci` has neither
`gh` nor network, so every test here drives the pure comparison with an injected label
set. The live read is a CI step and `make labels`.

The fix command carried by each problem is asserted, not just the fact of a violation:
the whole value of this gate over "the labels look wrong" is that its output is
copy-pasteable, and a problem that names a label without naming the command that fixes it
is the failure mode this repo keeps hitting.

Stdlib-only; every fixture is a tempdir, never under primitives-core/.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_labels as L  # noqa: E402


def _live(extra=(), missing=()):
    """The exact vocabulary, plus `extra` labels, minus `missing` ones."""
    return sorted((set(L.VOCABULARY) | set(extra)) - set(missing))


class ExactSet(unittest.TestCase):
    def test_exact_vocabulary_is_clean(self):
        self.assertEqual(L.check(_live()), [])

    def test_order_does_not_matter(self):
        self.assertEqual(L.check(sorted(L.VOCABULARY, reverse=True)), [])

    def test_vocabulary_is_the_five_labels_the_owner_froze(self):
        """A silent edit to the constant is the one way this gate lies about what it enforces."""
        self.assertEqual(
            set(L.VOCABULARY),
            {"type:feat", "type:fix", "type:chore", "decision", "epic"},
        )


class Extra(unittest.TestCase):
    def test_one_extra_label_fails(self):
        problems = L.check(_live(extra=["wontfix"]))
        self.assertEqual(len(problems), 1)
        self.assertIn("wontfix", problems[0])

    def test_extra_label_carries_the_delete_command(self):
        problems = L.check(_live(extra=["wontfix"]))
        self.assertIn("gh label delete", problems[0])
        self.assertTrue(problems[0].endswith("gh label delete 'wontfix'"), problems[0])

    def test_extra_label_never_suggests_creating_it(self):
        problems = L.check(_live(extra=["wontfix"]))
        self.assertNotIn("gh label create", problems[0])


class Missing(unittest.TestCase):
    def test_one_missing_label_fails(self):
        problems = L.check(_live(missing=["epic"]))
        self.assertEqual(len(problems), 1)
        self.assertIn("epic", problems[0])

    def test_missing_label_carries_the_create_command(self):
        problems = L.check(_live(missing=["epic"]))
        self.assertIn("gh label create", problems[0])
        self.assertTrue(problems[0].endswith("gh label create 'epic'"), problems[0])

    def test_empty_live_set_reports_every_label_missing(self):
        problems = L.check([])
        self.assertEqual(len(problems), len(L.VOCABULARY))
        self.assertTrue(all("gh label create" in p for p in problems))


class BothAtOnce(unittest.TestCase):
    def test_extra_and_missing_both_reported(self):
        problems = L.check(_live(extra=["wontfix"], missing=["epic"]))
        self.assertEqual(len(problems), 2)
        self.assertTrue(any(p.endswith("gh label delete 'wontfix'") for p in problems))
        self.assertTrue(any(p.endswith("gh label create 'epic'") for p in problems))

    def test_problems_are_sorted_for_a_stable_diff(self):
        problems = L.check(_live(extra=["zzz", "aaa"], missing=["epic"]))
        self.assertEqual(problems, sorted(problems))


class InjectedJson(unittest.TestCase):
    def test_gh_shaped_json_round_trips_from_a_file(self):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "labels.json")
            with open(fp, "w", encoding="utf-8") as fh:
                json.dump([{"name": n} for n in sorted(L.VOCABULARY)], fh)
            self.assertEqual(sorted(L.read_labels(fp)), sorted(L.VOCABULARY))

    def test_injected_file_drives_the_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "labels.json")
            with open(fp, "w", encoding="utf-8") as fh:
                json.dump([{"name": n} for n in _live(extra=["wontfix"])], fh)
            self.assertTrue(
                any(p.endswith("gh label delete 'wontfix'") for p in L.check(L.read_labels(fp)))
            )

    def test_extra_keys_gh_emits_are_ignored(self):
        """`gh label list --json name` is asked for one field; tolerate a richer payload."""
        payload = json.dumps([{"name": "epic", "color": "ededed", "description": "x"}])
        self.assertEqual(L.parse_gh_labels(payload), ["epic"])

    def test_empty_list_parses_to_no_labels(self):
        self.assertEqual(L.parse_gh_labels("[]"), [])


class NetworkContract(unittest.TestCase):
    """The three ways the live read can fail resolve to two different exit codes.

    Stubbed at the module boundary, so no test here opens a socket or runs a subprocess.
    Getting this wrong is silent in the worst direction: a gate that exits 0 whenever it
    cannot run teaches every reader that green means it ran.
    """

    def _run(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = L.main([])
        return rc, buf.getvalue()

    def test_gh_missing_from_path_fails_the_gate(self):
        with mock.patch.object(L.shutil, "which", return_value=None):
            rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("gh is not on PATH", out)

    def test_unreachable_host_skips_with_a_notice(self):
        with mock.patch.object(L, "gh_labels", return_value=(None, "gh label list failed")), \
             mock.patch.object(L, "_github_reachable", return_value=False), \
             mock.patch.object(L.shutil, "which", return_value="/usr/bin/gh"):
            rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertIn("ℹ", out)
        self.assertIn("unreachable", out)

    def test_reachable_host_with_failing_gh_fails_the_gate(self):
        with mock.patch.object(L, "gh_labels", return_value=(None, "gh label list failed: 401")), \
             mock.patch.object(L, "_github_reachable", return_value=True), \
             mock.patch.object(L.shutil, "which", return_value="/usr/bin/gh"):
            rc, out = self._run()
        self.assertEqual(rc, 1)
        self.assertIn("401", out)


if __name__ == "__main__":
    unittest.main()
