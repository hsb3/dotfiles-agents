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

    def test_the_type_field_becomes_a_label_and_area_labels_are_dropped(self):
        # `docs` is the task's type and survives; `backend` is a per-repo area label and
        # does not, because the central vocabulary is closed. See CentralVocabularyTests.
        path = write(self.root, "tasks", "task-004.md", TASK)
        self.assertEqual(ob.parse_task_file(path, "TASK")["labels"], ["docs"])

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
        self.assertIn("DECISION", ob.parse_task_file(path, "DECISION")["doc_labels"])

    def test_tasks_do_not_get_the_decision_label(self):
        root = tempfile.mkdtemp()
        path = write(root, "tasks", "task-009.md", BARE)
        self.assertNotIn("DECISION", ob.parse_task_file(path, "TASK")["doc_labels"])


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


DOC = """---
id: doc-002
title: Backend-gap register
type: specification
---

# Backend-gap register

Living doc.
"""

DOC_OTHER = DOC.replace("type: specification", "type: other")


class DocumentLabelTests(unittest.TestCase):
    """Kaneo has no document type, so a label is the only thing that can carry one."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_docs_are_read_at_all(self):
        # They were silently skipped at first: backlog/docs is a fourth source, and
        # dropping it loses whole documents without a word.
        write(self.root, "docs", "doc-002.md", DOC)
        self.assertEqual([r["kind"] for r in ob.read_backlog(self.root)], ["DOC"])

    def test_every_document_carries_the_umbrella_label(self):
        write(self.root, "docs", "doc-002.md", DOC)
        write(self.root, "decisions", "decision-1.md", BARE)
        for record in ob.read_backlog(self.root):
            self.assertIn(ob.DOC_LABEL, record["doc_labels"], record["kind"])

    def test_a_known_backlog_type_maps_to_a_kind(self):
        write(self.root, "docs", "doc-002.md", DOC)
        self.assertIn("SPEC", ob.read_backlog(self.root)[0]["doc_labels"])

    def test_type_other_gets_no_kind_rather_than_a_guessed_one(self):
        # `other` is the majority value in real repos and carries no information.
        write(self.root, "docs", "doc-002.md", DOC_OTHER)
        record = ob.read_backlog(self.root)[0]
        self.assertEqual(set(record["doc_labels"]) & set(ob.DOC_KINDS), set())
        self.assertIn(ob.DOC_LABEL, record["doc_labels"])

    def test_decisions_carry_both_the_umbrella_and_their_kind(self):
        write(self.root, "decisions", "decision-1.md", BARE)
        labels = ob.read_backlog(self.root)[0]["doc_labels"]
        self.assertIn(ob.DOC_LABEL, labels)
        self.assertIn("DECISION", labels)

    def test_tasks_are_not_labelled_as_documents(self):
        write(self.root, "tasks", "task-009.md", BARE)
        self.assertNotIn(ob.DOC_LABEL, ob.read_backlog(self.root)[0]["doc_labels"])

    def test_the_kind_vocabulary_is_closed_and_every_kind_has_a_colour(self):
        self.assertTrue(all(c.startswith("#") for c in ob.DOC_KINDS.values()))
        self.assertTrue(set(ob.DOC_TYPE_MAP.values()) <= set(ob.DOC_KINDS))


    def test_a_docs_raw_type_does_not_leak_in_as_a_label(self):
        # `type: other` became a literal `other` label, and `type: specification` sat
        # next to the `spec` it maps to. Both are junk on a board you filter by label.
        write(self.root, "docs", "a.md", DOC)
        write(self.root, "docs", "b.md", DOC_OTHER)
        recs = ob.read_backlog(self.root)
        seen = {l for r in recs for l in r["labels"]} | {l for r in recs for l in r["doc_labels"]}
        self.assertNotIn("other", seen)
        self.assertNotIn("specification", seen)
        self.assertIn("SPEC", seen)

    def test_a_tasks_type_is_still_a_label(self):
        write(self.root, "tasks", "task-004.md", TASK)
        self.assertIn("docs", ob.read_backlog(self.root)[0]["labels"])

    def test_documents_route_to_their_lane_not_a_workflow_one(self):
        lanes = {"DRAFT": "to-do", "DECISION": "documents", "DOC": "documents"}
        record = {"kind": "DOC", "status": "", "body": "b"}
        self.assertEqual(ob.lane_for(record, {}, lanes), "documents")


class LabelCasingTests(unittest.TestCase):
    """The workspace label endpoint returns one row per attachment, and real workspaces
    already hold mixed casing (`RESEARCH` and `handoff` side by side). Matching
    case-sensitively seeds a second label that reads as the same one and filters as two."""

    ROWS = [
        {"name": "HANDOFF", "color": "purple"},
        {"name": "HANDOFF", "color": "purple"},
        {"name": "infra", "color": "#3b82f6"},
    ]

    def test_attach_reuses_existing_casing_and_colour(self):
        # HANDOFF is a real workspace label the plugin does not own, so the board's
        # casing and colour win. (An owned document label goes the other way — see
        # UppercaseVocabularyTests.)
        sent = []
        original = ob.api
        ob.api = lambda method, path, body=None: sent.append(body)
        try:
            ob.attach_labels("ws", [({"labels": ["handoff"]}, "t1")], self.ROWS)
        finally:
            ob.api = original
        self.assertEqual(sent[0]["name"], "HANDOFF")
        self.assertEqual(sent[0]["color"], "purple")

    def test_an_unknown_label_keeps_its_own_name(self):
        sent = []
        original = ob.api
        ob.api = lambda method, path, body=None: sent.append(body)
        try:
            ob.attach_labels("ws", [({"labels": ["brand-new"]}, "t1")], self.ROWS)
        finally:
            ob.api = original
        self.assertEqual(sent[0]["name"], "brand-new")


class SourceIdTests(unittest.TestCase):
    """adopt only works if a hand-migrated title still names its source file."""

    def test_recovers_ids_from_real_board_titles(self):
        for title, want in [
            ("TASK-083 \u2014 New account never receives its confirmation email", "TASK-083"),
            ("TASK-013.05: Prove hard-purge workspace reprovision", "TASK-013.05"),
            ("decision-002: Full cutover", "decision-002"),
            ("DRAFT-012: v2 comment reactions", "DRAFT-012"),
        ]:
            with self.subTest(title=title):
                self.assertEqual(ob.SOURCE_ID.search(title).group(0), want)

    def test_a_title_with_no_source_id_is_left_alone(self):
        self.assertIsNone(ob.SOURCE_ID.search("Meta: how this migration was done"))


class UppercaseVocabularyTests(unittest.TestCase):
    """Casing is the readability rule: UPPERCASE = what kind of document, lowercase =
    what kind of work. So the document vocabulary's casing is owned here and overrides
    whatever is on the board, while work labels keep the board's casing."""

    def test_the_whole_document_vocabulary_is_uppercase(self):
        for name in {ob.DOC_LABEL, *ob.DOC_KINDS, *ob.DOC_TYPE_MAP.values()}:
            self.assertEqual(name, name.upper(), name)

    def test_a_document_label_is_forced_to_its_declared_casing(self):
        sent = []
        original = ob.api
        ob.api = lambda method, path, body=None: sent.append(body)
        try:
            ob.attach_labels("ws", [({"labels": [], "doc_labels": ["DECISION"]}, "t1")],
                             [{"name": "decision", "color": "#111111"}])
        finally:
            ob.api = original
        self.assertEqual(sent[0]["name"], "DECISION")

    def test_an_owned_label_takes_the_declared_colour_too(self):
        sent = []
        original = ob.api
        ob.api = lambda method, path, body=None: sent.append(body)
        try:
            ob.attach_labels("ws", [({"labels": [], "doc_labels": ["RESEARCH"]}, "t1")],
                             [{"name": "research", "color": "pink"}])
        finally:
            ob.api = original
        self.assertEqual(sent[0]["name"], "RESEARCH")
        self.assertEqual(sent[0]["color"], ob.DOC_KINDS["RESEARCH"])


