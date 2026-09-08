"""board-triage's split into a backend-agnostic core plus per-backend adapters.

Two invariants and one adapter's logic. The invariants are the split itself: if the
rubric page starts naming a backend again, or an adapter stops declaring where the
rubric's outputs land, the skill has quietly re-fused and adding a third backend means
editing the procedure again. Both failures are silent — an agent reading a
GitHub-flavoured procedure against a Kaneo board just produces a wrong changeset.

The Kaneo half is covered where it can be wrong on its own: what the snapshot looks
like, what a changeset row resolves to, and that a cell already at its target value
produces no write. The network is not mocked — a mock there asserts only that the
author's guess about Kaneo's response shape is self-consistent. The one exception is
KaneoApplyReadBack, which fakes the transport to pin apply's own control flow; its
docstring says why that is not the same bet.
"""

import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "board-triage")
ADAPTERS = os.path.join(SKILL, "references", "adapters")

sys.path.insert(0, os.path.join(SKILL, "scripts"))

import kaneo_board as kb  # noqa: E402

# Loaded by path (not sys.path import) so this file's fixture module name can't collide
# with test_github_projects_board.py's own load of the same script.
_gpb_spec = importlib.util.spec_from_file_location(
    "github_projects_board_stderr_pin", os.path.join(SKILL, "scripts", "github_projects_board.py")
)
gpb = importlib.util.module_from_spec(_gpb_spec)
_gpb_spec.loader.exec_module(gpb)

# Naming any of these on the rubric page means the judgment has been re-coupled to one
# board. Lowercased substring match, so "gh " catches the CLI without catching "high".
BACKEND_TOKENS = (
    "github",
    "graphql",
    "projects (v2)",
    "project (v2)",
    "kaneo",
    "gh ",
    "jira",
    "linear",
)

# Every adapter answers the same four questions, or the core cannot rely on it.
REQUIRED_ADAPTER_SECTIONS = ("## Key", "## Export", "## Apply", "## Field map")


def read(path):
    with open(path) as handle:
        return handle.read()


class BackendAgnosticCore(unittest.TestCase):
    """AC #1/#3: the rubric and procedure name no backend, so a new one costs an adapter."""

    def test_skill_body_names_no_backend(self):
        # Frontmatter is exempt: the description is the trigger surface, and someone
        # asking to triage a named board should still reach this skill.
        raw = read(os.path.join(SKILL, "SKILL.md"))
        body = raw.split("\n---\n", 1)[1] if raw.startswith("---\n") else raw
        offset = len(raw[: len(raw) - len(body)].splitlines())

        offenders = []
        for lineno, line in enumerate(body.splitlines(), offset + 1):
            if "references/adapters/" in line:
                continue  # the adapter index is the one place a backend may be named
            low = line.lower()
            for token in BACKEND_TOKENS:
                if token in low:
                    offenders.append(f"SKILL.md:{lineno}: {token!r} in {line.strip()!r}")
        self.assertEqual([], offenders, "backend leaked into the backend-agnostic core")

    def test_core_documents_the_adapter_contract(self):
        body = read(os.path.join(SKILL, "SKILL.md"))
        for required in ("**Snapshot**", "**Changeset**", "**Apply**", "**Field map**"):
            self.assertIn(required, body, "adapter contract is missing a required artifact")

    def test_no_dangling_board_analyst_agent(self):
        """AC #4: the hand-off variant used to route through an agent that never existed."""
        for dirpath, _, filenames in os.walk(SKILL):
            for name in filenames:
                if name.endswith(".md"):
                    path = os.path.join(dirpath, name)
                    self.assertNotIn("board-analyst", read(path), f"{path} names a nonexistent agent")


class Adapters(unittest.TestCase):
    """AC #2: two adapters, each answering the contract's questions."""

    def test_at_least_two_adapters_exist(self):
        found = sorted(n for n in os.listdir(ADAPTERS) if n.endswith(".md"))
        self.assertGreaterEqual(len(found), 2, f"expected two or more adapters, found {found}")

    def test_each_adapter_declares_the_contract(self):
        for name in sorted(os.listdir(ADAPTERS)):
            if not name.endswith(".md"):
                continue
            body = read(os.path.join(ADAPTERS, name))
            with self.subTest(adapter=name):
                for section in REQUIRED_ADAPTER_SECTIONS:
                    self.assertIn(section, body, f"{name} is missing {section}")

    def test_core_links_every_adapter(self):
        body = read(os.path.join(SKILL, "SKILL.md"))
        for name in sorted(os.listdir(ADAPTERS)):
            if name.endswith(".md"):
                self.assertIn(f"references/adapters/{name}", body, f"{name} is unreachable")


