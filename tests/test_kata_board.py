"""board-triage's Kata adapter: the transformations, not the network.

Sibling of test_github_projects_board.py, and covered on the same principle —
everything between `kata list --json` and the argv of a mutation is this adapter's own
judgment and can be wrong on its own, so it is tested; the `kata` calls themselves are
only checked at the boundary (the argv built and the exit-code contract), because a
mock of Kata's responses would assert nothing but that the author's guess about them is
self-consistent.

What breaks silently if this drifts: a band that maps to the wrong integer re-prioritises
a whole board, a cell that no longer compares equal turns every re-run into fresh writes,
and a `status` row that stops being refused writes a lane that does not exist here.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "board-triage")

sys.path.insert(0, os.path.join(SKILL, "scripts"))

import kata_board as kb  # noqa: E402

# Shaped like `kata list --json`: one triaged issue, one untouched by triage.
ISSUES = [
    {
        "short_id": "b2",
        "title": "already urgent",
        "priority": 1,
        "owner": "someone",
        "labels": ["infra", "api"],
        "metadata": {"deadline_on": "2026-09-01"},
    },
    {
        "short_id": "a1",
        "title": "untriaged thing",
        "labels": [],
        "metadata": {},
    },
]
LABELS = [{"label": "infra"}, {"label": "docs"}, {"label": "api"}]


def snapshot():
    return kb.build_snapshot("demo", ISSUES, LABELS)


class Snapshot(unittest.TestCase):
    def test_shape_matches_the_contract(self):
        snap = snapshot()
        self.assertEqual("kata", snap["board"]["backend"])
        self.assertEqual("demo", snap["board"]["name"])
        self.assertEqual(["a1", "b2"], [i["key"] for i in snap["items"]], "items sort by key")
        self.assertEqual(["P0", "P1", "P2", "P3"], snap["fields"]["priority"]["options"])
        self.assertEqual(["api", "docs", "infra"], snap["fields"]["labels"]["options"])
        json.dumps(snap)  # the snapshot has to survive a round-trip to the analyst

    def test_native_priority_reads_back_as_a_rubric_band(self):
        item = next(i for i in snapshot()["items"] if i["key"] == "b2")
        self.assertEqual("P1", item["fields"]["priority"])
        self.assertEqual("2026-09-01", item["fields"]["due"])
        self.assertEqual("someone", item["fields"]["assignee"])
        self.assertEqual(["api", "infra"], item["labels"], "labels are sorted")

    def test_untriaged_cells_read_as_null_not_a_band(self):
        item = next(i for i in snapshot()["items"] if i["key"] == "a1")
        self.assertEqual({"priority": None, "due": None, "assignee": None}, item["fields"])

    def test_status_is_absent_not_null(self):
        """An unmapped output must not look like an unset-but-settable cell."""
        self.assertNotIn("status", snapshot()["items"][0]["fields"])

    def test_exported_items_are_open(self):
        self.assertEqual({"open"}, {i["state"] for i in snapshot()["items"]})

    def test_missing_labels_key_does_not_crash(self):
        snap = kb.build_snapshot("demo", [{"short_id": "z9", "labels": None}], [])
        self.assertEqual([], snap["items"][0]["labels"])


class Normalize(unittest.TestCase):
    def test_bands_resolve_to_kata_integers(self):
        self.assertEqual((0, None), kb.normalize("priority", "P0"))
        self.assertEqual((3, None), kb.normalize("priority", "p3"))

    def test_blank_priority_is_a_clear_not_an_error(self):
        self.assertEqual((None, None), kb.normalize("priority", "  "))

    def test_priority_off_the_rubric_is_refused(self):
        value, problem = kb.normalize("priority", "P9")
        self.assertIsNone(value)
        self.assertIn("P9", problem)

    def test_labels_split_strip_and_sort(self):
        self.assertEqual((["api", "infra"], None), kb.normalize("labels", " infra , api ,"))

    def test_status_has_no_cell_on_this_backend(self):
        value, problem = kb.normalize("status", "in-progress")
        self.assertIsNone(value)
        self.assertIn("no cell on Kata", problem)

    def test_plain_fields_pass_through_with_blank_as_none(self):
        self.assertEqual(("2026-09-01", None), kb.normalize("due", " 2026-09-01 "))
        self.assertEqual((None, None), kb.normalize("due", ""))


class Changeset(unittest.TestCase):
    def test_parses_tsv_and_skips_header_and_comments(self):
        rows = kb.parse_changeset("key\tfield\tvalue\n# note\n\na1\tpriority\tP1\n")
        self.assertEqual([("a1", "priority", "P1")], rows)

    def test_field_is_lowercased_and_a_tabbed_value_survives(self):
        self.assertEqual(
            [("a1", "title", "one\ttwo")], kb.parse_changeset("a1\tTitle\tone\ttwo")
        )

    def test_a_row_without_a_field_is_fatal_not_guessed(self):
        with self.assertRaises(SystemExit) as caught:
            kb.parse_changeset("a1\n")
        self.assertIn("line 1", str(caught.exception))


class Plan(unittest.TestCase):
    def test_writes_only_differing_cells(self):
        ops, problems = kb.plan(snapshot(), [("a1", "priority", "P1"), ("b2", "priority", "P1")])
        self.assertEqual([], problems)
        self.assertEqual(
            [["edit", "a1", "--priority", "1"]],
            [argv for argv, _ in ops],
            "b2 is already P1 — a no-op row must not produce a write",
        )

    def test_replanning_an_applied_changeset_is_empty(self):
        rows = [("b2", "priority", "P1"), ("b2", "due", "2026-09-01"),
                ("b2", "assignee", "someone"), ("b2", "labels", "api,infra")]
        self.assertEqual(([], []), kb.plan(snapshot(), rows), "apply must be idempotent")

    def test_blank_values_clear_the_cell(self):
        rows = [("b2", "priority", ""), ("b2", "due", ""), ("b2", "assignee", "")]
        ops, problems = kb.plan(snapshot(), rows)
        self.assertEqual([], problems)
        self.assertEqual(
            [["edit", "b2", "--priority", "-"], ["deadline", "b2", "-"], ["unassign", "b2"]],
            [argv for argv, _ in ops],
        )

    def test_labels_diff_into_add_and_remove(self):
        ops, problems = kb.plan(snapshot(), [("b2", "labels", "docs,infra")])
        self.assertEqual([], problems)
        self.assertEqual(
            [["label", "add", "b2", "docs"], ["label", "rm", "b2", "api"]],
            [argv for argv, _ in ops],
        )

    def test_setting_a_due_date_and_an_assignee(self):
        ops, _ = kb.plan(snapshot(), [("a1", "due", "2026-10-01"), ("a1", "assignee", "you")])
        self.assertEqual(
            [["deadline", "a1", "2026-10-01"], ["assign", "a1", "you"]],
            [argv for argv, _ in ops],
        )

    def test_unknown_item_and_unknown_field_are_reported_not_guessed(self):
        ops, problems = kb.plan(snapshot(), [("zz", "priority", "P1"), ("a1", "impact", "High")])
        self.assertEqual([], ops)
        self.assertEqual(2, len(problems))
        self.assertIn("not on this board", problems[0])
        self.assertIn("no Kata cell", problems[1])

    def test_a_status_row_is_refused_rather_than_written_somewhere_else(self):
        ops, problems = kb.plan(snapshot(), [("a1", "status", "in-progress")])
        self.assertEqual([], ops)
        self.assertIn("no cell on Kata", problems[0])


class KataCalls(unittest.TestCase):
    """The subprocess boundary: the argv built, and exit code as the contract."""

    def completed(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_reads_are_json_and_project_scoped(self):
        with mock.patch.object(kb.subprocess, "run") as run:
            run.return_value = self.completed(stdout='{"issues": []}')
            self.assertEqual({"issues": []}, kb._kata(["list"], "demo"))
        self.assertEqual(["kata", "list", "--project", "demo", "--json"], run.call_args[0][0])

    def test_empty_read_output_is_an_empty_result_not_a_crash(self):
        with mock.patch.object(kb.subprocess, "run") as run:
            run.return_value = self.completed(stdout="  ")
            self.assertEqual({}, kb._kata(["labels"], "demo"))

    def test_a_failed_read_stops_the_run_and_surfaces_stderr(self):
        with mock.patch.object(kb.subprocess, "run") as run:
            run.return_value = self.completed(returncode=2, stderr="no such project")
            with self.assertRaises(SystemExit) as caught:
                kb._kata(["list"], "demo")
        self.assertIn("no such project", str(caught.exception))

    def test_writes_use_agent_output_and_fail_loudly(self):
        with mock.patch.object(kb.subprocess, "run") as run:
            run.return_value = self.completed()
            kb._kata_write(["label", "add", "a1", "docs"], "demo")
        self.assertEqual(
            ["kata", "label", "add", "a1", "docs", "--project", "demo", "--agent"],
            run.call_args[0][0],
        )
        with mock.patch.object(kb.subprocess, "run") as run:
            run.return_value = self.completed(returncode=1, stderr="rejected")
            with self.assertRaises(SystemExit):
                kb._kata_write(["label", "add", "a1", "docs"], "demo")


class ApplyExitContract(unittest.TestCase):
    """cmd_apply end to end: a SKIP is a failure, on stderr, and the rest still applies.

    Pinned per adapter rather than once, because each adapter owns its own reporting and
    the three drifted apart unnoticed: an operator scripting `apply || abort` has to get
    the same answer from all of them, and has to be able to tee stdout without the
    refusals vanishing into it.
    """

    def run_apply(self, changeset):
        writes = []

        def run(cmd, capture_output=False, text=False, **_):
            if "list" in cmd:
                return mock.Mock(returncode=0, stdout=json.dumps({"issues": ISSUES}), stderr="")
            if "labels" in cmd:
                return mock.Mock(returncode=0, stdout=json.dumps({"labels": LABELS}), stderr="")
            writes.append(list(cmd))
            return mock.Mock(returncode=0, stdout="", stderr="")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "changeset.tsv")
        with open(path, "w") as handle:
            handle.write(changeset)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(kb.subprocess, "run", run), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = kb.main(["apply", "--project", "demo", "--changeset", path, "--apply"])
        return code, out.getvalue(), err.getvalue(), writes

    def test_a_skip_is_a_failure_on_stderr_and_the_rest_still_applies(self):
        code, out, err, writes = self.run_apply(
            "key\tfield\tvalue\nzz\tpriority\tP1\na1\tpriority\tP1\n"
        )
        self.assertEqual(1, code, out + err)
        self.assertIn("SKIP zz: not on this board", err)
        self.assertNotIn("SKIP", out, "a refusal belongs on stderr, not in the row log")
        self.assertIn("APPLY a1 priority", out, "the resolvable row still applies")
        self.assertEqual(
            [["kata", "edit", "a1", "--priority", "1", "--project", "demo", "--agent"]], writes
        )

    def test_a_wholly_resolvable_changeset_exits_clean(self):
        code, out, err, writes = self.run_apply("key\tfield\tvalue\na1\tpriority\tP1\n")
        self.assertEqual(0, code, out + err)
        self.assertNotIn("SKIP", out + err)
        self.assertEqual(1, len(writes))


class Cli(unittest.TestCase):
    """argparse wiring: which command runs, and what the flags default to."""

    def run_main(self, argv, command):
        seen = {}

        def handler(args):
            seen.update(vars(args))
            return 0

        with mock.patch.object(kb, command, handler):
            code = kb.main(argv)
        return code, seen

    def test_export_routes_with_optional_out(self):
        code, seen = self.run_main(["export", "--project", "demo"], "cmd_export")
        self.assertEqual(0, code)
        self.assertEqual("demo", seen["project"])
        self.assertIsNone(seen["out"], "--out defaults to stdout")

    def test_apply_is_dry_run_unless_asked(self):
        _, seen = self.run_main(["apply", "--project", "d", "--changeset", "c.tsv"], "cmd_apply")
        self.assertFalse(seen["apply"], "a write must be opt-in")
        _, seen = self.run_main(
            ["apply", "--project", "d", "--changeset", "c.tsv", "--apply"], "cmd_apply"
        )
        self.assertTrue(seen["apply"])

    def test_a_missing_subcommand_or_project_is_a_usage_error(self):
        for argv in ([], ["export"], ["apply", "--project", "d"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as caught:
                with open(os.devnull, "w") as devnull:
                    stderr, sys.stderr = sys.stderr, devnull
                    try:
                        kb.main(argv)
                    finally:
                        sys.stderr = stderr
            self.assertEqual(2, caught.exception.code)

    def test_help_needs_no_kata_binary(self):
        with self.assertRaises(SystemExit) as caught:
            with open(os.devnull, "w") as devnull:
                stdout, sys.stdout = sys.stdout, devnull
                try:
                    kb.main(["--help"])
                finally:
                    sys.stdout = stdout
        self.assertEqual(0, caught.exception.code)


if __name__ == "__main__":
    unittest.main()