class LayoutTests(unittest.TestCase):
    """Backlog.md layouts differ per repo, silently. One keeps finished work in tasks/
    with status Done; another moves it to completed/; a third nests archive/tasks/."""

    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_completed_counts_as_tasks(self):
        write(self.root, "completed", "task-029.md", BARE)
        self.assertEqual([r["kind"] for r in ob.read_backlog(self.root)], ["TASK"])

    def test_archive_is_excluded_by_default(self):
        # The owner filed it out of view on purpose; resurrecting it silently is wrong.
        write(self.root, "archive/tasks", "task-001.md", BARE)
        self.assertEqual(ob.read_backlog(self.root), [])

    def test_archive_is_read_recursively_when_asked(self):
        write(self.root, "archive/tasks", "task-001.md", BARE)
        self.assertEqual(len(ob.read_backlog(self.root, include_archive=True)), 1)

    def test_an_unclaimed_folder_is_reported_not_swept_in(self):
        write(self.root, "templates", "a.md", BARE)
        self.assertEqual(ob.unhandled_folders(self.root), {"templates": 1})

    def test_archive_is_reported_while_excluded(self):
        write(self.root, "archive/tasks", "task-001.md", BARE)
        self.assertEqual(ob.unhandled_folders(self.root), {"archive": 1})

    def test_archive_stops_being_reported_once_included(self):
        write(self.root, "archive/tasks", "task-001.md", BARE)
        self.assertEqual(ob.unhandled_folders(self.root, include_archive=True), {})

    def test_known_folders_are_never_reported_as_unhandled(self):
        write(self.root, "tasks", "task-004.md", TASK)
        write(self.root, "completed", "task-029.md", BARE)
        self.assertEqual(ob.unhandled_folders(self.root), {})


