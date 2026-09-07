"""board-triage's GitHub Projects adapter: the argv it builds and what it does with the answer.

Sibling of test_kata_board.py, covered on the same principle: everything between the
GraphQL payload and the argv of a mutation is this adapter's own judgment. `subprocess.run`
is stubbed with a dispatcher that answers on the query text and records each argv, so the
`gh` calls themselves are only checked at the boundary.

What breaks silently if this drifts: a cell that stops comparing equal turns every re-run
into fresh writes, a refusal that stops refusing writes a field the project API cannot set,
a dropped cursor exports page one as if it were the whole board, and a `CLOSED` item that
maps back to `open` buries the live work under a board's worth of closed blanks.
"""

import contextlib
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
SCRIPT = os.path.join(
    ROOT, "primitives-core", "skills", "board-triage", "scripts", "github_projects_board.py"
)

# No __pycache__ under primitives-core: it is litter there, and a same-length edit within
# one mtime-second (mutation testing this script) would otherwise load stale bytecode.
_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _spec = importlib.util.spec_from_file_location("github_projects_board", SCRIPT)
    gpb = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(gpb)
finally:
    sys.dont_write_bytecode = _bytecode

PROJECT = {"id": "PVT_board", "title": "widgets board"}
MUTATION_OK = {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_1"}}}}


def project_ok(query):
    scope = "organization" if "organization(login" in query else "user"
    return {"data": {scope: {"projectV2": PROJECT}}}


def project_missing(query):
    scope = "organization" if "organization(login" in query else "user"
    return {"data": {scope: {"projectV2": None}}}


FIELDS = {
    "data": {
        "node": {
            "fields": {
                "nodes": [
                    {
                        "id": "F_status",
                        "name": "Status",
                        "dataType": "SINGLE_SELECT",
                        "options": [{"id": "opt_todo", "name": "Todo"}, {"id": "opt_done", "name": "Done"}],
                    },
                    {
                        "id": "F_pri",
                        "name": "Priority",
                        "dataType": "SINGLE_SELECT",
                        "options": [{"id": "opt_p0", "name": "P0"}, {"id": "opt_p1", "name": "P1"}],
                    },
                    {"id": "F_effort", "name": "Est Effort", "dataType": "NUMBER"},
                    {"id": "F_target", "name": "Target", "dataType": "DATE"},
                    {"id": "F_notes", "name": "Notes", "dataType": "TEXT"},
                    {"id": "F_labels", "name": "Labels", "dataType": "LABELS"},
                    {
                        "id": "F_sprint",
                        "name": "Sprint",
                        "dataType": "ITERATION",
                        "configuration": {
                            "iterations": [{"id": "it_2", "title": "Sprint 2"}],
                            "completedIterations": [{"id": "it_1", "title": "Sprint 1"}],
                        },
                    },
                    None,  # the API returns nulls for field types the query does not fragment
                ]
            }
        }
    }
}


class Gh:
    """Stands in for `subprocess.run`: records every argv, answers on the query text.

    A graphql response may be a callable (given the query text) or a list consumed one
    call at a time, last entry repeating — that is how a paginated read is scripted.
    """

    def __init__(self, graphql=(), rest=None):
        self.graphql = list(graphql)
        self.rest = dict(rest or {})
        self.calls = []
        self.envs = []

    def __call__(self, cmd, capture_output=False, text=False, env=None):
        self.calls.append(list(cmd))
        self.envs.append(dict(env) if env is not None else None)
        if cmd[0] != "gh":
            raise AssertionError(f"not a gh call: {cmd}")
        if cmd[1:3] == ["api", "graphql"]:
            query = next(a for a in cmd if a.startswith("query="))
            for key, payload in self.graphql:
                if key in query:
                    if isinstance(payload, list):
                        payload = payload.pop(0) if len(payload) > 1 else payload[0]
                    if callable(payload):
                        payload = payload(query)
                    return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")
            raise AssertionError("no canned response for query: " + query[:120])
        path = next(a for a in cmd if a.startswith("repos/"))
        rc, out = self.rest.get(path, (1, ""))
        return subprocess.CompletedProcess(cmd, rc, out, "not found" if rc else "")

    def graphql_calls(self):
        return [c for c in self.calls if c[1:3] == ["api", "graphql"]]

    def query_of(self, cmd):
        return next(a for a in cmd if a.startswith("query="))

    def matching(self, needle):
        return [c for c in self.graphql_calls() if needle in self.query_of(c)]

    def mutations(self):
        return self.matching("mutation(")

    def rest_calls(self):
        return [c for c in self.calls if c[1:3] != ["api", "graphql"]]


def run_main(argv, gh):
    """Drive main() with a stubbed gh; returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch("subprocess.run", gh):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = gpb.main(argv)
            except SystemExit as exc:
                code = exc.code
    return code, out.getvalue(), err.getvalue()


def board_gh(items_pages, rest=None, project=project_ok):
    return Gh(
        graphql=[
            ("projectV2(number:$n)", project),
            ("fields(first:50", FIELDS),
            ("items(first:100", items_pages),
            ("mutation(", MUTATION_OK),
        ],
        rest=rest,
    )


def item(number, state="OPEN", status="Todo", priority="P0", effort=3.0, notes="seed"):
    return {
        "id": f"PVTI_{number}",
        "content": {
            "__typename": "Issue",
            "number": number,
            "title": f"issue {number}",
            "state": state,
            "repository": {"nameWithOwner": "acme/widgets"},
            "labels": {"nodes": [{"name": "bug"}, {"name": "infra"}]},
            "milestone": {"title": "m1"},
            "parent": {"number": 4},
        },
        "fieldValues": {
            "nodes": [
                {"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": status, "field": {"name": "Status"}},
                {"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": priority, "field": {"name": "Priority"}},
                {"__typename": "ProjectV2ItemFieldNumberValue", "number": effort, "field": {"name": "Est Effort"}},
                {"__typename": "ProjectV2ItemFieldTextValue", "text": notes, "field": {"name": "Notes"}},
                {"__typename": "ProjectV2ItemFieldLabelValue", "field": None},
            ]
        },
    }


def page(*items, cursor=None):
    info = {"hasNextPage": cursor is not None, "endCursor": cursor}
    return {"data": {"node": {"items": {"pageInfo": info, "nodes": list(items)}}}}


DRAFT = {
    "id": "PVTI_d",
    "content": {"__typename": "DraftIssue", "title": "a draft"},
    "fieldValues": {"nodes": []},
}

CLOSED_ITEM = {
    "id": "PVTI_2",
    "content": {"__typename": "Issue", "number": 2, "title": "second", "state": "CLOSED"},
    "fieldValues": {
        "nodes": [{"__typename": "ProjectV2ItemFieldNumberValue", "number": 0, "field": {"name": "Est Effort"}}]
    },
}


def export_gh():
    return board_gh([page(item(1), DRAFT, cursor="CURSOR1"), page(CLOSED_ITEM)])


# --- pure helpers -----------------------------------------------------------------


class Helpers(unittest.TestCase):
    def test_values_equal_is_case_insensitive_with_a_numeric_fallback(self):
        self.assertTrue(gpb.values_equal("Done", "done"))
        self.assertTrue(gpb.values_equal(3.0, "3"))
        self.assertTrue(gpb.values_equal(3, "3.0"))
        self.assertFalse(gpb.values_equal("Todo", "Done"))
        self.assertFalse(gpb.values_equal(None, ""), "an unset cell never equals a changeset value")
        self.assertFalse(gpb.values_equal(None, "Done"))

    def test_resolve_field_ignores_case_spaces_and_underscores(self):
        fields = {"Est Effort": {}, "Status": {}}
        self.assertEqual("Est Effort", gpb.resolve_field("est_effort", fields))
        self.assertEqual("Est Effort", gpb.resolve_field("ESTEFFORT", fields))
        self.assertEqual("Status", gpb.resolve_field("status", fields))
        self.assertIsNone(gpb.resolve_field("nope", fields))

    def test_field_value_keeps_empty_text_and_zero(self):
        self.assertEqual("", gpb.field_value({"__typename": "ProjectV2ItemFieldTextValue", "text": ""}))
        self.assertEqual(0, gpb.field_value({"__typename": "ProjectV2ItemFieldNumberValue", "number": 0}))
        self.assertEqual(
            "Todo", gpb.field_value({"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": "Todo"})
        )
        self.assertEqual(
            "Sprint 1", gpb.field_value({"__typename": "ProjectV2ItemFieldIterationValue", "title": "Sprint 1"})
        )
        self.assertIsNone(gpb.field_value({"__typename": "ProjectV2ItemFieldLabelValue"}))


class Changeset(unittest.TestCase):
    def test_both_header_spellings_are_dropped_and_noise_is_skipped(self):
        rows = gpb.parse_changeset("key\tfield\tvalue\n# a comment\n\n671\tpriority\tP1\n")
        self.assertEqual([("671", "priority", "P1")], rows)
        self.assertEqual(
            rows,
            gpb.parse_changeset("issue\tfield\tvalue\n671\tpriority\tP1\n"),
            "board-apply.py's 'issue' header still parses",
        )

    def test_a_row_without_a_field_column_is_an_error(self):
        with self.assertRaises(SystemExit) as cm:
            gpb.parse_changeset("671\n")
        self.assertIn("line 1", str(cm.exception.code))

    def test_field_token_is_lowered_and_the_value_is_stripped(self):
        self.assertEqual([("1", "est effort", "5")], gpb.parse_changeset("1\tEst Effort\t5\n"))
        self.assertEqual([("1", "notes", "")], gpb.parse_changeset("1\tnotes\t\n"))


# --- export -----------------------------------------------------------------------


class Export(unittest.TestCase):
    def snapshot(self, argv=("export", "-o", "acme", "-n", "8"), gh=None):
        gh = gh or export_gh()
        code, out, err = run_main(list(argv), gh)
        self.assertEqual(0, code, out + err)
        return json.loads(out), gh

    def test_board_block_names_the_backend_and_the_project(self):
        snap, _ = self.snapshot()
        self.assertEqual(["board", "fields", "items"], list(snap))
        self.assertEqual(
            {
                "name": "widgets board",
                "backend": "github-projects",
                "owner": "acme",
                "number": 8,
                "id": "PVT_board",
            },
            snap["board"],
        )

    def test_items_are_a_complete_grid_keyed_by_issue_number(self):
        snap, _ = self.snapshot()
        self.assertEqual([1, 2], [i["key"] for i in snap["items"]], "draft issues are dropped")
        first = snap["items"][0]
        self.assertEqual("PVTI_1", first["id"])
        self.assertEqual("issue 1", first["title"])
        self.assertEqual(["bug", "infra"], first["labels"])
        self.assertEqual("m1", first["milestone"])
        self.assertEqual(4, first["parent"])
        self.assertEqual("acme/widgets", first["repo"])
        self.assertEqual(
            {
                "Status": "Todo",
                "Priority": "P0",
                "Est Effort": 3.0,
                "Target": None,
                "Notes": "seed",
                "Sprint": None,
            },
            first["fields"],
            "every operating field is a column, null when unset",
        )
        self.assertNotIn("Labels", first["fields"], "a LABELS field is not settable, so it is not a cell")

        second = snap["items"][1]
        self.assertEqual(0, second["fields"]["Est Effort"], "a zero cell is a value, not a blank")
        self.assertEqual([], second["labels"])
        self.assertIsNone(second["milestone"])
        self.assertIsNone(second["parent"])

    def test_closed_items_come_back_as_done(self):
        snap, _ = self.snapshot()
        self.assertEqual(["open", "done"], [i["state"] for i in snap["items"]])

    def test_merged_is_done_and_an_unknown_state_stays_visible(self):
        gh = board_gh([page(item(1, state="MERGED"), item(3, state=None))])
        snap, _ = self.snapshot(gh=gh)
        self.assertEqual(["done", "open"], [i["state"] for i in snap["items"]])

    def test_fields_block_is_the_changeset_enum_reference(self):
        snap, _ = self.snapshot()
        self.assertEqual(["Todo", "Done"], snap["fields"]["Status"]["options"])
        self.assertEqual(["P0", "P1"], snap["fields"]["Priority"]["options"])
        self.assertEqual(
            ["Sprint 2", "Sprint 1"],
            snap["fields"]["Sprint"]["options"],
            "completed iterations are legal changeset values too",
        )
        self.assertEqual(["YYYY-MM-DD"], snap["fields"]["Target"]["options"])
        self.assertEqual(["<number>"], snap["fields"]["Est Effort"]["options"])
        self.assertEqual(["<text>"], snap["fields"]["Notes"]["options"])
        self.assertNotIn("Labels", snap["fields"], "a field no changeset can write is not offered")

    def test_pagination_passes_the_cursor_to_the_second_page(self):
        snap, gh = self.snapshot()
        pages = gh.matching("items(first:100")
        self.assertEqual(2, len(pages))
        self.assertNotIn("after=CURSOR1", pages[0])
        self.assertIn("after=CURSOR1", pages[1])
        self.assertIn("id=PVT_board", pages[1])
        self.assertEqual([1, 2], [i["key"] for i in snap["items"]])

    def test_out_writes_the_json_to_a_file_and_counts_the_untriaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshot.json")
            code, out, err = run_main(["export", "-o", "acme", "-n", "8", "--out", path], export_gh())
            self.assertEqual(0, code, out + err)
            with open(path) as handle:
                written = json.load(handle)
        self.assertEqual([1, 2], [i["key"] for i in written["items"]])
        self.assertIn("2 items (1 untriaged)", out)
        self.assertIn(path, out)

    def test_project_lookup_argv_carries_the_owner_and_number(self):
        _, gh = self.snapshot()
        lookup = gh.matching("projectV2(number:$n)")[0]
        self.assertEqual(["gh", "api", "graphql"], lookup[:3])
        self.assertIn("o=acme", lookup)
        self.assertEqual(["-F", "n=8"], lookup[-2:], "an Int! var needs -F, not -f")
        self.assertIn("user(login", gh.query_of(lookup))

    def test_org_owner_type_switches_the_graphql_scope(self):
        _, gh = self.snapshot(argv=("export", "-o", "acme", "-n", "8", "--owner-type", "org"))
        self.assertIn("organization(login", gh.query_of(gh.matching("projectV2(number:$n)")[0]))

    def test_missing_project_exits_before_reading_fields(self):
        gh = board_gh([page(item(1))], project=project_missing)
        code, out, err = run_main(["export", "-o", "acme", "-n", "8"], gh)
        self.assertIn("acme#8 not found", str(code))
        self.assertEqual(1, len(gh.calls), "no field query is issued once the project is missing")


# --- apply ------------------------------------------------------------------------


class Apply(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def changeset(self, *rows, header="key"):
        path = os.path.join(self.tmp, "changeset.tsv")
        with open(path, "w") as handle:
            handle.write(f"{header}\tfield\tvalue\n")
            for row in rows:
                handle.write("\t".join(row) + "\n")
        return path

    def argv(self, path, *extra):
        return ["apply", "-o", "acme", "-n", "8", "--changeset", path, *extra]

    def test_only_the_differing_cell_is_written(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "priority", "P0"), ("1", "status", "Done"))
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertIn("OK    #1 priority=P0: unchanged", out)
        self.assertIn("SET   #1 status=Done", out)
        muts = gh.mutations()
        self.assertEqual(1, len(muts), out)
        for pair in ("p=PVT_board", "i=PVTI_1", "f=F_status", "o=opt_done"):
            self.assertIn(pair, muts[0])
        self.assertIn("updateProjectV2ItemFieldValue", gh.query_of(muts[0]))

    def test_the_issue_header_spelling_still_applies(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "status", "Done"), header="issue")
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertEqual(1, len(gh.mutations()), out)
        self.assertNotIn("SKIP", out, "the header is a header, not a row keyed 'issue'")

    def test_rerun_against_the_written_board_writes_nothing(self):
        gh = board_gh([page(item(1, status="Done"))])
        cs = self.changeset(("1", "priority", "P0"), ("1", "status", "Done"))
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertEqual([], gh.mutations(), "an idempotent re-run is free")
        self.assertEqual(2, out.count("OK    "), out)

    def test_dry_run_plans_without_writing(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "status", "Done"), ("1", "notes", "hello"))
        code, out, err = run_main(self.argv(cs), gh)
        self.assertEqual(0, code, out + err)
        self.assertEqual(2, out.count("DRY   would set"), out)
        self.assertEqual([], gh.mutations())
        self.assertIn("re-run with --apply", err)

    def test_every_refusal_path_skips_instead_of_writing(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(
            ("9", "status", "Done"),  # not on the board
            ("1", "nope", "x"),  # no such field
            ("1", "labels", "bug"),  # not settable via the project API
            ("abc", "status", "Done"),  # not an issue number
            ("1", "blocked_by", "2"),  # needs --repo
        )
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertIn("SKIP  #9 status=Done: not on board", out)
        self.assertIn("SKIP  #1 nope=x: no field matches 'nope'", out)
        self.assertIn("(LABELS) not settable", out)
        self.assertIn("SKIP  row key='abc': not an integer", out)
        self.assertIn("SKIP  #1 blocked_by=2: --repo required", out)
        self.assertEqual(5, out.count("SKIP  "), out)
        self.assertEqual([], gh.mutations())

    def test_unknown_single_select_option_fails_the_run(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "status", "Shipped"))
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(1, code, out + err)
        self.assertIn("FAIL  #1 status=Shipped: no option 'Shipped'", out)
        self.assertEqual([], gh.mutations())

    def test_iteration_value_resolves_against_completed_buckets_too(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "sprint", "sprint 1"))
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertIn("o=it_1", gh.mutations()[0])

    def test_scalar_write_branches_bind_their_typed_variables(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "est effort", "5"), ("1", "target", "2026-06-18"), ("1", "notes", "hello"))
        code, out, err = run_main(self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out + err)
        number, date, text = gh.mutations()
        self.assertEqual(["-F", "nn=5"], number[-2:], "a Float! var needs -F, not -f")
        self.assertIn("f=F_effort", number)
        self.assertIn("d=2026-06-18", date)
        self.assertEqual("-f", date[date.index("d=2026-06-18") - 1])
        self.assertIn("f=F_target", date)
        self.assertIn("t=hello", text)
        self.assertEqual("-f", text[text.index("t=hello") - 1])
        self.assertIn("f=F_notes", text)

    def test_empty_value_clears_only_a_populated_cell(self):
        gh = board_gh([page(item(1, notes="seed"))])
        code, out, err = run_main(self.argv(self.changeset(("1", "notes", "")), "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertIn("SET   #1 notes=(clear)", out)
        muts = gh.mutations()
        self.assertEqual(1, len(muts))
        self.assertIn("clearProjectV2ItemFieldValue", gh.query_of(muts[0]))
        self.assertIn("f=F_notes", muts[0])

        gh2 = board_gh([page(item(1, notes=""))])
        code, out, err = run_main(self.argv(self.changeset(("1", "notes", "")), "--apply"), gh2)
        self.assertEqual(0, code, out + err)
        self.assertIn("already clear", out)
        self.assertEqual([], gh2.mutations())

    def test_blocked_by_posts_to_the_rest_dependencies_endpoint(self):
        gh = board_gh(
            [page(item(1))],
            rest={
                "repos/acme/widgets/issues/2": (0, "77\n"),
                "repos/acme/widgets/issues/1/dependencies/blocked_by": (0, ""),
            },
        )
        cs = self.changeset(("1", "blocked_by", "2"))
        code, out, err = run_main(self.argv(cs, "--repo", "acme/widgets", "--apply"), gh)
        self.assertEqual(0, code, out + err)
        self.assertIn("SET   #1 blocked_by=2", out)
        self.assertEqual(
            [
                ["gh", "api", "repos/acme/widgets/issues/2", "--jq", ".id"],
                [
                    "gh",
                    "api",
                    "-X",
                    "POST",
                    "repos/acme/widgets/issues/1/dependencies/blocked_by",
                    "-F",
                    "issue_id=77",
                ],
            ],
            gh.rest_calls(),
        )
        self.assertEqual([], gh.mutations())

    def test_a_missing_blocker_fails_the_run(self):
        gh = board_gh([page(item(1))])
        cs = self.changeset(("1", "blocking", "2"))
        code, out, err = run_main(self.argv(cs, "--repo", "acme/widgets", "--apply"), gh)
        self.assertEqual(1, code, out + err)
        self.assertIn("FAIL  #1 blocking=2", out)

    def test_github_token_is_stripped_from_the_gh_environment(self):
        """A repo-scoped GITHUB_TOKEN shadows the project-scoped keyring login."""
        gh = board_gh([page(item(1))])
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "shadowing-token"}):
            code, out, err = run_main(self.argv(self.changeset(("1", "status", "Todo"))), gh)
        self.assertEqual(0, code, out + err)
        self.assertTrue(gh.envs)
        for env in gh.envs:
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertIn("PATH", env, "the rest of the environment still reaches gh")

    def test_apply_re_pulls_the_board_instead_of_trusting_a_snapshot(self):
        gh = board_gh([page(item(1))])
        code, out, err = run_main(self.argv(self.changeset(("1", "status", "Done"))), gh)
        self.assertEqual(0, code, out + err)
        self.assertEqual(1, len(gh.matching("items(first:100")), "a fresh pull, every run")


if __name__ == "__main__":
    unittest.main()
