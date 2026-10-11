"""board-triage's Backlog.md adapter: the transformations, not the network.

Sibling of test_kata_board.py, covered on the same principle: everything between
`backlog task list --json` and the argv of a write is this adapter's own judgment and can
be wrong on its own, so it is tested; the `backlog` calls themselves are only checked at
the boundary (the argv built and the exit-code contract).

What breaks silently if this drifts: a band that maps to the wrong native value
re-prioritises a whole board, a cell that no longer compares equal turns every re-run
into fresh writes, and a done-status row that stops being refused closes work from a
triage pass.
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

import backlog_board as bb  # noqa: E402

STATUSES = ["To Do", "In Progress", "Done"]
CONFIG_LABELS = ["docs"]
# Shaped like `backlog task list --json` (trimmed to the keys the adapter reads): one
# triaged task, one untouched by triage, one already done.
TASKS = [
    {"id": "TASK-2", "title": "already urgent", "status": "To Do", "priority": "high",
     "labels": ["infra", "api"], "dueDate": "2026-09-01"},
    {"id": "TASK-1", "title": "untriaged thing", "status": "To Do", "priority": None,
     "labels": [], "dueDate": None},
    {"id": "TASK-3", "title": "shipped", "status": "Done", "priority": "medium",
     "labels": ["shipped"], "dueDate": None},
]


def snapshot():
    return bb.build_snapshot("/work/demo", TASKS, STATUSES, CONFIG_LABELS)


def argvs(ops):
    return [argv for argv, _ in ops]


class BandMap(unittest.TestCase):
    def test_bands_write_down_to_backlog_priorities(self):
        self.assertEqual(
            {"p0": "high", "p1": "high", "p2": "medium", "p3": "low"}, bb.BAND_TO_PRIORITY
        )

    def test_priorities_read_back_up_to_bands_and_p0_has_no_home(self):
        self.assertEqual({"high": "P1", "medium": "P2", "low": "P3"}, bb.PRIORITY_TO_BAND)

    def test_p0_against_a_high_task_is_no_change(self):
        ops, problems = bb.plan(snapshot(), [("TASK-2", "priority", "P0")], STATUSES)
        self.assertEqual(([], []), (ops, problems), "P0 lands as high and reads back as P1")

    def test_p1_against_a_high_task_is_no_change_and_p2_is_a_write(self):
        self.assertEqual(([], []), bb.plan(snapshot(), [("TASK-2", "priority", "P1")], STATUSES))
        ops, _ = bb.plan(snapshot(), [("TASK-2", "priority", "P2")], STATUSES)
        self.assertEqual([["task", "edit", "TASK-2", "--priority", "medium"]], argvs(ops))


class Snapshot(unittest.TestCase):
    def test_shape_matches_the_contract(self):
        snap = snapshot()
        self.assertEqual({"name": "demo", "backend": "backlog"}, snap["board"])
        self.assertEqual(["P0", "P1", "P2", "P3"], snap["fields"]["priority"]["options"])
        self.assertEqual(["YYYY-MM-DD"], snap["fields"]["due"]["options"])
        json.dumps(snap)  # the snapshot has to survive a round-trip to the analyst

    def test_status_options_are_the_configured_ones_minus_done(self):
        self.assertEqual(["To Do", "In Progress"], snapshot()["fields"]["status"]["options"])

    def test_label_options_union_config_and_every_listed_task_done_included(self):
        self.assertEqual(
            ["api", "docs", "infra", "shipped"], snapshot()["fields"]["labels"]["options"]
        )

    def test_done_tasks_are_excluded_at_export_case_insensitively(self):
        tasks = TASKS + [{"id": "TASK-4", "title": "x", "status": "DONE", "labels": []}]
        snap = bb.build_snapshot("/w/demo", tasks, STATUSES, [])
        self.assertEqual({"TASK-2", "TASK-1"}, {i["key"] for i in snap["items"]})

    def test_the_last_configured_status_is_the_done_one(self):
        snap = bb.build_snapshot(
            "/w/d", [{"id": "T-1", "status": "Shipped"}, {"id": "T-2", "status": "Done"}],
            ["Open", "Shipped"], [],
        )
        self.assertEqual(["T-2"], [i["key"] for i in snap["items"]])
        self.assertEqual(["Open"], snap["fields"]["status"]["options"])

    def test_native_values_read_back_as_rubric_cells(self):
        item = next(i for i in snapshot()["items"] if i["key"] == "TASK-2")
        self.assertEqual("TASK-2", item["id"])
        self.assertEqual("open", item["state"])
        self.assertEqual({"priority": "P1", "status": "To Do", "due": "2026-09-01"}, item["fields"])
        self.assertEqual(["api", "infra"], item["labels"], "labels are sorted")

    def test_untriaged_cells_read_as_null(self):
        item = next(i for i in snapshot()["items"] if i["key"] == "TASK-1")
        self.assertEqual({"priority": None, "status": "To Do", "due": None}, item["fields"])

    def test_missing_or_null_labels_do_not_crash(self):
        snap = bb.build_snapshot("/w/d", [{"id": "T-1", "status": "To Do", "labels": None}], STATUSES, [])
        self.assertEqual([], snap["items"][0]["labels"])

    def test_fetch_reads_tasks_statuses_and_labels_from_the_root(self):
        replies = {
            ("task", "list", "--json", "--sort", "id"): json.dumps({"tasks": TASKS}),
            ("config", "get", "statuses"): "To Do, In Progress, Done\n",
            ("config", "get", "labels"): "docs\n",
        }
        with mock.patch.object(bb, "_backlog", lambda args, root: replies[tuple(args)]):
            snap, statuses = bb.fetch_snapshot("/work/demo")
        self.assertEqual(STATUSES, statuses)
        self.assertEqual(["TASK-2", "TASK-1"], [i["key"] for i in snap["items"]])

    def test_an_empty_label_config_and_an_empty_board_are_a_legal_board(self):
        replies = {
            ("task", "list", "--json", "--sort", "id"): json.dumps({"tasks": []}),
            ("config", "get", "statuses"): "To Do, Done\n",
            ("config", "get", "labels"): "\n",
        }
        with mock.patch.object(bb, "_backlog", lambda args, root: replies[tuple(args)]):
            snap, _ = bb.fetch_snapshot(".")
        self.assertEqual([], snap["items"])
        self.assertEqual([], snap["fields"]["labels"]["options"])


class Normalize(unittest.TestCase):
    def test_bands_resolve_to_backlog_priorities(self):
        self.assertEqual(("high", None), bb.normalize("priority", "P0", STATUSES))
        self.assertEqual(("medium", None), bb.normalize("priority", " p2 ", STATUSES))
        self.assertEqual(("low", None), bb.normalize("priority", "P3", STATUSES))

    def test_a_blank_priority_normalizes_to_unset(self):
        self.assertEqual((None, None), bb.normalize("priority", "  ", STATUSES))

    def test_priority_off_the_rubric_is_refused(self):
        value, problem = bb.normalize("priority", "P9", STATUSES)
        self.assertIsNone(value)
        self.assertIn("P9", problem)

    def test_labels_split_strip_dedupe_and_sort(self):
        self.assertEqual((["api", "infra"], None), bb.normalize("labels", " infra , api ,infra,", STATUSES))
        self.assertEqual(([], None), bb.normalize("labels", "", STATUSES))

    def test_status_is_written_in_the_configured_case(self):
        self.assertEqual(("In Progress", None), bb.normalize("status", "in progress", STATUSES))
        self.assertEqual(("To Do", None), bb.normalize("status", " TO DO ", STATUSES))

    def test_the_done_status_is_refused_as_not_a_triage_move(self):
        value, problem = bb.normalize("status", "done", STATUSES)
        self.assertIsNone(value)
        self.assertIn("closing is the landing step, not triage", problem)

    def test_an_unconfigured_or_blank_status_is_refused(self):
        for raw in ("Blocked", ""):
            with self.subTest(raw=raw):
                value, problem = bb.normalize("status", raw, STATUSES)
                self.assertIsNone(value)
                self.assertIn("To Do, In Progress", problem)

    def test_due_dates_pass_through_blank_clears_and_junk_is_refused(self):
        self.assertEqual(("2026-09-01", None), bb.normalize("due", " 2026-09-01 ", STATUSES))
        self.assertEqual((None, None), bb.normalize("due", "", STATUSES))
        value, problem = bb.normalize("due", "next week", STATUSES)
        self.assertIsNone(value)
        self.assertIn("YYYY-MM-DD", problem)
        self.assertIn("YYYY-MM-DD", bb.normalize("due", "2026-13-40", STATUSES)[1])


class Changeset(unittest.TestCase):
    def test_parses_tsv_and_skips_header_and_comments(self):
        rows = bb.parse_changeset("key\tfield\tvalue\n# note\n\nTASK-1\tpriority\tP1\n")
        self.assertEqual([("TASK-1", "priority", "P1")], rows)

    def test_field_is_lowercased_and_a_tabbed_value_survives(self):
        self.assertEqual([("T-1", "title", "one\ttwo")], bb.parse_changeset("T-1\tTitle\tone\ttwo"))

    def test_a_row_without_a_field_is_fatal_not_guessed(self):
        with self.assertRaises(SystemExit) as caught:
            bb.parse_changeset("TASK-1\n")
        self.assertIn("line 1", str(caught.exception))


class Plan(unittest.TestCase):
    def plan(self, *rows):
        return bb.plan(snapshot(), list(rows), STATUSES)

    def test_writes_only_differing_cells(self):
        ops, problems = self.plan(("TASK-1", "priority", "P1"), ("TASK-2", "priority", "P1"))
        self.assertEqual([], problems)
        self.assertEqual([["task", "edit", "TASK-1", "--priority", "high"]], argvs(ops))

    def test_replanning_an_applied_changeset_is_empty(self):
        rows = [("TASK-2", "priority", "P1"), ("TASK-2", "due", "2026-09-01"),
                ("TASK-2", "labels", "api,infra"), ("TASK-2", "status", "to do")]
        self.assertEqual(([], []), self.plan(*rows), "apply must be idempotent")

    def test_a_status_write_carries_the_canonical_case(self):
        ops, problems = self.plan(("TASK-1", "status", "in progress"))
        self.assertEqual([], problems)
        self.assertEqual([["task", "edit", "TASK-1", "-s", "In Progress"]], argvs(ops))

    def test_a_status_already_set_in_another_case_is_no_change(self):
        snap = snapshot()
        snap["items"][0]["fields"]["status"] = "in progress"
        self.assertEqual(([], []), bb.plan(snap, [("TASK-2", "status", "In Progress")], STATUSES))

    def test_the_done_status_is_a_skip_not_a_write(self):
        ops, problems = self.plan(("TASK-1", "status", "Done"))
        self.assertEqual([], ops)
        self.assertIn("TASK-1: ", problems[0])
        self.assertIn("closing is the landing step", problems[0])

    def test_labels_write_the_full_desired_set(self):
        ops, problems = self.plan(("TASK-2", "labels", "infra,docs"))
        self.assertEqual([], problems)
        self.assertEqual([["task", "edit", "TASK-2", "-l", "docs,infra"]], argvs(ops))
        self.assertEqual("TASK-2 labels: +docs -api", ops[0][1])

    def test_the_same_label_set_in_any_order_is_no_change(self):
        self.assertEqual(([], []), self.plan(("TASK-2", "labels", "infra, api")))

    def test_an_empty_label_set_clears_them_and_is_free_when_already_empty(self):
        ops, _ = self.plan(("TASK-2", "labels", ""))
        self.assertEqual([["task", "edit", "TASK-2", "--clear-labels"]], argvs(ops))
        self.assertEqual(([], []), self.plan(("TASK-1", "labels", "")))

    def test_setting_and_clearing_a_due_date(self):
        ops, problems = self.plan(("TASK-1", "due", "2026-10-01"), ("TASK-2", "due", ""))
        self.assertEqual([], problems)
        self.assertEqual(
            [["task", "edit", "TASK-1", "--due-date", "2026-10-01"],
             ["task", "edit", "TASK-2", "--clear-due-date"]],
            argvs(ops),
        )
        self.assertEqual(([], []), self.plan(("TASK-1", "due", "")))

    def test_a_blank_priority_is_a_skip_when_one_is_set(self):
        ops, problems = self.plan(("TASK-2", "priority", ""))
        self.assertEqual([], ops)
        self.assertEqual(["TASK-2: Backlog.md cannot clear a priority"], problems)

    def test_a_blank_priority_on_an_untriaged_task_is_no_change(self):
        self.assertEqual(([], []), self.plan(("TASK-1", "priority", "")))

    def test_a_non_band_priority_is_a_skip(self):
        ops, problems = self.plan(("TASK-1", "priority", "urgent"))
        self.assertEqual([], ops)
        self.assertIn("'urgent' is not a band", problems[0])

    def test_unknown_task_and_unmapped_field_are_reported_not_guessed(self):
        ops, problems = self.plan(
            ("TASK-9", "priority", "P1"), ("TASK-1", "impact", "High"), ("TASK-1", "assignee", "x")
        )
        self.assertEqual([], ops)
        self.assertEqual(3, len(problems))
        self.assertIn("not on this board", problems[0])
        self.assertIn("no Backlog.md cell for field 'impact'", problems[1])
        self.assertIn("'assignee'", problems[2])

    def test_a_done_task_is_not_on_the_board_so_its_rows_skip(self):
        ops, problems = self.plan(("TASK-3", "priority", "P1"))
        self.assertEqual([], ops)
        self.assertIn("TASK-3: not on this board", problems[0])


class BacklogCalls(unittest.TestCase):
    """The subprocess boundary: the argv built, cwd as the board locator, exit as the contract."""

    def completed(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_calls_run_from_the_board_root(self):
        with mock.patch.object(bb.subprocess, "run") as run:
            run.return_value = self.completed(stdout="out\n")
            self.assertEqual("out\n", bb._backlog(["task", "list", "--json"], "/work/demo"))
        self.assertEqual(["backlog", "task", "list", "--json"], run.call_args[0][0])
        self.assertEqual("/work/demo", run.call_args[1]["cwd"])

    def test_a_failed_call_stops_the_run_and_surfaces_stderr(self):
        with mock.patch.object(bb.subprocess, "run") as run:
            run.return_value = self.completed(returncode=1, stderr="No Backlog.md project found")
            with self.assertRaises(SystemExit) as caught:
                bb._backlog(["task", "list", "--json"], ".")
        self.assertIn("No Backlog.md project found", str(caught.exception))

    def test_a_missing_binary_or_root_is_a_clean_exit_not_a_traceback(self):
        with mock.patch.object(bb.subprocess, "run", side_effect=FileNotFoundError("backlog")):
            with self.assertRaises(SystemExit) as caught:
                bb._backlog(["config", "get", "statuses"], "/nope")
        self.assertIn("backlog", str(caught.exception))

    def test_an_empty_status_config_is_fatal_not_an_index_error(self):
        replies = {("task", "list", "--json", "--sort", "id"): '{"tasks": []}', ("config", "get", "statuses"): "\n",
                   ("config", "get", "labels"): "\n"}
        with mock.patch.object(bb, "_backlog", lambda args, root: replies[tuple(args)]):
            with self.assertRaises(SystemExit) as caught:
                bb.fetch_snapshot(".")
        self.assertIn("statuses", str(caught.exception))


class ApplyExitContract(unittest.TestCase):
    """cmd_apply end to end: a SKIP is a failure, on stderr, and the rest still applies."""

    def run_apply(self, changeset, *flags):
        calls = []

        def run(cmd, capture_output=False, text=False, cwd=None, **_):
            calls.append((list(cmd), cwd))
            if cmd[1:6] == ["task", "list", "--json", "--sort", "id"]:
                return mock.Mock(returncode=0, stdout=json.dumps({"tasks": TASKS}), stderr="")
            if cmd[1:4] == ["config", "get", "statuses"]:
                return mock.Mock(returncode=0, stdout="To Do, In Progress, Done\n", stderr="")
            if cmd[1:4] == ["config", "get", "labels"]:
                return mock.Mock(returncode=0, stdout="docs\n", stderr="")
            return mock.Mock(returncode=0, stdout="Updated task\n", stderr="")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "changeset.tsv")
        with open(path, "w") as handle:
            handle.write(changeset)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(bb.subprocess, "run", run), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bb.main(["apply", "--root", "/work/demo", "--changeset", path, *flags])
        writes = [c for c in calls if c[0][1:3] == ["task", "edit"]]
        return code, out.getvalue(), err.getvalue(), writes

    def test_a_skip_is_a_failure_on_stderr_and_the_rest_still_applies(self):
        code, out, err, writes = self.run_apply(
            "key\tfield\tvalue\nTASK-9\tpriority\tP1\nTASK-1\tpriority\tP1\n", "--apply"
        )
        self.assertEqual(1, code, out + err)
        self.assertIn("SKIP TASK-9: not on this board", err)
        self.assertNotIn("SKIP", out, "a refusal belongs on stderr, not in the row log")
        self.assertIn("APPLY TASK-1 priority", out, "the resolvable row still applies")
        self.assertEqual(
            [(["backlog", "task", "edit", "TASK-1", "--priority", "high"], "/work/demo")], writes
        )

    def test_a_wholly_resolvable_changeset_exits_clean(self):
        code, out, err, writes = self.run_apply("key\tfield\tvalue\nTASK-1\tpriority\tP1\n", "--apply")
        self.assertEqual(0, code, out + err)
        self.assertNotIn("SKIP", out + err)
        self.assertEqual(1, len(writes))

    def test_dry_run_is_the_default_and_writes_nothing(self):
        code, out, _, writes = self.run_apply("TASK-1\tpriority\tP1\n")
        self.assertEqual(0, code)
        self.assertEqual([], writes)
        self.assertIn("DRY   TASK-1 priority", out)
        self.assertIn("re-run with --apply", out)

    def test_a_changeset_with_nothing_to_change_says_so(self):
        code, out, _, writes = self.run_apply("TASK-2\tpriority\tP0\n", "--apply")
        self.assertEqual(0, code)
        self.assertEqual([], writes)
        self.assertIn("nothing to change", out)


class Cli(unittest.TestCase):
    """argparse wiring: which command runs, and what the flags default to."""

    def run_main(self, argv, command):
        seen = {}

        def handler(args):
            seen.update(vars(args))
            return 0

        with mock.patch.object(bb, command, handler):
            code = bb.main(argv)
        return code, seen

    def test_export_routes_with_root_defaulting_to_cwd_and_optional_out(self):
        code, seen = self.run_main(["export"], "cmd_export")
        self.assertEqual(0, code)
        self.assertEqual(".", seen["root"])
        self.assertIsNone(seen["out"], "--out defaults to stdout")
        _, seen = self.run_main(["export", "--root", "/b", "--out", "s.json"], "cmd_export")
        self.assertEqual(("/b", "s.json"), (seen["root"], seen["out"]))

    def test_apply_is_dry_run_unless_asked(self):
        _, seen = self.run_main(["apply", "--changeset", "c.tsv"], "cmd_apply")
        self.assertFalse(seen["apply"], "a write must be opt-in")
        _, seen = self.run_main(["apply", "--changeset", "c.tsv", "--apply"], "cmd_apply")
        self.assertTrue(seen["apply"])

    def test_a_missing_subcommand_or_changeset_is_a_usage_error(self):
        for argv in ([], ["apply"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    bb.main(argv)
                self.assertEqual(2, caught.exception.code)

    def test_help_needs_no_backlog_binary(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
            bb.main(["--help"])
        self.assertEqual(0, caught.exception.code)


if __name__ == "__main__":
    unittest.main()
