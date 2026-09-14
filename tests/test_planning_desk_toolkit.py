"""The planning-desk toolkit: the Kata adapter, the snapshot loader, and the three
analysis scripts that read a snapshot.

Two boundaries are faked and nothing else: `subprocess.run` becomes an argv dispatcher
(so a test pins the argv a script BUILT, not just the value it got back), and the plans
desk is a tempdir wired in by patching each module's `PLANS_DIR` / `README`. Everything
between the tracker's `list --json` and a mutation's argv is this toolkit's own judgment
and can be wrong on its own, so it is tested directly.

What breaks silently if this drifts: a snapshot field that stops normalizing turns an
absent value into a KeyError mid-audit, a `state`/`status` row that stops being refused
writes a lane the tracker does not have, and a ref rule that stops matching makes every
plan look untracked.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
UTILS = ROOT / "primitives-core" / "skills" / "planning-desk" / "scripts" / "_utils"

sys.path.insert(0, str(UTILS))

import conformance  # noqa: E402
import reconcile  # noqa: E402
import tracker  # noqa: E402


def _load(name: str, path: Path):
    """Load a bundled script under an explicit module name (`coverage` would collide
    with the well-known third-party package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


kata = _load("pd_kata_adapter", UTILS / "adapters" / "kata.py")
pd_coverage = _load("pd_coverage", UTILS / "coverage.py")

# --------------------------------------------------------------------------- fixtures
# Hand-shaped to mirror the tracker's `list --json`, whose shape was read off a live
# 303-issue payload on 2026-09-07: an unset field is ABSENT, never an explicit null --
# that payload contained zero JSON nulls of any kind. `child_counts` is `{open, total}`
# when there are children and absent otherwise; `parent` is an object; `blocked_by` is
# a list of objects. `c0ld` carries explicit nulls anyway, as a tolerance case: the
# adapter must not care which way a tracker spells "nothing here".
ISSUES = [
    {
        "short_id": "xmwb",
        "title": "Wire the adapter",
        "body": "## Acceptance criteria\n- it exports\n\n## Dependencies & gates\n- none\n",
        "status": "open",
        "priority": 1,
        "labels": ["infra", "chore"],
        "owner": "some-actor",
        "parent": {"short_id": "p937", "qualified_id": "demo#p937", "status": "open"},
        "blocked_by": [{"short_id": "ay9p", "qualified_id": "demo#ay9p"}],
        "qualified_id": "demo#xmwb",
    },
    {
        "short_id": "p937",
        "title": "The desk itself",
        "body": "## Close when\n- every child lands\n",
        "status": "open",
        "labels": [],
        "child_counts": {"open": 1, "total": 2},
        "qualified_id": "demo#p937",
    },
    {
        # Nothing set: no priority, no owner, no parent, no labels, no child_counts.
        "short_id": "ay9p",
        "title": "Prose only",
        "body": "just a paragraph",
        "status": "open",
        "qualified_id": "demo#ay9p",
    },
    {
        "short_id": "epk1",
        "title": "Epic by label, no children yet",
        "body": "## Close criteria\n- ships\n",
        "status": "open",
        "labels": ["epic"],
        "qualified_id": "demo#epk1",
    },
    {
        "short_id": "c0ld",
        "title": "Already done",
        "body": "## Acceptance criteria\n- shipped\n\n## Gates\n- none\n",
        "status": "closed",
        "priority": 4,  # off the P0-P3 band vocabulary
        "labels": ["chore"],
        "closed_reason": "done",
        # Explicit nulls, which this tracker does not emit but another might.
        "owner": None,
        "child_counts": None,
        "blocked_by": None,
        "qualified_id": "demo#c0ld",
    },
]


def snapshot(project="demo", issues=None):
    return kata.build_snapshot(project, ISSUES if issues is None else issues)


def item(snap, key):
    return next(i for i in snap["items"] if i["key"] == key)


class Snapshot(unittest.TestCase):
    def test_shape_matches_the_contract(self):
        snap = snapshot()
        self.assertEqual({"name": "demo", "backend": "kata"}, snap["tracker"])
        self.assertEqual(
            ["ay9p", "c0ld", "epk1", "p937", "xmwb"],
            [i["key"] for i in snap["items"]],
            "items sort by key",
        )
        self.assertEqual(
            {
                "key",
                "title",
                "state",
                "kind",
                "labels",
                "body",
                "parent",
                "blocked_by",
                "priority",
                "owner",
            },
            set(item(snap, "xmwb")),
        )
        json.dumps(snap)  # the snapshot has to survive a round-trip to the analyst

    def test_a_fully_populated_item_reads_back_whole(self):
        got = item(snapshot(), "xmwb")
        self.assertEqual("open", got["state"])
        self.assertEqual("issue", got["kind"])
        self.assertEqual("P1", got["priority"])
        self.assertEqual(["chore", "infra"], got["labels"], "labels are sorted")
        self.assertEqual("p937", got["parent"])
        self.assertEqual(["ay9p"], got["blocked_by"])
        self.assertEqual("some-actor", got["owner"])

    def test_absent_fields_normalize_to_null_and_empty_never_missing(self):
        got = item(snapshot(), "ay9p")
        self.assertIsNone(got["priority"])
        self.assertIsNone(got["parent"])
        self.assertIsNone(got["owner"])
        self.assertEqual([], got["blocked_by"])
        self.assertEqual([], got["labels"])
        self.assertEqual("issue", got["kind"])

    def test_an_explicit_null_normalizes_the_same_way_an_absent_key_does(self):
        got = item(snapshot(), "c0ld")
        self.assertIsNone(got["owner"])
        self.assertEqual([], got["blocked_by"])
        self.assertEqual("issue", got["kind"], "a null child_counts is not children")

    def test_children_make_an_epic_even_without_the_label(self):
        self.assertEqual("epic", item(snapshot(), "p937")["kind"])

    def test_the_label_makes_an_epic_even_without_children(self):
        self.assertEqual("epic", item(snapshot(), "epk1")["kind"])

    def test_closed_items_keep_their_state_rather_than_being_dropped(self):
        self.assertEqual("closed", item(snapshot(), "c0ld")["state"])

    def test_a_priority_off_the_band_vocabulary_is_null_not_invented(self):
        self.assertIsNone(item(snapshot(), "c0ld")["priority"], "native 4 has no band")

    def test_the_tracker_name_falls_back_to_what_the_tracker_reported(self):
        """No --project: the name comes from the items' own qualified ids."""
        self.assertEqual("demo", snapshot(project=None)["tracker"]["name"])

    def test_an_empty_tracker_still_produces_a_valid_snapshot(self):
        snap = kata.build_snapshot(None, [])
        self.assertEqual({"name": "", "backend": "kata"}, snap["tracker"])
        self.assertEqual([], snap["items"])


class Normalize(unittest.TestCase):
    def test_bands_resolve_to_native_integers(self):
        self.assertEqual((0, None), kata.normalize("priority", "P0"))
        self.assertEqual((3, None), kata.normalize("priority", "p3"))

    def test_blank_priority_is_a_clear_not_an_error(self):
        self.assertEqual((None, None), kata.normalize("priority", "  "))

    def test_priority_off_the_rubric_is_refused(self):
        value, problem = kata.normalize("priority", "P9")
        self.assertIsNone(value)
        self.assertIn("P9", problem)

    def test_labels_split_strip_and_sort(self):
        self.assertEqual((["api", "infra"], None), kata.normalize("labels", " infra , api ,"))

    def test_state_and_status_have_no_changeset_cell(self):
        for field in ("state", "status"):
            with self.subTest(field=field):
                value, problem = kata.normalize(field, "closed")
                self.assertIsNone(value)
                self.assertIn("not a changeset cell", problem)

    def test_owner_passes_through_with_blank_as_none(self):
        self.assertEqual(("someone", None), kata.normalize("owner", " someone "))
        self.assertEqual((None, None), kata.normalize("owner", ""))


class Changeset(unittest.TestCase):
    def test_parses_tsv_and_skips_header_comments_and_blanks(self):
        rows = kata.parse_changeset("key\tfield\tvalue\n# note\n\nay9p\tpriority\tP1\n")
        self.assertEqual([("ay9p", "priority", "P1")], rows)

    def test_field_is_lowercased_and_a_tabbed_value_survives(self):
        self.assertEqual(
            [("ay9p", "title", "one\ttwo")], kata.parse_changeset("ay9p\tTitle\tone\ttwo")
        )

    def test_a_row_without_a_field_is_fatal_not_guessed(self):
        with self.assertRaises(SystemExit) as caught:
            kata.parse_changeset("ay9p\n")
        self.assertIn("line 1", str(caught.exception))

    def test_a_row_with_no_value_COLUMN_is_fatal_not_an_empty_value(self):
        """A lost trailing tab must not read as "clear this cell": on a labels row an
        empty value plans a `label rm` for every label the item has."""
        with self.assertRaises(SystemExit) as caught:
            kata.parse_changeset("xmwb\tlabels\n")
        self.assertIn("line 1", str(caught.exception))

    def test_an_empty_value_column_is_still_a_clear(self):
        self.assertEqual([("xmwb", "labels", "")], kata.parse_changeset("xmwb\tlabels\t"))


class Plan(unittest.TestCase):
    def test_writes_only_differing_cells(self):
        ops, problems = kata.plan(
            snapshot(), [("ay9p", "priority", "P1"), ("xmwb", "priority", "P1")]
        )
        self.assertEqual([], problems)
        self.assertEqual(
            [["edit", "ay9p", "--priority", "1"]],
            [argv for argv, _ in ops],
            "xmwb is already P1 -- a no-op row must not produce a write",
        )

    def test_replanning_an_applied_changeset_is_empty(self):
        rows = [
            ("xmwb", "priority", "P1"),
            ("xmwb", "labels", "chore,infra"),
            ("xmwb", "owner", "some-actor"),
            ("ay9p", "owner", ""),
        ]
        self.assertEqual(([], []), kata.plan(snapshot(), rows), "apply must be idempotent")

    def test_labels_diff_into_add_and_remove(self):
        ops, problems = kata.plan(snapshot(), [("xmwb", "labels", "infra,needs-plan")])
        self.assertEqual([], problems)
        self.assertEqual(
            [["label", "add", "xmwb", "needs-plan"], ["label", "rm", "xmwb", "chore"]],
            [argv for argv, _ in ops],
        )

    def test_a_blank_priority_clears_the_cell(self):
        ops, _ = kata.plan(snapshot(), [("xmwb", "priority", "")])
        self.assertEqual([["edit", "xmwb", "--priority", "-"]], [argv for argv, _ in ops])

    def test_owner_assigns_and_unassigns_only_when_it_differs(self):
        rows = [
            ("ay9p", "owner", "you"),  # unowned -> assign
            ("xmwb", "owner", ""),  # owned -> unassign
            ("xmwb", "owner", "some-actor"),  # already the owner -> nothing
        ]
        ops, problems = kata.plan(snapshot(), rows)
        self.assertEqual([], problems)
        self.assertEqual(
            [["assign", "ay9p", "you"], ["unassign", "xmwb"]], [argv for argv, _ in ops]
        )

    def test_unknown_key_and_unknown_field_are_reported_not_guessed(self):
        ops, problems = kata.plan(
            snapshot(), [("zzzz", "priority", "P1"), ("ay9p", "impact", "High")]
        )
        self.assertEqual([], ops)
        self.assertEqual(2, len(problems))
        self.assertIn("not on this tracker", problems[0])
        self.assertIn("no cell for field 'impact'", problems[1])

    def test_a_status_row_is_refused_rather_than_written_somewhere_else(self):
        ops, problems = kata.plan(snapshot(), [("ay9p", "status", "closed")])
        self.assertEqual([], ops)
        self.assertIn("not a changeset cell", problems[0])

    def test_a_closed_item_still_resolves(self):
        """apply re-resolves against every item, so a label on a closed item lands."""
        ops, problems = kata.plan(snapshot(), [("c0ld", "labels", "chore,archived")])
        self.assertEqual([], problems)
        self.assertEqual([["label", "add", "c0ld", "archived"]], [argv for argv, _ in ops])


class TrackerCalls(unittest.TestCase):
    """The subprocess boundary: the argv built, and exit code as the contract."""

    def completed(self, returncode=0, stdout="", stderr=""):
        return mock.Mock(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_reads_are_json_and_project_scoped(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(stdout='{"issues": []}')
            self.assertEqual({"issues": []}, kata._read(["list"], "demo"))
        self.assertEqual(["kata", "list", "--project", "demo", "--json"], run.call_args[0][0])

    def test_no_project_means_no_project_flag_at_all(self):
        """Absent --project, the binary resolves the project from the workspace."""
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(stdout="{}")
            kata._read(["list"], None)
        self.assertEqual(["kata", "list", "--json"], run.call_args[0][0])

    def test_export_asks_for_every_row_not_the_default_page(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(stdout=json.dumps({"issues": ISSUES}))
            snap = kata.fetch_snapshot(None, "all")
        self.assertEqual(
            ["kata", "list", "--status", "all", "--limit", "0", "--json"], run.call_args[0][0]
        )
        self.assertEqual(5, len(snap["items"]))

    def test_empty_read_output_is_an_empty_result_not_a_crash(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(stdout="  ")
            self.assertEqual({}, kata._read(["list"], "demo"))

    def test_output_that_is_not_json_is_a_sentence_not_a_traceback(self):
        """A notice or progress line on stdout must not surface as a decoder error."""
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(stdout="notice: connecting...\n{}")
            with self.assertRaises(SystemExit) as caught:
                kata._read(["list"], "demo")
        self.assertIn("not JSON", str(caught.exception))

    def test_a_failed_read_stops_the_run_and_surfaces_stderr(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(returncode=2, stderr="no such project")
            with self.assertRaises(SystemExit) as caught:
                kata._read(["list"], "demo")
        self.assertIn("no such project", str(caught.exception))

    def test_writes_use_agent_output_and_fail_loudly(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed()
            kata._write(["label", "add", "ay9p", "needs-plan"], None)
        self.assertEqual(
            ["kata", "label", "add", "ay9p", "needs-plan", "--agent"], run.call_args[0][0]
        )
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.completed(returncode=1, stderr="rejected")
            with self.assertRaises(SystemExit):
                kata._write(["label", "add", "ay9p", "needs-plan"], None)


class AdapterCli(unittest.TestCase):
    def listed(self, issues=ISSUES):
        return mock.Mock(returncode=0, stdout=json.dumps({"issues": issues}), stderr="")

    def test_export_writes_a_file_and_summarises_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "snap.json"
            with mock.patch.object(kata.subprocess, "run") as run:
                run.return_value = self.listed()
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = kata.main(
                        ["export", "--project", "demo", "--status", "all", "--out", str(out)]
                    )
            self.assertEqual(0, code)
            self.assertEqual(f"5 items (4 open, 1 closed) -> {out}", buffer.getvalue().strip())
            self.assertEqual(5, len(json.loads(out.read_text())["items"]))

    def test_export_without_out_prints_the_snapshot(self):
        with mock.patch.object(kata.subprocess, "run") as run:
            run.return_value = self.listed([])
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                kata.main(["export"])
        self.assertEqual([], json.loads(buffer.getvalue())["items"])

    def test_apply_is_dry_run_unless_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            changeset = Path(tmp) / "c.tsv"
            changeset.write_text("key\tfield\tvalue\nay9p\tlabels\tneeds-plan\n")
            with mock.patch.object(kata.subprocess, "run") as run:
                run.return_value = self.listed()
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = kata.main(["apply", "--changeset", str(changeset)])
            self.assertEqual(0, code)
            self.assertIn("DRY", buffer.getvalue())
            self.assertEqual(1, run.call_count, "a dry run reads the tracker and writes nothing")

    def test_an_unresolvable_row_exits_non_zero_while_the_rest_are_planned(self):
        with tempfile.TemporaryDirectory() as tmp:
            changeset = Path(tmp) / "c.tsv"
            changeset.write_text("zzzz\tlabels\tx\nay9p\tlabels\tneeds-plan\n")
            with mock.patch.object(kata.subprocess, "run") as run:
                run.return_value = self.listed()
                buffer, errors = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(errors):
                    code = kata.main(["apply", "--changeset", str(changeset)])
        self.assertEqual(1, code)
        self.assertIn("SKIP", errors.getvalue())
        self.assertIn("ay9p +needs-plan", buffer.getvalue())

    def test_a_missing_subcommand_is_a_usage_error(self):
        for argv in ([], ["apply"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as caught:
                with contextlib.redirect_stderr(io.StringIO()):
                    kata.main(argv)
            self.assertEqual(2, caught.exception.code)

    def test_help_needs_no_tracker_binary(self):
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stdout(io.StringIO()):
                kata.main(["--help"])
        self.assertEqual(0, caught.exception.code)


class SnapshotLoader(unittest.TestCase):
    """tracker.py: --snapshot wins, otherwise the named adapter is invoked."""

    def args(self, **overrides):
        defaults = {"snapshot": None, "adapter": "kata", "project": None, "status": "open"}
        defaults.update(overrides)
        return mock.Mock(**defaults)

    def test_a_snapshot_file_is_read_straight_off_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            payload = {"tracker": {"name": "demo", "backend": "kata"}, "items": []}
            path.write_text(json.dumps(payload))
            self.assertEqual(payload, tracker.load_snapshot(self.args(snapshot=str(path))))

    def test_without_a_snapshot_the_adapter_is_invoked(self):
        payload = {"tracker": {"name": "demo", "backend": "kata"}, "items": []}
        with mock.patch.object(tracker.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stdout=json.dumps(payload), stderr="")
            self.assertEqual(
                payload, tracker.load_snapshot(self.args(project="demo", status="all"))
            )
        argv = run.call_args[0][0]
        self.assertEqual(sys.executable, argv[0])
        self.assertTrue(argv[1].endswith(str(Path("adapters") / "kata.py")), argv[1])
        self.assertEqual(["export", "--status", "all", "--project", "demo"], argv[2:])

    def test_no_project_is_not_passed_down_to_the_adapter(self):
        with mock.patch.object(tracker.subprocess, "run") as run:
            run.return_value = mock.Mock(
                returncode=0, stdout='{"tracker": {}, "items": []}', stderr=""
            )
            tracker.load_snapshot(self.args())
        self.assertEqual(["export", "--status", "open"], run.call_args[0][0][2:])

    def test_adapter_output_that_is_not_json_is_a_sentence_not_a_traceback(self):
        """Symmetric with the --snapshot path: a bad payload is fatal either way."""
        with mock.patch.object(tracker.subprocess, "run") as run:
            run.return_value = mock.Mock(
                returncode=0, stdout="notice: connecting...\n{}", stderr=""
            )
            with self.assertRaises(SystemExit) as caught:
                tracker.load_snapshot(self.args())
        self.assertIn("kata.py", str(caught.exception))
        self.assertIn("not JSON", str(caught.exception))

    def test_a_failing_adapter_stops_the_run(self):
        with mock.patch.object(tracker.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=3, stdout="", stderr="daemon unreachable")
            with self.assertRaises(SystemExit) as caught:
                tracker.load_snapshot(self.args())
        self.assertIn("daemon unreachable", str(caught.exception))

    def test_an_unknown_adapter_names_the_path_it_looked_for(self):
        with self.assertRaises(SystemExit) as caught:
            tracker.load_snapshot(self.args(adapter="nope"))
        self.assertIn("nope.py", str(caught.exception))

    def test_malformed_json_is_loud_rather_than_an_empty_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            path.write_text("{not json")
            with self.assertRaises(SystemExit) as caught:
                tracker.load_snapshot(self.args(snapshot=str(path)))
        self.assertIn(str(path), str(caught.exception))
        self.assertIn("not JSON", str(caught.exception))

    def test_a_snapshot_missing_its_contract_keys_is_refused(self):
        for payload in ("{}", '{"items": []}', '{"tracker": {}}', '{"tracker": {}, "items": {}}'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "snap.json"
                path.write_text(payload)
                with self.assertRaises(SystemExit) as caught:
                    tracker.load_snapshot(self.args(snapshot=str(path)))
                self.assertIn("not a snapshot", str(caught.exception))

    def test_the_flags_land_on_a_parser_with_the_defaults_the_desk_expects(self):
        import argparse

        parser = argparse.ArgumentParser()
        tracker.add_tracker_args(parser)
        args = parser.parse_args([])
        self.assertEqual("kata", args.adapter)
        self.assertEqual("open", args.status)
        self.assertIsNone(args.snapshot)
        self.assertIsNone(args.project)

        other = argparse.ArgumentParser()
        tracker.add_tracker_args(other, default_status="all")
        self.assertEqual("all", other.parse_args([]).status)


# ------------------------------------------------- the analysis scripts' fixtures
def make_item(key, **overrides):
    """One contract-shaped snapshot item, every cell explicit."""
    base = {
        "key": key,
        "title": f"work on {key}",
        "state": "open",
        "kind": "issue",
        "labels": [],
        "body": "",
        "parent": None,
        "blocked_by": [],
        "priority": None,
    }
    base.update(overrides)
    return base


def make_snapshot(*items):
    return {"tracker": {"name": "demo", "backend": "kata"}, "items": list(items)}


CONFORMANT_BODY = "## Acceptance criteria\n- it works\n\n## Dependencies & gates\n- none\n"


def write_snapshot(directory, snapshot):
    path = Path(directory) / "snapshot.json"
    path.write_text(json.dumps(snapshot))
    return str(path)


@contextlib.contextmanager
def desk(readme: str, plans: dict):
    """A plans desk in a tempdir: README.md plus <slug>/plan.md for each entry.

    Both `reconcile` globals are patched, and `coverage` reads the desk through the
    same module object, so one patch covers every caller.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text(readme)
        for slug, body in plans.items():
            (root / slug).mkdir()
            if body is not None:
                (root / slug / "plan.md").write_text(body)
        with mock.patch.object(reconcile, "PLANS_DIR", root), mock.patch.object(
            reconcile, "README", root / "README.md"
        ):
            yield root


def run_main(module, argv):
    """Run a script's main() in-process; returns (exit code, stdout)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = module.main(argv)
    return code, buffer.getvalue()


class Conformance(unittest.TestCase):
    def test_a_body_with_both_required_sections_conforms(self):
        self.assertEqual([], conformance.audit_item(make_item("a1", body=CONFORMANT_BODY)))

    def test_missing_gates_alone_is_minor(self):
        item = make_item("a1", body="## Acceptance criteria\n- it works\n")
        missing = conformance.audit_item(item)
        self.assertEqual(["Dependencies & gates"], missing)
        self.assertEqual("MINOR", conformance.severity(missing, epic=False))

    def test_missing_acceptance_criteria_is_critical(self):
        item = make_item("a1", body="## Dependencies & gates\n- none\n")
        missing = conformance.audit_item(item)
        self.assertEqual(["Acceptance criteria"], missing)
        self.assertEqual("CRITICAL", conformance.severity(missing, epic=False))

    def test_a_body_with_no_headings_at_all_is_critical(self):
        missing = conformance.audit_item(make_item("a1", body="just a paragraph"))
        self.assertEqual(1, len(missing))
        self.assertIn("no headings", missing[0])
        self.assertEqual("CRITICAL", conformance.severity(missing, epic=False))

    def test_an_epic_is_judged_on_its_close_condition(self):
        epic = make_item("e1", kind="epic", body="## Close when\n- children land\n")
        self.assertEqual([], conformance.audit_item(epic))
        bare = make_item("e2", kind="epic", body="## Acceptance criteria\n- x\n")
        missing = conformance.audit_item(bare)
        self.assertEqual("EPIC", conformance.severity(missing, epic=True))

    def test_a_hash_comment_inside_a_fenced_block_is_not_a_heading(self):
        """The whole gate rests on this: a body of prose plus a shell block whose
        comments happen to say `accept` and `depends` is NOT conformant."""
        body = (
            "Some prose about the work.\n\n"
            "```bash\n"
            "# Accept the defaults\n"
            "# depends on node 20 and gates on make ci\n"
            "make ci\n"
            "```\n"
        )
        missing = conformance.audit_item(make_item("a1", body=body))
        self.assertEqual(1, len(missing))
        self.assertIn("no headings", missing[0])

    def test_a_fenced_comment_cannot_satisfy_a_section_a_real_heading_is_missing(self):
        body = "## Acceptance criteria\n- it works\n\n```sh\n# gates: make ci\n```\n"
        self.assertEqual(["Dependencies & gates"], conformance.audit_item(make_item("a1", body=body)))

    def test_a_tilde_fence_is_stripped_too(self):
        body = "prose\n\n~~~\n# Acceptance criteria\n# gates\n~~~\n"
        self.assertIn("no headings", conformance.audit_item(make_item("a1", body=body))[0])

    def test_a_real_heading_after_a_fenced_block_still_counts(self):
        body = (
            "## Acceptance criteria\n- x\n\n```sh\nmake ci\n```\n\n## Dependencies & gates\n- y\n"
        )
        self.assertEqual([], conformance.audit_item(make_item("a1", body=body)))

    def test_alternate_wordings_of_the_headings_are_accepted(self):
        item = make_item("a1", body="### Definition of done\n- x\n\n### Depends on\n- y\n")
        self.assertEqual([], conformance.audit_item(item))

    def test_closed_items_are_not_audited(self):
        snapshot = make_snapshot(make_item("c1", state="closed", body="nothing here"))
        result = conformance.run(snapshot)
        self.assertEqual({"total": 0, "bad": []}, result)

    def test_exit_codes_and_json_are_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean = write_snapshot(tmp, make_snapshot(make_item("a1", body=CONFORMANT_BODY)))
            code, out = run_main(conformance, ["--snapshot", clean])
            self.assertEqual(0, code)
            self.assertIn("1/1", out)

            path = Path(tmp) / "dirty.json"
            path.write_text(json.dumps(make_snapshot(make_item("b2", body="prose"))))
            code, out = run_main(conformance, ["--snapshot", str(path), "--json"])
            self.assertEqual(1, code)
            payload = json.loads(out)
            self.assertEqual("CRITICAL", payload["bad"][0]["severity"])
            self.assertEqual("b2", payload["bad"][0]["key"])

    def test_the_human_output_bands_every_finding(self):
        snapshot = make_snapshot(
            make_item("a1", body="prose only"),
            make_item("b2", body="## Acceptance criteria\n- x\n"),
            make_item("e3", kind="epic", body="## Acceptance criteria\n- x\n"),
            make_item("g4", body=CONFORMANT_BODY),
        )
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_main(conformance, ["--snapshot", write_snapshot(tmp, snapshot)])
        self.assertEqual(1, code)
        self.assertIn("1/4", out)
        for band in ("CRITICAL", "EPIC", "MINOR"):
            self.assertIn(band, out)
        self.assertIn("3 non-conformant", out)


class Coverage(unittest.TestCase):
    README = (
        "ACTIVE plans:\n\n"
        "| Plan | Tracker ref(s) | Status |\n| ---- | ---- | ---- |\n"
        "| alpha | `xmwb` | drafting |\n"
    )

    def snapshot(self):
        return make_snapshot(
            make_item("xmwb", labels=["chore"]),
            make_item("ay9p", labels=["documentation"]),
            make_item("p937", kind="epic"),
            make_item("c0ld", state="closed"),
            make_item("bug1", labels=["bug"], title="fix a typo"),
            make_item("bug2", labels=["bug"], title="refactor the importer"),
        )

    def test_the_backlog_is_open_non_epic_items_with_no_plan_folder(self):
        with desk(self.README, {"alpha": "## Tracking\n\n`xmwb`\n"}):
            result = pd_coverage.compute(self.snapshot())
        self.assertEqual(["ay9p", "bug1", "bug2"], [u["key"] for u in result["unplanned"]])
        self.assertEqual(1, result["planned_count"])
        self.assertEqual(
            4, result["non_epic_count"], "epics and closed items are not planning backlog"
        )

    def test_docs_and_small_bugs_are_tagged_maybe_trivial_not_dropped(self):
        with desk(self.README, {"alpha": "## Tracking\n\n`xmwb`\n"}):
            result = pd_coverage.compute(self.snapshot())
        trivial = {u["key"]: u["maybe_trivial"] for u in result["unplanned"]}
        self.assertTrue(trivial["ay9p"], "documentation")
        self.assertTrue(trivial["bug1"], "a small-looking bug")
        self.assertFalse(trivial["bug2"], "a broad-scope title is not trivial")

    def test_a_changeset_proposes_needs_plan_on_the_full_label_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = write_snapshot(tmp, self.snapshot())
            changeset = Path(tmp) / "changeset.tsv"
            with desk(self.README, {"alpha": "## Tracking\n\n`xmwb`\n"}):
                code, _ = run_main(
                    pd_coverage, ["--snapshot", snapshot, "--changeset", str(changeset)]
                )
            self.assertEqual(1, code)
            lines = changeset.read_text().splitlines()
        self.assertEqual("key\tfield\tvalue", lines[0])
        self.assertIn("ay9p\tlabels\tdocumentation,needs-plan", lines)
        self.assertIn("bug1\tlabels\tbug,needs-plan", lines)
        self.assertEqual(4, len(lines), "one row per uncovered item, header aside")

    def test_a_fully_covered_desk_exits_clean(self):
        readme = self.README + "| beta | `ay9p` | drafting |\n"
        plans = {"alpha": "## Tracking\n\n`xmwb`\n", "beta": "## Tracking\n\n`ay9p`\n"}
        snapshot = make_snapshot(make_item("xmwb"), make_item("ay9p"))
        with tempfile.TemporaryDirectory() as tmp, desk(readme, plans):
            code, out = run_main(pd_coverage, ["--snapshot", write_snapshot(tmp, snapshot)])
        self.assertEqual(0, code)
        self.assertIn("The backlog is covered.", out, "the covered-path sentence")

    def test_an_ambiguous_tracking_parse_never_proposes_a_label(self):
        """The changeset is the one place the toolkit proposes a WRITE, and it is fed
        by the least reliable parse in the tree -- so a warned folder's candidate refs
        are reported but withheld from the proposal."""
        plans = {"alpha": "## Tracking\n\nEpic: p937\nItem: xmwb\n"}
        with tempfile.TemporaryDirectory() as tmp, desk(self.README, plans):
            snapshot = write_snapshot(tmp, self.snapshot())
            changeset = Path(tmp) / "changeset.tsv"
            code, out = run_main(
                pd_coverage, ["--snapshot", snapshot, "--changeset", str(changeset)]
            )
            rows = changeset.read_text()
        self.assertEqual(1, code)
        self.assertNotIn("xmwb", rows, "an ambiguous ref must not be proposed a label")
        self.assertIn("ay9p\tlabels", rows, "unambiguous items are still proposed")
        self.assertIn("alpha", out, "the ambiguous folder is named to the user")

    def test_the_ambiguity_is_surfaced_in_the_machine_readable_output(self):
        plans = {"alpha": "## Tracking\n\nEpic: p937\nItem: xmwb\n"}
        with tempfile.TemporaryDirectory() as tmp, desk(self.README, plans):
            code, out = run_main(
                pd_coverage, ["--snapshot", write_snapshot(tmp, self.snapshot()), "--json"]
            )
        payload = json.loads(out)
        self.assertEqual(1, code)
        ambiguous = {row["key"]: row["ambiguous"] for row in payload["unplanned"]}
        self.assertTrue(ambiguous["xmwb"])
        self.assertFalse(ambiguous["ay9p"])
        self.assertEqual(1, len(payload["warnings"]))
        self.assertEqual("alpha", payload["warnings"][0]["plan"])

    def test_json_output_is_machine_parseable(self):
        with tempfile.TemporaryDirectory() as tmp, desk(self.README, {"alpha": "## Tracking\n\n`xmwb`\n"}):
            code, out = run_main(
                pd_coverage, ["--snapshot", write_snapshot(tmp, self.snapshot()), "--json"]
            )
        self.assertEqual(1, code)
        self.assertEqual(3, len(json.loads(out)["unplanned"]))


class ReconcileRefs(unittest.TestCase):
    """The tracker-agnostic ref rule: the first token that is a key in the snapshot."""

    KEYS = {"xmwb", "p937", "ABC-12"}

    def ref(self, text, keys=None):
        return reconcile.find_known_ref(text, keys or self.KEYS)[0]

    def test_a_bare_token_resolves(self):
        self.assertEqual("xmwb", self.ref("| `xmwb` | drafting |"))

    def test_a_qualified_ref_resolves_to_its_key(self):
        """`#` is outside the token class, so `demo#xmwb` splits without extra help."""
        self.assertEqual("xmwb", self.ref("demo#xmwb (epic p937)"))

    def test_a_hyphenated_key_survives_tokenizing(self):
        self.assertEqual("ABC-12", self.ref("see ABC-12 for detail"))

    def test_the_first_known_key_wins_over_later_ones(self):
        self.assertEqual("p937", self.ref("p937 then xmwb"))

    def test_a_token_that_is_not_a_key_is_not_a_ref(self):
        self.assertIsNone(self.ref("tracked on the board, #412"))

    def test_a_date_fragment_cannot_impersonate_a_numeric_key(self):
        """Splitting tokens on `-` would resolve `2026-07-12` to the key `12`."""
        keys = {"12", "412"}
        self.assertEqual("412", self.ref("tracked in the 2026-07-12 ruling, issue #412", keys))

    def test_the_span_points_at_the_matched_token_not_the_first_substring(self):
        """`section.index(ref)` would find the `p937` inside `feat/p937x-thing`."""
        text = "branch feat/p937x-thing\nEpic: p937\n"
        ref, start = reconcile.find_known_ref(text, self.KEYS)
        self.assertEqual("p937", ref)
        self.assertEqual(text.index("Epic: p937") + len("Epic: "), start)


class Reconcile(unittest.TestCase):
    README = (
        "# plans\n\nACTIVE plans (associated with an OPEN item):\n\n"
        "| Plan | Tracker ref(s) | Status |\n| ---- | ---- | ---- |\n"
        "| alpha | `xmwb` | drafting |\n"
        "| beta | `c0ld` | drafting |\n"
        "| gamma | `ay9p` | drafting |\n"
        "| delta | `xmwb` | drafting |\n"
        "| epsilon | `nope1` | drafting |\n"
        "| zeta | - | drafting |\n\n"
        "ARCHIVED (item closed; plan moved):\n\n"
        "| Plan (archived path) | Tracker ref(s) | Why archived |\n| ---- | ---- | ---- |\n"
        "| old-one | `p937` | shipped |\n"
        "| enablement | (no ref) | never tracked |\n"
    )
    PLANS = {
        "alpha": "## Tracking\n\ndemo#xmwb\n",
        "beta": "## Tracking\n\n`c0ld`\n",
        "delta": "## Tracking\n\n`p937`\n",  # README says xmwb -> mismatch
        "epsilon": "## Tracking\n\nnot filled in yet\n",
        "zeta": "## Notes\n\nno tracking section\n",
        "orphan": "## Tracking\n\n`ay9p`\n",  # on disk, no ACTIVE row
    }

    def snapshot(self):
        return make_snapshot(
            make_item("xmwb"),
            make_item("ay9p"),
            make_item("p937", state="open"),
            make_item("c0ld", state="closed"),
        )

    def drift(self):
        with desk(self.README, self.PLANS):
            return reconcile.run(self.snapshot())

    def kinds(self, result, plan):
        return sorted(d["kind"] for d in result["drift"] if d["plan"] == plan)

    def test_every_drift_kind_is_still_detected(self):
        result = self.drift()
        self.assertEqual(["active-but-closed"], self.kinds(result, "beta"))
        self.assertEqual(["row-no-folder"], self.kinds(result, "gamma"))
        self.assertEqual(["body-mismatch"], self.kinds(result, "delta"))
        self.assertEqual(["folder-no-row"], self.kinds(result, "orphan"))
        self.assertEqual(["archived-but-open"], self.kinds(result, "old-one"))
        self.assertEqual(["issue-missing"], self.kinds(result, "epsilon"))
        self.assertEqual(["active-no-issue"], self.kinds(result, "zeta"))

    def test_a_row_that_agrees_with_the_tracker_and_disk_is_ok(self):
        result = self.drift()
        self.assertEqual([], self.kinds(result, "alpha"))
        self.assertEqual(1, len([line for line in result["ok"] if line.startswith("alpha")]))

    def test_an_archived_row_naming_no_ref_is_not_drift(self):
        self.assertEqual([], self.kinds(self.drift(), "enablement"))

    def test_a_plan_naming_no_known_key_warns_without_failing_the_run(self):
        warns = {w["plan"]: w["detail"] for w in self.drift()["warns"]}
        self.assertIn("no known", warns["epsilon"])
        self.assertIn("`## Tracking`", warns["zeta"])

    def test_the_counts_describe_what_was_read(self):
        counts = self.drift()["counts"]
        self.assertEqual({"active": 6, "archived": 2, "folders": 6}, counts)

    def test_a_clean_desk_exits_zero_and_a_dirty_one_exits_one(self):
        readme = (
            "ACTIVE plans:\n\n| Plan | Tracker ref(s) | Status |\n| --- | --- | --- |\n"
            "| alpha | `xmwb` | drafting |\n\nARCHIVED (closed):\n\n"
            "| Plan (archived path) | Tracker ref(s) | Why |\n| --- | --- | --- |\n"
            "| old-one | `c0ld` | shipped |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = write_snapshot(tmp, self.snapshot())
            with desk(readme, {"alpha": "## Tracking\n\n`xmwb`\n"}):
                code, out = run_main(reconcile, ["--snapshot", snapshot])
            self.assertEqual(0, code)
            self.assertIn("No drift", out)
            with desk(self.README, self.PLANS):
                code, out = run_main(reconcile, ["--snapshot", snapshot, "--json"])
        self.assertEqual(1, code)
        self.assertEqual(7, len(json.loads(out)["drift"]))

    def test_a_relation_line_warns_wherever_the_relation_word_sits(self):
        """Each of these resolves to a ref that is NOT the plan's own tracking ref.
        The parse cannot be made right in general, so it must be flagged."""
        sections = {
            "blocked": "## Tracking\n\nBlocked by ay9p; this plan tracks xmwb\n",
            "depends": "## Tracking\n\nDepends on p937. Tracking: xmwb\n",
            "supersedes": "## Tracking\n\nSupersedes c0ld -- now tracked as xmwb\n",
            "parent": "## Tracking\n\nParent: p937  Item: xmwb\n",
            "trailing-epic": "## Tracking\n\npart of the p937 epic, tracks xmwb\n",
            "substring": "## Tracking\n\nbranch feat/p937x-thing\nEpic: p937\n",
        }
        keys = {"xmwb", "ay9p", "p937", "c0ld"}
        for name, section in sections.items():
            with self.subTest(case=name), desk("", {"alpha": section}):
                refs, warn = reconcile.plan_tracking_refs("alpha", keys)
                self.assertIsNotNone(warn, f"{name}: resolved {refs} with no warning")

    def test_an_unambiguous_tracking_section_does_not_warn(self):
        with desk("", {"alpha": "## Tracking\n\nTracked as demo#xmwb\n"}):
            refs, warn = reconcile.plan_tracking_refs("alpha", {"xmwb", "p937"})
        self.assertEqual(["xmwb"], refs)
        self.assertIsNone(warn)

    def test_an_epic_flagged_warning_still_reports_the_ref_it_found(self):
        with desk("", {"alpha": "## Tracking\n\nEpic: p937\nItem: xmwb\n"}):
            refs, warn = reconcile.plan_tracking_refs("alpha", {"xmwb", "p937"})
        self.assertEqual(["p937", "xmwb"], refs, "every known key in the section")
        self.assertIn("p937", warn)

    def test_an_archived_row_naming_an_unknown_ref_is_drift(self):
        readme = (
            "ACTIVE plans:\n\n| Plan | Tracker ref(s) | Status |\n| --- | --- | --- |\n\n"
            "ARCHIVED (closed):\n\n| Plan (archived path) | Tracker ref(s) | Why |\n"
            "| --- | --- | --- |\n| old-one | `gone9` | shipped |\n"
        )
        with desk(readme, {}):
            result = reconcile.run(self.snapshot())
        self.assertEqual(["issue-missing"], [d["kind"] for d in result["drift"]])
        self.assertIn("gone9", result["drift"][0]["detail"])

    def test_the_human_output_prints_every_drift_and_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = write_snapshot(tmp, self.snapshot())
            with desk(self.README, self.PLANS):
                code, out = run_main(reconcile, ["--snapshot", snapshot])
        self.assertEqual(1, code)
        self.assertIn("DRIFT [active-but-closed] beta", out)
        self.assertIn("WARN zeta", out)
        self.assertIn("OK   alpha", out)
        self.assertIn("7 drift item(s)", out)

    def test_a_missing_desk_readme_says_so_instead_of_raising(self):
        """Run from somewhere that is not a plans desk, the answer is a sentence."""
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(reconcile, "README", Path(tmp) / "README.md"):
                with self.assertRaises(SystemExit) as caught:
                    reconcile.parse_readme_rows()
        self.assertIn("README.md", str(caught.exception))
        self.assertIn("plans desk", str(caught.exception))

    def test_the_default_status_is_all_so_archived_rows_can_be_checked(self):
        parser = reconcile.build_parser()
        self.assertEqual("all", parser.parse_args([]).status)


if __name__ == "__main__":
    unittest.main()
