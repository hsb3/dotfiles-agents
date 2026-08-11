"""The onboarder's offline half: parsing Backlog.md and resolving statuses to lanes.

The network half is deliberately not mocked. What can actually go wrong there is the
shape of a live Kaneo response, and a mock asserts only that the author's guess about
that shape is self-consistent. These tests cover the parts that are wrong or right on
their own: the frontmatter subset, section extraction, and — the one that matters — that
a status is never mapped to a lane the target board does not have.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "primitives-core",
        "skills",
        "kaneo",
        "scripts",
    ),
)

import onboard_repo as ob  # noqa: E402

TASK = """---
id: TASK-004
title: Refresh the overview diagram
status: Done
assignee: []
labels:
  - docs
  - backend
dependencies:
  - TASK-003
priority: high
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The diagram predates the current schema.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria

<!-- SECTION:ACCEPTANCE_CRITERIA:BEGIN -->
- [x] Regenerated
<!-- SECTION:ACCEPTANCE_CRITERIA:END -->
"""

BARE = """---
id: TASK-009
title: No marked sections here
status: To Do
priority: nonsense
---

Just a plain body, written by hand.
"""


def write(root, folder, name, text):
    directory = os.path.join(root, "backlog", folder)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class FrontmatterTests(unittest.TestCase):
    def test_scalars_inline_lists_and_block_lists(self):
        fields = ob.parse_frontmatter(
            "id: TASK-1\nlabels: []\ntags: [a, b]\ndeps:\n  - TASK-2\n  - TASK-3\n"
        )
        self.assertEqual(fields["id"], "TASK-1")
        self.assertEqual(fields["labels"], [])
        self.assertEqual(fields["tags"], ["a", "b"])
        self.assertEqual(fields["deps"], ["TASK-2", "TASK-3"])

    def test_quoted_dates_keep_no_quotes(self):
        self.assertEqual(
            ob.parse_frontmatter("created_date: '2026-07-28 11:58'\n")["created_date"],
            "2026-07-28 11:58",
        )


class TaskFileTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_marked_sections_are_carried_in_order(self):
        path = write(self.root, "tasks", "task-004.md", TASK)
        record = ob.parse_task_file(path, "TASK")
        self.assertEqual(record["source_id"], "TASK-004")
        self.assertEqual(record["priority"], "high")
        self.assertIn("predates the current schema", record["body"])
        self.assertIn("Regenerated", record["body"])
        self.assertLess(
            record["body"].index("predates"), record["body"].index("Regenerated"),
            "sections must keep their declared order",
        )

    def test_the_type_field_becomes_a_label_alongside_declared_labels(self):
        path = write(self.root, "tasks", "task-004.md", TASK)
        self.assertEqual(ob.parse_task_file(path, "TASK")["labels"], ["backend", "docs"])

    def test_a_file_with_no_markers_keeps_its_whole_body(self):
        # Losing the body of a hand-written card is silent data loss, so the fallback
        # matters more than the happy path.
        path = write(self.root, "tasks", "task-009.md", BARE)
        record = ob.parse_task_file(path, "TASK")
        self.assertIn("Just a plain body", record["body"])

    def test_an_unknown_priority_falls_back_rather_than_failing_the_import(self):
        path = write(self.root, "tasks", "task-009.md", BARE)
        self.assertEqual(ob.parse_task_file(path, "TASK")["priority"], "medium")

    def test_a_file_without_frontmatter_is_skipped_not_crashed_on(self):
        path = write(self.root, "tasks", "readme.md", "# not a task\n")
        self.assertIsNone(ob.parse_task_file(path, "TASK"))

    def test_read_backlog_collects_every_kind(self):
        write(self.root, "tasks", "task-004.md", TASK)
        write(self.root, "drafts", "draft-001.md", BARE)
        write(self.root, "decisions", "decision-1.md", BARE)
        kinds = sorted(r["kind"] for r in ob.read_backlog(self.root))
        self.assertEqual(kinds, ["DECISION", "DRAFT", "TASK"])

    def test_a_repo_with_no_backlog_reads_as_greenfield(self):
        self.assertEqual(ob.read_backlog(tempfile.mkdtemp()), [])


class StatusResolutionTests(unittest.TestCase):
    """The check that keeps work out of lanes the target board does not have."""

    COLUMNS = [
        {"slug": "to-do", "name": "To Do", "position": 0},
        {"slug": "in-progress", "name": "In Progress", "position": 1},
        {"slug": "documents", "name": "Documents", "position": 2},
    ]

    def _records(self, *statuses):
        return [{"status": s} for s in statuses]

    def test_matches_on_slug_and_on_display_name(self):
        mapping, unmapped = ob.resolve_statuses(
            self._records("To Do", "in-progress"), self.COLUMNS
        )
        self.assertEqual(mapping, {"To Do": "to-do", "in-progress": "in-progress"})
        self.assertEqual(unmapped, [])

    def test_a_status_with_no_lane_is_reported_never_guessed(self):
        # The failure this prevents: "Up Next" quietly landing in whichever lane sorts
        # first, which looks like a successful import.
        mapping, unmapped = ob.resolve_statuses(self._records("Up Next"), self.COLUMNS)
        self.assertEqual(unmapped, ["Up Next"])
        self.assertNotIn("Up Next", mapping)

    def test_a_board_specific_lane_resolves(self):
        # `documents` exists on one real board and no fixed vocabulary would predict it.
        mapping, _ = ob.resolve_statuses(self._records("Documents"), self.COLUMNS)
        self.assertEqual(mapping["Documents"], "documents")

    def test_blank_statuses_are_not_mapped(self):
        mapping, unmapped = ob.resolve_statuses(self._records("", ""), self.COLUMNS)
        self.assertEqual((mapping, unmapped), ({}, []))


class SlugTests(unittest.TestCase):
    def test_punctuation_and_case_collapse_to_one_hyphen(self):
        self.assertEqual(ob.slugify("In Review!"), "in-review")
        self.assertEqual(ob.slugify("  Up   Next  "), "up-next")


class KindRoutingTests(unittest.TestCase):
    """Drafts and decisions must never reach lane resolution.

    Real backlogs hold decision statuses like `Accepted (corrected 2026-07-29)` and
    `superseded by decision-002`. Routing those through lane resolution asks the board to
    grow one column per historical footnote.
    """

    def _records(self):
        return [
            {"kind": "TASK", "status": "To Do", "body": "b"},
            {"kind": "DECISION", "status": "Accepted (corrected 2026-07-29)", "body": "b"},
            {"kind": "DRAFT", "status": "Draft", "body": "b"},
        ]

    def test_only_tasks_reach_lane_resolution(self):
        kinds = {r["kind"] for r in ob.workflow_records(self._records())}
        self.assertEqual(kinds, {"TASK"})

    def test_free_text_decision_statuses_never_become_lanes(self):
        _, unmapped = ob.resolve_statuses(
            ob.workflow_records(self._records()),
            [{"slug": "to-do", "name": "To Do"}],
        )
        self.assertEqual(unmapped, [])

    def test_non_task_kinds_take_their_fixed_lane(self):
        lanes = {"DRAFT": "to-do", "DECISION": "documents"}
        mapping = {"To Do": "to-do"}
        got = [ob.lane_for(r, mapping, lanes) for r in self._records()]
        self.assertEqual(got, ["to-do", "documents", "to-do"])

    def test_a_dropped_status_is_preserved_in_the_body(self):
        record = {"kind": "DECISION", "status": "superseded by decision-002", "body": "why"}
        body = ob.body_for(record)
        self.assertIn("superseded by decision-002", body)
        self.assertIn("why", body)

    def test_task_bodies_are_left_alone(self):
        record = {"kind": "TASK", "status": "Done", "body": "why"}
        self.assertEqual(ob.body_for(record), "why")


class DecisionLabelTests(unittest.TestCase):
    def test_decisions_are_labelled_so_they_stay_filterable(self):
        root = tempfile.mkdtemp()
        path = write(root, "decisions", "decision-1.md", BARE)
        self.assertIn("decision", ob.parse_task_file(path, "DECISION")["labels"])

    def test_tasks_do_not_get_the_decision_label(self):
        root = tempfile.mkdtemp()
        path = write(root, "tasks", "task-009.md", BARE)
        self.assertNotIn("decision", ob.parse_task_file(path, "TASK")["labels"])


class BlockScalarTests(unittest.TestCase):
    """Backlog.md folds any long title. In one real repo that is 100 of 192 task files,
    so mishandling it silently retitles most of an import to `>-`."""

    def test_folded_scalar_joins_with_spaces(self):
        fields = ob.parse_frontmatter(
            "title: >-\n  Frontend contract: author the openapi.json\n  and close gaps\n"
            "status: Done\n"
        )
        self.assertEqual(
            fields["title"], "Frontend contract: author the openapi.json and close gaps"
        )
        self.assertEqual(fields["status"], "Done", "the next key must still be read")

    def test_literal_scalar_keeps_line_breaks(self):
        fields = ob.parse_frontmatter("body: |\n  one\n  two\n")
        self.assertEqual(fields["body"], "one\ntwo")

    def test_a_hyphen_inside_a_folded_scalar_is_not_a_list_item(self):
        fields = ob.parse_frontmatter("title: >-\n  fix the - dash handling\nstatus: Done\n")
        self.assertEqual(fields["title"], "fix the - dash handling")

    def test_a_block_list_after_a_folded_scalar_still_parses(self):
        fields = ob.parse_frontmatter(
            "title: >-\n  a long folded title\nlabels:\n  - docs\n  - backend\n"
        )
        self.assertEqual(fields["labels"], ["docs", "backend"])


if __name__ == "__main__":
    unittest.main()