COLUMNS = [
    {"slug": "to-do", "name": "To Do", "isFinal": False},
    {"slug": "up-next", "name": "Up Next", "isFinal": False},
    {"slug": "done", "name": "Done", "isFinal": True},
]

BOARD = [
    {
        "slug": "to-do",
        "isFinal": False,
        "tasks": [
            {
                "id": "t1",
                "number": 10,
                "title": "untriaged thing",
                "status": "to-do",
                "priority": "no-priority",
                "dueDate": None,
                "assigneeName": None,
                "labels": [],
            },
            {
                "id": "t2",
                "number": 11,
                "title": "already high",
                "status": "to-do",
                "priority": "high",
                "dueDate": "2026-09-01T00:00:00.000Z",
                "assigneeName": "someone",
                "labels": [{"id": "row-a", "name": "infra"}],
            },
        ],
    },
    {"slug": "done", "isFinal": True, "tasks": [{"id": "t3", "number": 9, "title": "shipped",
                                                 "status": "done", "priority": "low",
                                                 "dueDate": None, "assigneeName": None,
                                                 "labels": []}]},
]

LABELS = [{"id": "ws-infra", "name": "infra"}, {"id": "ws-docs", "name": "docs"}]


def snapshot():
    snap = kb.build_snapshot({"name": "demo"}, COLUMNS, BOARD, LABELS)
    attachments = {t["id"]: {l["name"]: l["id"] for l in t["labels"]}
                   for c in BOARD for t in c["tasks"]}
    for item in snap["items"]:
        item["label_ids"] = attachments.get(item["id"], {})
    return snap


class KaneoSnapshot(unittest.TestCase):
    def test_shape_matches_the_contract(self):
        snap = snapshot()
        self.assertEqual("kaneo", snap["board"]["backend"])
        self.assertEqual([9, 10, 11], [i["key"] for i in snap["items"]])
        self.assertEqual(["to-do", "up-next", "done"], snap["fields"]["status"]["options"])
        json.dumps(snap)  # the snapshot has to survive a round-trip to the analyst

    def test_untriaged_priority_reads_as_null_not_a_band(self):
        item = next(i for i in snapshot()["items"] if i["key"] == 10)
        self.assertIsNone(item["fields"]["priority"], "blanks must be visible to triage")

    def test_native_priority_reads_back_as_a_rubric_band(self):
        item = next(i for i in snapshot()["items"] if i["key"] == 11)
        self.assertEqual("P1", item["fields"]["priority"])

    def test_final_column_marks_state_done(self):
        item = next(i for i in snapshot()["items"] if i["key"] == 9)
        self.assertEqual("done", item["state"])

    def test_impact_and_effort_are_absent_not_null(self):
        """An unmapped output must not look like an unset-but-settable cell."""
        fields = snapshot()["items"][0]["fields"]
        self.assertNotIn("impact", fields)
        self.assertNotIn("effort", fields)


class KaneoChangeset(unittest.TestCase):
    def test_parses_tsv_and_skips_header_and_comments(self):
        rows = kb.parse_changeset("key\tfield\tvalue\n# note\n\n10\tpriority\tP1\n")
        self.assertEqual([(10, "priority", "P1")], rows)

    def test_bands_and_native_priorities_both_resolve(self):
        self.assertEqual(("urgent", None), kb.normalize("priority", "P0"))
        self.assertEqual(("urgent", None), kb.normalize("priority", "urgent"))
        self.assertEqual(("no-priority", None), kb.normalize("priority", ""))
        value, problem = kb.normalize("priority", "P9")
        self.assertIsNone(value)
        self.assertIn("P9", problem)

    def test_plan_writes_only_differing_cells(self):
        ops, problems = kb.plan(snapshot(), [(10, "priority", "P1"), (11, "priority", "P1")])
        self.assertEqual([], problems)
        self.assertEqual([("updatePriority", "high", "t1")], [op[:3] for op in ops],
                         "#11 is already high — a no-op row must not produce a write")

    def test_replanning_an_applied_changeset_is_empty(self):
        rows = [(11, "priority", "P1"), (11, "status", "to-do"), (11, "due", "2026-09-01")]
        ops, problems = kb.plan(snapshot(), rows)
        self.assertEqual(([], []), (ops, problems), "apply must be idempotent")

    def test_status_off_the_board_is_refused(self):
        ops, problems = kb.plan(snapshot(), [(10, "status", "in-progress")])
        self.assertEqual([], ops)
        self.assertIn("not a lane on this board", problems[0])

    def test_unknown_item_and_unknown_field_are_reported_not_guessed(self):
        ops, problems = kb.plan(snapshot(), [(99, "priority", "P1"), (10, "impact", "High")])
        self.assertEqual([], ops)
        self.assertEqual(2, len(problems))
        self.assertIn("not on this board", problems[0])
        self.assertIn("no Kaneo cell", problems[1])

    def test_labels_diff_into_attach_and_detach(self):
        ops, problems = kb.plan(snapshot(), [(11, "labels", "docs")],
                                {"infra": "ws-infra", "docs": "ws-docs"})
        self.assertEqual([], problems)
        self.assertEqual(
            [("addLabel", "ws-docs", "t2"), ("removeLabel", "row-a", "t2")],
            [op[:3] for op in ops],
        )

    def test_label_missing_from_the_workspace_is_skipped_not_invented(self):
        ops, problems = kb.plan(snapshot(), [(10, "labels", "nope")], {"infra": "ws-infra"})
        self.assertEqual([], ops)
        self.assertIn("does not exist in this workspace", problems[0])

    def test_group_collapses_same_valued_writes_into_one_call(self):
        ops = [("updatePriority", "high", "t1", ""), ("updatePriority", "high", "t2", ""),
               ("updateStatus", "up-next", "t1", "")]
        calls = kb.group(ops)
        self.assertEqual(2, len(calls))
        self.assertEqual(["t1", "t2"], next(c for c in calls if c["operation"] == "updatePriority")["taskIds"])


