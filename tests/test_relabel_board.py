"""board-triage's relabeler: the map, the delta, and the one gate that lets it write.

Sibling of test_kata_board.py and covered on the same principle — everything between
`kata list --json` and the argv of a mutation is this script's own judgment, so it is
tested directly; the `kata` calls are only checked at the boundary.

What breaks silently if this drifts, in the order it would hurt:

- **The write gate.** A bulk relabeler that writes without `APPLY=1` rewrites every open
  card on a board before anyone has read the plan. So `APPLY` unset, `APPLY=0` and
  `APPLY=` are each asserted to produce ZERO mutating calls, against a stubbed runner —
  reading the source proves nothing about what runs.
- **A mirror.** The GitHub sync owns a mirror's labels and title and re-applies its
  version on the issue's next change, so a relabeled mirror is work that gets reverted.
- **A conflict.** Two `area:` or two `type:` labels on one card is the human's call; a
  script that picks one silently deletes a fact.
- **A wrong target.** `bug -> type:feat` would be invisible in a diff and wrong on 78
  cards, so map targets are validated against the closed vocabulary.
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

import relabel_board as rb  # noqa: E402

SHIPPED_MAP = os.path.join(SKILL, "scripts", "label-map.yaml")

MAP = rb.parse_label_map(
    """
# a comment