class LaneResolutionTests(unittest.TestCase):
    """A column created as "Documents" and renamed keeps slug `documents`; one created as
    "Document" gets `document`. Two boards meant to match then disagree on the value the
    API wants, and only the slug works."""

    RENAMED = [{"slug": "documents", "name": "Document"}]
    FRESH = [{"slug": "document", "name": "Document"}]

    def test_matches_a_renamed_column_by_display_name(self):
        self.assertEqual(ob.resolve_lane("document", self.RENAMED), "documents")

    def test_matches_a_fresh_column_by_slug(self):
        self.assertEqual(ob.resolve_lane("document", self.FRESH), "document")

    def test_always_returns_the_slug_the_api_wants(self):
        self.assertEqual(ob.resolve_lane("Document", self.RENAMED), "documents")

    def test_an_absent_lane_resolves_to_none_rather_than_a_guess(self):
        self.assertIsNone(ob.resolve_lane("document", [{"slug": "to-do", "name": "To Do"}]))


class SourceLabelCollisionTests(unittest.TestCase):
    """api-agents uses `decision` and `research` as ORDINARY task labels. Forcing those
    into the document vocabulary would relabel plain tasks as documents, so the casing
    rule applies only to labels this script added."""

    def _sent(self, record):
        sent = []
        original = ob.api
        ob.api = lambda method, path, body=None: sent.append(body)
        try:
            ob.attach_labels("ws", [(record, "t1")], [])
        finally:
            ob.api = original
        return [s["name"] for s in sent]

    def test_a_task_label_named_decision_is_not_promoted_to_a_document_type(self):
        got = self._sent({"labels": ["decision"], "doc_labels": []})
        self.assertEqual(got, ["decision"])

    def test_a_task_label_named_research_keeps_its_case(self):
        got = self._sent({"labels": ["research"], "doc_labels": []})
        self.assertEqual(got, ["research"])

    def test_a_real_decision_document_still_gets_the_uppercase_label(self):
        got = self._sent({"labels": [], "doc_labels": ["DECISION", "DOC"]})
        self.assertEqual(sorted(got), ["DECISION", "DOC"])

    def test_both_sets_are_attached_when_a_document_also_has_its_own_labels(self):
        got = self._sent({"labels": ["backend"], "doc_labels": ["DOC"]})
        self.assertEqual(sorted(got), ["DOC", "backend"])


class CentralVocabularyTests(unittest.TestCase):
    """A central board whose label list is the union of every repo's local habits filters
    worse than one with a closed set. api-agents alone carried 52 (`area: agent`,
    `size/L`, `platform-opportunity`)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        ob.KEEP_SOURCE_LABELS[0] = False

    def tearDown(self):
        ob.KEEP_SOURCE_LABELS[0] = False

    def _labels(self, frontmatter_labels):
        body = "---\nid: TASK-1\ntitle: t\nstatus: To Do\nlabels:\n"
        body += "".join(f"  - {l}\n" for l in frontmatter_labels) + "---\n\nbody\n"
        write(self.root, "tasks", "task-1.md", body)
        return ob.read_backlog(self.root)[0]["labels"]

    def test_off_vocabulary_labels_are_dropped(self):
        self.assertEqual(self._labels(["area: agent", "size/L", "backend"]), [])

    def test_vocabulary_labels_survive(self):
        self.assertEqual(self._labels(["bug", "chore"]), ["bug", "chore"])

    def test_synonyms_fold_into_the_closed_set(self):
        self.assertEqual(self._labels(["enhancement"]), ["feature"])
        self.assertEqual(self._labels(["documentation"]), ["docs"])
        self.assertEqual(self._labels(["testing"]), ["test"])

    def test_casing_is_normalised(self):
        self.assertEqual(self._labels(["BUG"]), ["bug"])

    def test_keep_source_labels_opts_out(self):
        ob.KEEP_SOURCE_LABELS[0] = True
        self.assertEqual(self._labels(["area: agent"]), ["area: agent"])

    def test_no_alias_points_outside_the_closed_set(self):
        self.assertTrue(set(ob.WORK_ALIASES.values()) <= set(ob.WORK_TYPES))

    def test_the_two_axes_never_collide(self):
        upper = {ob.DOC_LABEL, *ob.DOC_KINDS}
        self.assertEqual({u.lower() for u in upper} & set(ob.WORK_TYPES), set())


if __name__ == "__main__":
    unittest.main()