class FakeKaneo:
    """In-memory Kaneo over the BOARD fixture: serves the four GETs apply issues and
    mutates its own copy on a bulk write, except for ops named in `revert`."""

    OP_FIELD = {
        "updateStatus": "status",
        "updatePriority": "priority",
        "updateDueDate": "dueDate",
        "updateAssignee": "assigneeName",
    }

    def __init__(self, revert=()):
        self.columns = copy.deepcopy(BOARD)
        self.revert = set(revert)  # (task id, operation) the server accepts and then undoes
        self.writes = []

    def __call__(self, method, path, body=None):
        if method == "GET":
            if path.startswith("/project/"):
                return {"name": "demo", "workspaceId": "ws1"}
            if path.startswith("/column/"):
                return copy.deepcopy(COLUMNS)
            if path.startswith("/task/tasks/"):
                return {"columns": copy.deepcopy(self.columns)}
            if path.startswith("/label/workspace/"):
                return copy.deepcopy(LABELS)
        if method == "PATCH" and path == "/task/bulk":
            self.writes.append(body)
            field = self.OP_FIELD[body["operation"]]
            for task_id in body["taskIds"]:
                if (task_id, body["operation"]) not in self.revert:
                    self._task(task_id)[field] = body["value"]
            return {}
        raise AssertionError(f"unexpected request: {method} {path}")

    def _task(self, task_id):
        return next(t for c in self.columns for t in c["tasks"] if t["id"] == task_id)