bug: type:fix
doc: type:chore
docs: type:chore
"kaneo-status:*": drop
"area:*": keep
"area:-infra": area:infra
"type:fix": keep
blocked: drop
"""
)


def issue(short_id, labels, title="a card", **extra):
    return {"short_id": short_id, "title": title, "labels": list(labels), **extra}


class MapParser(unittest.TestCase):
    def test_comments_blanks_quoted_and_glob_keys_all_parse(self):
        self.assertEqual("type:fix", MAP["bug"])
        self.assertEqual("drop", MAP["kaneo-status:*"], "a quoted glob key keeps its glob")
        self.assertEqual("area:infra", MAP["area:-infra"], "a quoted key loses only its quotes")
        self.assertEqual("keep", MAP["type:fix"])

    def test_a_line_that_is_not_a_mapping_is_refused_not_skipped(self):
        with self.assertRaises(rb.MapError) as caught:
            rb.parse_label_map("bug: type:fix\nnonsense\n")
        self.assertIn("line 2", str(caught.exception))

    def test_a_duplicate_key_is_refused_because_the_loser_would_be_invisible(self):
        with self.assertRaises(rb.MapError) as caught:
            rb.parse_label_map("bug: type:fix\nbug: type:chore\n")
        self.assertIn("bug", str(caught.exception))

    def test_a_target_outside_the_closed_vocabulary_is_refused(self):
        with self.assertRaises(rb.MapError) as caught:
            rb.parse_label_map("bug: type:featt\n")
        self.assertIn("type:featt", str(caught.exception))

    def test_an_unreadable_map_is_an_input_error_not_a_crash(self):
        with self.assertRaises(rb.MapError):
            rb.load_label_map(os.path.join(tempfile.gettempdir(), "no-such-label-map.yaml"))


class Resolve(unittest.TestCase):
    def test_a_glob_covers_the_whole_family(self):
        self.assertEqual("drop", rb.resolve("kaneo-status:anything", MAP))
        self.assertEqual("drop", rb.resolve("kaneo-status:to-do", MAP))

    def test_an_exact_key_beats_a_glob_so_a_malformed_twin_is_corrected(self):
        self.assertEqual("area:infra", rb.resolve("area:-infra", MAP))
        self.assertEqual("keep", rb.resolve("area:repo", MAP), "the family is core by default")

    def test_an_unknown_label_resolves_to_nothing_rather_than_a_guess(self):
        self.assertIsNone(rb.resolve("spike", MAP))


class ShippedMap(unittest.TestCase):
    """The map that ships is data, and data can be malformed. Parse it for real."""

    def setUp(self):
        self.mapping = rb.load_label_map(SHIPPED_MAP)

    def test_it_parses_and_carries_the_rulings_renames(self):
        self.assertEqual("type:fix", self.mapping["bug"])
        self.assertEqual("type:feat", self.mapping["enhancement"])
        self.assertEqual("type:chore", self.mapping["chore"])
        self.assertEqual("decision", self.mapping["decide"])
        self.assertEqual("area:backend", self.mapping["workstream:backend"])

    def test_the_retired_families_resolve_to_drop(self):
        for name in ("kaneo-status:to-do", "priority:high", "effort:l", "priority:-low"):
            with self.subTest(name=name):
                self.assertEqual("drop", rb.resolve(name, self.mapping))

    def test_the_labels_live_evidence_disqualified_are_unmapped_not_renamed(self):
        """Three entries were removed after measurement. Pinned so nobody re-adds them.

        `task` reads as a chore only if you never look at a board: where it is live it is
        the residual "a work item" value, sitting in the same slot as `bug` and `feature`
        and mutually exclusive with them, on cards whose titles are features and fixes.
        `blocked` and `parked` were dropped as duplicates of state kata computes — but the
        measured cards carry no `blocked_by` edge and no `someday`/`scheduled_on`, so the
        label is the only record, not a copy of one.
        """
        for name in ("task", "blocked", "parked"):
            with self.subTest(name=name):
                self.assertIsNone(rb.resolve(name, self.mapping))

    def test_the_states_that_are_genuinely_computed_still_drop(self):
        for name in ("backlog", "triage"):
            with self.subTest(name=name):
                self.assertEqual("drop", rb.resolve(name, self.mapping))

    def test_no_key_is_dead_under_another_key(self):
        """An exact key a glob already answers identically is noise pretending to be intent."""
        globs = [k for k in self.mapping if k.endswith("*")]
        dead = [
            key
            for key in self.mapping
            if not key.endswith("*")
            for glob in globs
            if key.startswith(glob[:-1]) and self.mapping[key] == self.mapping[glob]
        ]
        self.assertEqual([], dead)

    def test_every_core_name_is_present_so_no_board_reports_its_own_vocabulary(self):
        for name in rb.CORE_NAMES:
            with self.subTest(name=name):
                self.assertEqual("keep", rb.resolve(name, self.mapping))
        self.assertEqual("keep", rb.resolve("area:whatever", self.mapping))


class Plan(unittest.TestCase):
    """The delta is pure: a list of issue dicts in, a report out, no `kata` anywhere."""

    def plan(self, issues, **kwargs):
        with mock.patch.object(rb.subprocess, "run", side_effect=AssertionError("no kata")):
            return rb.plan(issues, MAP, **kwargs)

    def test_a_renamed_label_is_removed_and_its_target_added(self):
        report = self.plan([issue("a1", ["bug"])])
        self.assertEqual(
            [{"key": "a1", "add": ["type:fix"], "remove": ["bug"]}], report["relabels"]
        )
        self.assertEqual({}, report["drops"])

    def test_a_card_already_core_produces_nothing(self):
        report = self.plan([issue("a1", ["type:fix", "area:repo", "epic"])])
        self.assertEqual([], report["relabels"])
        self.assertEqual([], report["conflicts"])

    def test_a_dropped_label_is_removed_with_nothing_put_back(self):
        report = self.plan([issue("a1", ["kaneo-status:to-do", "blocked"])])
        self.assertEqual(
            [{"key": "a1", "add": [], "remove": ["blocked", "kaneo-status:to-do"]}],
            report["relabels"],
        )
        self.assertEqual({"blocked": 1, "kaneo-status:to-do": 1}, report["drops"])

    def test_two_spellings_of_one_target_add_it_once(self):
        report = self.plan([issue("a1", ["doc", "docs"])])
        self.assertEqual(
            [{"key": "a1", "add": ["type:chore"], "remove": ["doc", "docs"]}],
            report["relabels"],
        )

    def test_a_target_already_present_is_not_added_again(self):
        report = self.plan([issue("a1", ["bug", "type:fix"])])
        self.assertEqual([{"key": "a1", "add": [], "remove": ["bug"]}], report["relabels"])

    def test_a_mirror_yields_no_operations_and_is_counted(self):
        report = self.plan(
            [issue("a1", ["bug"], metadata={"github_issue": 12}), issue("b2", ["bug"])]
        )
        self.assertEqual(1, report["mirrors_skipped"])
        self.assertEqual(["b2"], [r["key"] for r in report["relabels"]])

    def test_two_areas_are_reported_and_the_card_is_left_alone(self):
        report = self.plan([issue("a1", ["area:repo", "area:-infra", "bug"])])
        self.assertEqual(
            [{"key": "a1", "kind": "area", "labels": ["area:infra", "area:repo"]}],
            report["conflicts"],
        )
        self.assertEqual([], report["relabels"], "no half-fix on a conflicted card")

    def test_two_types_are_reported_and_the_card_is_left_alone(self):
        report = self.plan([issue("a1", ["bug", "docs"])])
        self.assertEqual(
            [{"key": "a1", "kind": "type", "labels": ["type:chore", "type:fix"]}],
            report["conflicts"],
        )
        self.assertEqual([], report["relabels"])

    def test_an_unmapped_label_is_counted_and_never_touched(self):
        report = self.plan([issue("a1", ["spike", "bug"]), issue("b2", ["spike"])])
        self.assertEqual({"spike": 2}, report["unmapped"])
        self.assertEqual([{"key": "a1", "add": ["type:fix"], "remove": ["bug"]}],
                         report["relabels"])

    def test_the_summary_carries_every_class_the_caller_asked_for(self):
        report = self.plan([issue("a1", ["bug"])])
        self.assertLessEqual(
            {"relabels", "drops", "unmapped", "conflicts", "mirrors_skipped"},
            set(report),
        )
        json.dumps(report)


class PrefixStrip(unittest.TestCase):
    CARDS = [issue("a1", [], title="skills: rewrite the thing"), issue("b2", [], title="plain")]

    def test_without_an_area_list_it_promotes_nothing_and_reports_everything(self):
        report = rb.plan(self.CARDS, MAP, strip_prefixes=True)
        self.assertEqual([], report["relabels"])
        self.assertEqual(
            [{"key": "a1", "prefix": "skills", "promoted": False}], report["prefixes"]
        )

    def test_a_prefix_in_the_area_list_moves_onto_the_card_as_a_label(self):
        report = rb.plan(self.CARDS, MAP, strip_prefixes=True, areas=["skills"])
        self.assertEqual(
            [{"key": "a1", "add": ["area:skills"], "remove": [],
              "title": "rewrite the thing"}],
            report["relabels"],
        )
        self.assertEqual([{"key": "a1", "prefix": "skills", "promoted": True}],
                         report["prefixes"])

    def test_an_area_list_entry_may_be_written_either_way(self):
        report = rb.plan(self.CARDS, MAP, strip_prefixes=True, areas=["area:skills"])
        self.assertEqual(["area:skills"], report["relabels"][0]["add"])

    def test_a_mirrors_title_is_the_syncs_to_own_so_it_is_not_stripped(self):
        cards = [issue("a1", [], title="skills: x", metadata={"github_issue": 3})]
        report = rb.plan(cards, MAP, strip_prefixes=True, areas=["skills"])
        self.assertEqual([], report["relabels"])
        self.assertEqual([], report["prefixes"])

    def test_promoting_into_an_existing_different_area_is_a_conflict_not_a_write(self):
        cards = [issue("a1", ["area:repo"], title="skills: x")]
        report = rb.plan(cards, MAP, strip_prefixes=True, areas=["skills"])
        self.assertEqual([], report["relabels"])
        self.assertEqual("area", report["conflicts"][0]["kind"])

    def test_off_by_default(self):
        self.assertEqual([], rb.plan(self.CARDS, MAP)["relabels"])
        self.assertNotIn("prefixes", rb.plan(self.CARDS, MAP))

    def test_a_stripped_title_that_would_read_as_an_option_is_refused(self):
        """`kata edit --title --force ...` is an argv injection, not a title."""
        cards = [issue("a1", [], title="skills: --force the thing")]
        report = rb.plan(cards, MAP, strip_prefixes=True, areas=["skills"])
        self.assertEqual([], report["relabels"])
        self.assertFalse(report["prefixes"][0]["promoted"])
        self.assertIn("-", report["prefixes"][0]["reason"])

    def test_a_prefix_that_is_the_whole_title_is_refused_rather_than_blanked(self):
        cards = [issue("a1", [], title="skills:   ")]
        report = rb.plan(cards, MAP, strip_prefixes=True, areas=["skills"])
        self.assertEqual([], report["relabels"])
        self.assertFalse(report["prefixes"][0]["promoted"])


class Operations(unittest.TestCase):
    def test_a_record_becomes_kata_argv_in_a_stable_order(self):
        record = {"key": "a1", "add": ["area:skills"], "remove": ["bug"], "title": "x"}
        self.assertEqual(
            [["label", "rm", "a1", "bug"],
             ["label", "add", "a1", "area:skills"],
             ["edit", "a1", "--title", "x"]],
            [argv for argv, _ in rb.operations([record])],
        )


class WriteGate(unittest.TestCase):
    """`APPLY=1` is the only thing that writes, asserted against a stubbed runner."""

    ISSUES = [issue("a1", ["bug", "kaneo-status:to-do"])]

    def run_main(self, argv, apply_value, issues=None):
        writes = []
        issues = self.ISSUES if issues is None else issues

        def run(cmd, **_):
            if "list" in cmd:
                return mock.Mock(
                    returncode=0, stdout=json.dumps({"issues": issues}), stderr=""
                )
            writes.append(list(cmd))
            return mock.Mock(returncode=0, stdout="", stderr="")

        env = dict(os.environ)
        env.pop("APPLY", None)
        if apply_value is not None:
            env["APPLY"] = apply_value
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(rb.subprocess, "run", run), \
                contextlib.redirect_stdout(out):
            code = rb.main(argv)
        return code, out.getvalue(), writes

    def test_no_apply_value_writes_nothing(self):
        for value in (None, "0", "", "  ", "no", "false"):
            with self.subTest(apply=value):
                _, out, writes = self.run_main(["--project", "demo"], value)
                self.assertEqual([], writes, f"APPLY={value!r} must not mutate the board")
                self.assertIn("dry run", out.lower())

    def test_apply_one_is_what_writes(self):
        code, out, writes = self.run_main(["--project", "demo"], "1")
        self.assertEqual(
            [["kata", "label", "rm", "a1", "bug", "--project", "demo", "--agent"],
             ["kata", "label", "rm", "a1", "kaneo-status:to-do", "--project", "demo",
              "--agent"],
             ["kata", "label", "add", "a1", "type:fix", "--project", "demo", "--agent"]],
            writes,
        )
        self.assertEqual(0, code, out)

    def test_the_affirmative_set_is_exactly_what_the_docstring_claims(self):
        """Pinned in both directions: the docstring said `APPLY=1` and four other values
        wrote too. A gate whose documented set is smaller than its real set is a lie that
        reads as safety."""
        for value in ("1", "true", "TRUE", "yes", "Yes", " 1 "):
            with self.subTest(apply=value):
                self.assertTrue(rb.apply_enabled({"APPLY": value}))
                _, _, writes = self.run_main(["--project", "demo"], value)
                self.assertTrue(writes, f"APPLY={value!r} is affirmative and must write")
        for value in ("", "0", "  ", "no", "false", "2", "01", "1x", "yes please"):
            with self.subTest(apply=value):
                self.assertFalse(rb.apply_enabled({"APPLY": value}))
        self.assertFalse(rb.apply_enabled({}), "unset is a dry run")

    def test_a_conflicted_card_is_never_written_even_under_apply(self):
        code, out, writes = self.run_main(
            ["--project", "demo"], "1", issues=[issue("z9", ["bug", "docs"])]
        )
        self.assertEqual([], writes)
        self.assertEqual(1, code, "an unresolved conflict is a finding")


class PartialApply(unittest.TestCase):
    """A bulk write that dies partway is the worst state this script can leave behind.

    `kata` mutates one label per call, so an abort halfway through a card leaves it with the
    old label already removed and the new one never added — no type at all. That has to be
    (a) visible, so the operator knows exactly what landed, and (b) a DIFFERENT exit code
    from an ordinary finding, or a wrapper cannot tell "there is work to review" from "the
    board is half-rewritten".
    """

    def run_apply(self, fail_on):
        calls = {"n": 0}
        writes = []

        def run(cmd, **_):
            if "list" in cmd:
                return mock.Mock(
                    returncode=0,
                    stdout=json.dumps({"issues": [issue("a1", ["bug", "kaneo-status:to-do"])]}),
                    stderr="",
                )
            calls["n"] += 1
            if calls["n"] == fail_on:
                return mock.Mock(returncode=1, stdout="", stderr="daemon said no")
            writes.append(list(cmd))
            return mock.Mock(returncode=0, stdout="", stderr="")

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, {**os.environ, "APPLY": "1"}), \
                mock.patch.object(rb.subprocess, "run", run), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rb.main(["--project", "demo"])
        return code, out.getvalue() + err.getvalue(), writes

    def test_an_abort_has_its_own_exit_code_and_names_what_landed(self):
        code, text, writes = self.run_apply(fail_on=3)
        self.assertEqual(3, code, text)
        self.assertEqual(2, len(writes), "the two ops before the failure did land")
        self.assertIn("daemon said no", text, "the reason survives")
        self.assertIn("a1 -bug", text, "an operator has to see what already applied")
        self.assertIn("+type:fix", text, "and what did not")

    def test_an_abort_on_the_first_operation_still_reports_cleanly(self):
        code, text, writes = self.run_apply(fail_on=1)
        self.assertEqual(3, code)
        self.assertEqual([], writes)
        self.assertIn("0 operation(s)", text)


class ExitCodes(unittest.TestCase):
    """0 nothing to do, 1 a finding or a pending change, 2 an input that cannot be read."""

    def run_main(self, argv, issues):
        def run(cmd, **_):
            return mock.Mock(returncode=0, stdout=json.dumps({"issues": issues}), stderr="")

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(rb.subprocess, "run", run), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rb.main(argv)
        return code, out.getvalue() + err.getvalue()

    def test_a_clean_board_is_zero(self):
        code, _ = self.run_main(["--project", "d"], [issue("a1", ["type:fix", "area:repo"])])
        self.assertEqual(0, code)

    def test_a_pending_change_is_one(self):
        code, _ = self.run_main(["--project", "d"], [issue("a1", ["bug"])])
        self.assertEqual(1, code)

    def test_an_unmapped_label_alone_is_a_finding(self):
        code, _ = self.run_main(["--project", "d"], [issue("a1", ["spike"])])
        self.assertEqual(1, code)

    def test_a_board_that_cannot_be_read_is_two_like_any_other_unreadable_input(self):
        def run(cmd, **_):
            return mock.Mock(returncode=1, stdout="", stderr="no such project")

        err = io.StringIO()
        with mock.patch.object(rb.subprocess, "run", run), contextlib.redirect_stderr(err):
            code = rb.main(["--project", "nope"])
        self.assertEqual(2, code)
        self.assertIn("no such project", err.getvalue())

    def test_an_unreadable_map_is_two_not_a_traceback(self):
        code, text = self.run_main(
            ["--project", "d", "--map", "/nonexistent/label-map.yaml"], []
        )
        self.assertEqual(2, code)
        self.assertIn("label-map.yaml", text)


class Cli(unittest.TestCase):
    def test_json_carries_the_five_classes_the_caller_needs(self):
        def run(cmd, **_):
            return mock.Mock(
                returncode=0, stdout=json.dumps({"issues": [issue("a1", ["bug"])]}), stderr=""
            )

        out = io.StringIO()
        with mock.patch.object(rb.subprocess, "run", run), contextlib.redirect_stdout(out):
            rb.main(["--project", "demo", "--json"])
        payload = json.loads(out.getvalue())
        self.assertEqual("demo", payload["project"])
        self.assertLessEqual(
            {"relabels", "drops", "unmapped", "conflicts", "mirrors_skipped"}, set(payload)
        )

    def test_a_missing_project_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as caught:
            with open(os.devnull, "w") as devnull:
                stderr, sys.stderr = sys.stderr, devnull
                try:
                    rb.main([])
                finally:
                    sys.stderr = stderr
        self.assertEqual(2, caught.exception.code)

    def test_help_needs_no_kata_binary(self):
        with self.assertRaises(SystemExit) as caught:
            with open(os.devnull, "w") as devnull:
                stdout, sys.stdout = sys.stdout, devnull
                try:
                    rb.main(["--help"])
                finally:
                    sys.stdout = stdout
        self.assertEqual(0, caught.exception.code)


if __name__ == "__main__":
    unittest.main()