class KaneoApplyReadBack(unittest.TestCase):
    """The module's no-mock rule has one exception, and this is it.

    What is asserted here is cmd_apply's own control flow — that a cell which reads back
    unchanged is not counted as applied, prints, and picks the exit code — not Kaneo's
    response shape. The shapes the fake serves are the same COLUMNS/BOARD/LABELS fixtures
    the snapshot tests above already run on, so no new guess about the server is being
    made; the only new claim is about this script. Measured 2026-08-22 on the real board:
    three `PATCH /task/bulk` status writes for DFA-260 were each undone 4-6s later, and
    apply still reported them applied because it counted operations issued.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_apply(self, fake, changeset, argv=("--apply", "--settle-seconds", "0")):
        path = os.path.join(self.tmp.name, "changeset.tsv")
        with open(path, "w") as handle:
            handle.write(changeset)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(kb, "_request", fake))
            stack.enter_context(mock.patch.dict(os.environ, {"KANEO_PROJECT_ID": "p1"}))
            slept = stack.enter_context(mock.patch("time.sleep"))
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            code = kb.main(["apply", "--changeset", path, *argv])
        self.assertFalse(slept.called, "--settle-seconds 0 must not sleep in a test suite")
        return code, out.getvalue(), err.getvalue()

    def test_landed_cell_is_counted_and_exits_clean(self):
        fake = FakeKaneo()
        code, out, err = self.run_apply(fake, "10\tstatus\tup-next\n")
        self.assertEqual("up-next", fake._task("t1")["status"])
        self.assertIn("applied 1 cell change(s)", out)
        self.assertNotIn("UNLANDED", out + err)
        self.assertEqual(0, code)

    def test_reverted_cell_is_not_counted_and_exits_2(self):
        fake = FakeKaneo(revert=[("t1", "updateStatus")])
        code, out, err = self.run_apply(fake, "10\tstatus\tup-next\n")
        self.assertEqual([{"operation": "updateStatus", "value": "up-next",
                           "taskIds": ["t1"]}], fake.writes, "the write must still be issued")
        self.assertIn("applied 0 cell change(s)", out)
        report = out + err
        self.assertIn("UNLANDED", report)
        self.assertIn("#10", report)
        self.assertIn("status", report)
        self.assertIn("up-next", report)
        self.assertEqual(2, code)
        self.assertNotEqual(1, code)

    def test_unlanded_beats_problems_in_the_exit_code(self):
        fake = FakeKaneo(revert=[("t1", "updateStatus")])
        code, _, err = self.run_apply(fake, "10\tstatus\tup-next\n99\tstatus\tup-next\n")
        self.assertIn("SKIP", err)
        self.assertIn("UNLANDED", err)
        self.assertEqual(2, code, "an unlanded cell outranks an unresolvable row")

    def test_a_skip_is_a_failure_on_stderr_and_the_rest_still_applies(self):
        """The contract's SKIP ruling, pinned on this adapter as it is on the other two."""
        fake = FakeKaneo()
        code, out, err = self.run_apply(fake, "99\tstatus\tup-next\n10\tstatus\tup-next\n")
        self.assertEqual(1, code, out + err)
        self.assertIn("SKIP #99: not on this board", err)
        self.assertNotIn("SKIP", out, "a refusal belongs on stderr, not in the row log")
        self.assertIn("applied 1 cell change(s)", out, "the resolvable row still applies")
        self.assertEqual("up-next", fake._task("t1")["status"])

    def test_unresolvable_row_alone_still_exits_1(self):
        code, out, err = self.run_apply(FakeKaneo(), "99\tpriority\tP1\n")
        self.assertIn("not on this board", err)
        self.assertNotIn("UNLANDED", out + err)
        self.assertEqual(1, code, "the pre-existing problems exit path must survive")

    def test_apply_help_documents_both_exit_codes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
            kb.main(["apply", "--help"])
        text = out.getvalue()
        self.assertIn("--settle-seconds", text)
        self.assertIn("exit codes:", text)
        # "1"/"2" appear in any help text; the codes have to be described, not present.
        self.assertIn("1  some changeset rows were unresolvable", text)
        self.assertIn("2  a written cell read back unchanged", text)


class GithubProjectsFailIsOnStderr(unittest.TestCase):
    """SKIP already moved to stderr for this adapter (see the fix on 5c9f095); FAIL must
    match, same as the Kaneo adapter's own SKIP-is-a-failure pin above."""

    @staticmethod
    def _stub_gh(cmd, capture_output=False, text=False, env=None):
        query = next((a for a in cmd if a.startswith("query=")), "")
        if "projectV2(number:$n)" in query:
            payload = {"data": {"user": {"projectV2": {"id": "PVT_1", "title": "t"}}}}
        elif "fields(first:50" in query:
            payload = {
                "data": {"node": {"fields": {"nodes": [
                    {"id": "F_status", "name": "Status", "dataType": "SINGLE_SELECT",
                     "options": [{"id": "opt_todo", "name": "Todo"}]},
                ]}}}
            }
        elif "items(first:100" in query:
            payload = {
                "data": {"node": {"items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{
                        "id": "PVTI_1",
                        "content": {
                            "__typename": "Issue", "number": 1, "title": "x", "state": "OPEN",
                            "repository": {"nameWithOwner": "acme/widgets"},
                            "labels": {"nodes": []}, "milestone": None, "parent": None,
                        },
                        "fieldValues": {"nodes": []},
                    }],
                }}}
            }
        else:
            raise AssertionError(f"unexpected query: {query[:80]}")
        return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")

    def test_an_unresolvable_option_fails_on_stderr_not_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "changeset.tsv")
            with open(path, "w") as handle:
                handle.write("1\tstatus\tShipped\n")
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("subprocess.run", self._stub_gh):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = gpb.main(["apply", "-o", "acme", "-n", "8", "--changeset", path])
        self.assertEqual(1, code)
        self.assertIn("FAIL  #1 status=Shipped: no option 'Shipped'", err.getvalue())
        self.assertNotIn("FAIL", out.getvalue(), "a refusal belongs on stderr, not the row log")


class KaneoAdapterDoc(unittest.TestCase):
    def test_apply_section_names_the_trustworthy_status_write_path(self):
        """A bulk status write that silently reverts is invisible unless the doc says so."""
        body = read(os.path.join(ADAPTERS, "kaneo.md"))
        apply_section = body.split("## Apply", 1)[1].split("\n## ", 1)[0]
        self.assertIn("PUT /task/status/", apply_section)
        self.assertIn("2026-08-22", apply_section)
        for code in ("exit 1", "exit 2"):
            self.assertIn(code, apply_section)


if __name__ == "__main__":
    unittest.main()
