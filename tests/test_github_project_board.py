"""github-project-board's three scripts: the argv they build and what they do with the answer.

Every one of them shells to `gh`, so `subprocess.run` is stubbed with a dispatcher that
answers on the query text and records each argv. What is covered is the half that can be
wrong on its own: board-apply's diff/resolve (a cell that stops comparing equal turns every
re-run into fresh writes, a refusal that stops refusing writes a field the project API cannot
set), board-export's snapshot grid and cursor loop (a dropped cursor silently exports page
one as if it were the board), and board-fields' option/iteration merge (a missing bucket
makes a valid changeset value look invalid).
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
SCRIPTS = os.path.join(ROOT, "primitives-core", "skills", "github-project-board", "scripts")


def _load(stem):
    path = os.path.join(SCRIPTS, stem + ".py")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# No __pycache__ under primitives-core: it is litter there, and a same-length edit within
# one mtime-second (mutation testing these scripts) would otherwise load stale bytecode.
_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    apply_mod = _load("board-apply")
    export_mod = _load("board-export")
    fields_mod = _load("board-fields")
finally:
    sys.dont_write_bytecode = _bytecode

PROJECT = {"id": "PVT_board", "title": "widgets board"}


def project_ok(query):
    scope = "organization" if "organization(login" in query else "user"
    return {"data": {scope: {"projectV2": PROJECT}}}


def project_missing(query):
    scope = "organization" if "organization(login" in query else "user"
    return {"data": {scope: {"projectV2": None}}}


MUTATION_OK = {"data": {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_1"}}}}


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


def run_main(module, argv, gh):
    """Drive a script's main() with a stubbed gh; returns (exit code, stdout)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch("subprocess.run", gh), mock.patch.object(sys, "argv", argv):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                module.main()
            except SystemExit as e:
                code = e.code
    return code, out.getvalue()


# --- board-apply ------------------------------------------------------------------

APPLY_FIELDS = {
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


def apply_item(number, status="Todo", priority="P0", effort=3.0, notes="seed"):
    return {
        "id": f"PVTI_{number}",
        "content": {"__typename": "Issue", "number": number},
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


def apply_page(*items):
    return {"data": {"node": {"items": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": list(items)}}}}


def apply_gh(items_page, rest=None):
    return Gh(
        graphql=[
            ("projectV2(number:$n)", project_ok),
            ("fields(first:50)", APPLY_FIELDS),
            ("items(first:100", items_page),
            ("mutation(", MUTATION_OK),
        ],
        rest=rest,
    )


class ApplyHelpers(unittest.TestCase):
    def test_values_equal_is_case_insensitive_with_a_numeric_fallback(self):
        self.assertTrue(apply_mod.values_equal("Done", "done"))
        self.assertTrue(apply_mod.values_equal(3.0, "3"))
        self.assertTrue(apply_mod.values_equal(3, "3.0"))
        self.assertFalse(apply_mod.values_equal("Todo", "Done"))
        self.assertFalse(apply_mod.values_equal(None, ""), "an unset cell never equals a changeset value")
        self.assertFalse(apply_mod.values_equal(None, "Done"))

    def test_resolve_field_ignores_case_spaces_and_underscores(self):
        fields = {"Est Effort": {}, "Status": {}}
        self.assertEqual("Est Effort", apply_mod.resolve_field("est_effort", fields))
        self.assertEqual("Est Effort", apply_mod.resolve_field("ESTEFFORT", fields))
        self.assertEqual("Status", apply_mod.resolve_field("status", fields))
        self.assertIsNone(apply_mod.resolve_field("nope", fields))

    def test_fv_scalar_reads_key_presence_so_empty_and_zero_survive(self):
        self.assertEqual("", apply_mod.fv_scalar({"text": ""}))
        self.assertEqual(0, apply_mod.fv_scalar({"number": 0}))
        self.assertEqual("Todo", apply_mod.fv_scalar({"name": "Todo"}))
        self.assertIsNone(apply_mod.fv_scalar({"text": None}))
        self.assertIsNone(apply_mod.fv_scalar({"__typename": "ProjectV2ItemFieldLabelValue"}))


class ApplyChangeset(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name

    def changeset(self, *rows):
        path = os.path.join(self.tmp, "changeset.tsv")
        with open(path, "w") as fh:
            fh.write("issue\tfield\tvalue\n")
            for row in rows:
                fh.write("\t".join(row) + "\n")
        return path

    def argv(self, path, *extra):
        return ["board-apply.py", "-o", "acme", "-n", "8", "--changeset", path, *extra]

    def test_only_the_differing_cell_is_written(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "priority", "P0"), ("1", "status", "Done"))
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("OK    #1 priority=P0: unchanged", out)
        self.assertIn("SET   #1 status=Done", out)
        muts = gh.mutations()
        self.assertEqual(1, len(muts), out)
        for pair in ("p=PVT_board", "i=PVTI_1", "f=F_status", "o=opt_done"):
            self.assertIn(pair, muts[0])
        self.assertIn("updateProjectV2ItemFieldValue", gh.query_of(muts[0]))

    def test_rerun_against_the_written_board_writes_nothing(self):
        gh = apply_gh(apply_page(apply_item(1, status="Done")))
        cs = self.changeset(("1", "priority", "P0"), ("1", "status", "Done"))
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertEqual([], gh.mutations(), "an idempotent re-run is free")
        self.assertEqual(2, out.count("OK    "), out)

    def test_project_lookup_argv_carries_the_owner_and_number(self):
        gh = apply_gh(apply_page(apply_item(1)))
        code, out = run_main(apply_mod, self.argv(self.changeset(("1", "status", "Todo"))), gh)
        self.assertEqual(0, code, out)
        lookup = gh.matching("projectV2(number:$n)")[0]
        self.assertEqual(["gh", "api", "graphql"], lookup[:3])
        self.assertIn("o=acme", lookup)
        self.assertEqual(["-F", "n=8"], lookup[-2:], "an Int! var needs -F, not -f")
        self.assertIn("user(login", gh.query_of(lookup))

    def test_org_owner_type_switches_the_graphql_scope(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "status", "Todo"))
        code, out = run_main(apply_mod, self.argv(cs, "--owner-type", "org"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("organization(login", gh.query_of(gh.matching("projectV2(number:$n)")[0]))

    def test_dry_run_plans_without_writing(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "status", "Done"), ("1", "notes", "hello"))
        code, out = run_main(apply_mod, self.argv(cs), gh)
        self.assertEqual(0, code, out)
        self.assertEqual(2, out.count("DRY   would set"), out)
        self.assertEqual([], gh.mutations())

    def test_every_refusal_path_skips_instead_of_writing(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(
            ("9", "status", "Done"),  # not on the board
            ("1", "nope", "x"),  # no such field
            ("1", "labels", "bug"),  # not settable via the project API
            ("abc", "status", "Done"),  # not an issue number
            ("1", "blocked_by", "2"),  # needs --repo
        )
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("SKIP  #9 status=Done: not on board", out)
        self.assertIn("SKIP  #1 nope=x: no field matches 'nope'", out)
        self.assertIn("(LABELS) not settable", out)
        self.assertIn("SKIP  row issue='abc': not an integer", out)
        self.assertIn("SKIP  #1 blocked_by=2: --repo required", out)
        self.assertEqual(5, out.count("SKIP  "), out)
        self.assertEqual([], gh.mutations())

    def test_unknown_single_select_option_fails_the_run(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "status", "Shipped"))
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(1, code, out)
        self.assertIn("FAIL  #1 status=Shipped: no option 'Shipped'", out)
        self.assertEqual([], gh.mutations())

    def test_iteration_value_resolves_against_completed_buckets_too(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "sprint", "sprint 1"))
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("o=it_1", gh.mutations()[0])

    def test_scalar_write_branches_bind_their_typed_variables(self):
        gh = apply_gh(apply_page(apply_item(1)))
        cs = self.changeset(("1", "est effort", "5"), ("1", "target", "2026-06-18"), ("1", "notes", "hello"))
        code, out = run_main(apply_mod, self.argv(cs, "--apply"), gh)
        self.assertEqual(0, code, out)
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
        gh = apply_gh(apply_page(apply_item(1, notes="seed")))
        code, out = run_main(apply_mod, self.argv(self.changeset(("1", "notes", "")), "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("SET   #1 notes=(clear)", out)
        muts = gh.mutations()
        self.assertEqual(1, len(muts))
        self.assertIn("clearProjectV2ItemFieldValue", gh.query_of(muts[0]))
        self.assertIn("f=F_notes", muts[0])

        gh2 = apply_gh(apply_page(apply_item(1, notes="")))
        code, out = run_main(apply_mod, self.argv(self.changeset(("1", "notes", "")), "--apply"), gh2)
        self.assertEqual(0, code, out)
        self.assertIn("already clear", out)
        self.assertEqual([], gh2.mutations())

    def test_blocked_by_posts_to_the_rest_dependencies_endpoint(self):
        gh = apply_gh(
            apply_page(apply_item(1)),
            rest={
                "repos/acme/widgets/issues/2": (0, "77\n"),
                "repos/acme/widgets/issues/1/dependencies/blocked_by": (0, ""),
            },
        )
        cs = self.changeset(("1", "blocked_by", "2"))
        code, out = run_main(apply_mod, self.argv(cs, "--repo", "acme/widgets", "--apply"), gh)
        self.assertEqual(0, code, out)
        self.assertIn("SET   #1 blocked_by=2", out)
        self.assertEqual(
            [
                ["gh", "api", "repos/acme/widgets/issues/2", "--jq", ".id"],
                ["gh", "api", "-X", "POST", "repos/acme/widgets/issues/1/dependencies/blocked_by", "-F", "issue_id=77"],
            ],
            gh.rest_calls(),
        )
        self.assertEqual([], gh.mutations())

    def test_github_token_is_stripped_from_the_gh_environment(self):
        """A repo-scoped GITHUB_TOKEN shadows the project-scoped keyring login."""
        gh = apply_gh(apply_page(apply_item(1)))
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "shadowing-token"}):
            code, out = run_main(apply_mod, self.argv(self.changeset(("1", "status", "Todo"))), gh)
        self.assertEqual(0, code, out)
        self.assertTrue(gh.envs)
        for env in gh.envs:
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertIn("PATH", env, "the rest of the environment still reaches gh")


# --- board-export -----------------------------------------------------------------

EXPORT_FIELDS = {
    "data": {
        "node": {
            "fields": {
                "nodes": [
                    {
                        "id": "F_status",
                        "name": "Status",
                        "dataType": "SINGLE_SELECT",
                        "options": [{"id": "opt_todo", "name": "Todo"}],
                    },
                    {"id": "F_effort", "name": "Est Effort", "dataType": "NUMBER"},
                    {"id": "F_labels", "name": "Labels", "dataType": "LABELS"},
                    {
                        "id": "F_sprint",
                        "name": "Sprint",
                        "dataType": "ITERATION",
                        "configuration": {
                            "duration": 14,
                            "iterations": [{"id": "it_2", "title": "Sprint 2", "startDate": "2026-01-15"}],
                            "completedIterations": [{"id": "it_1", "title": "Sprint 1", "startDate": "2026-01-01"}],
                        },
                    },
                    None,
                ]
            }
        }
    }
}

EXPORT_PAGE_1 = {
    "data": {
        "node": {
            "items": {
                "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR1"},
                "nodes": [
                    {
                        "id": "PVTI_1",
                        "content": {
                            "__typename": "Issue",
                            "number": 1,
                            "title": "first",
                            "state": "OPEN",
                            "url": "https://example.invalid/1",
                            "repository": {"nameWithOwner": "acme/widgets"},
                            "labels": {"nodes": [{"name": "bug"}, {"name": "infra"}]},
                            "milestone": {"title": "m1"},
                            "parent": {"number": 4},
                        },
                        "fieldValues": {
                            "nodes": [
                                {
                                    "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                    "name": "Todo",
                                    "field": {"name": "Status"},
                                },
                                {
                                    "__typename": "ProjectV2ItemFieldTextValue",
                                    "text": "ignored",
                                    "field": {"name": "Labels"},
                                },
                            ]
                        },
                    },
                    {"id": "PVTI_d", "content": {"__typename": "DraftIssue", "title": "a draft"}, "fieldValues": {"nodes": []}},
                ],
            }
        }
    }
}

EXPORT_PAGE_2 = {
    "data": {
        "node": {
            "items": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "id": "PVTI_2",
                        "content": {"__typename": "Issue", "number": 2, "title": "second", "state": "CLOSED"},
                        "fieldValues": {"nodes": [{"__typename": "ProjectV2ItemFieldNumberValue", "number": 0, "field": {"name": "Est Effort"}}]},
                    }
                ],
            }
        }
    }
}


def export_gh():
    return Gh(
        graphql=[
            ("projectV2(number:$n)", project_ok),
            ("fields(first:50)", EXPORT_FIELDS),
            ("items(first:100", [EXPORT_PAGE_1, EXPORT_PAGE_2]),
        ]
    )


class Export(unittest.TestCase):
    def test_snapshot_shape_is_a_complete_grid(self):
        gh = export_gh()
        code, out = run_main(export_mod, ["board-export.py", "-o", "acme", "-n", "8"], gh)
        self.assertEqual(0, code, out)
        snap = json.loads(out)
        self.assertEqual(["project", "fields", "items"], list(snap))
        self.assertEqual(
            {"owner": "acme", "owner_type": "user", "number": 8, "id": "PVT_board", "title": "widgets board"},
            snap["project"],
        )
        self.assertEqual([1, 2], [i["number"] for i in snap["items"]], "draft issues are dropped")

        first = snap["items"][0]
        self.assertEqual(["bug", "infra"], first["labels"])
        self.assertEqual("m1", first["milestone"])
        self.assertEqual(4, first["parent"])
        self.assertEqual("acme/widgets", first["repo"])
        self.assertEqual({"Status": "Todo", "Est Effort": None, "Sprint": None}, first["fields"])

        second = snap["items"][1]
        self.assertEqual({"Status": None, "Est Effort": 0, "Sprint": None}, second["fields"])
        self.assertEqual([], second["labels"])
        self.assertIsNone(second["milestone"])
        self.assertIsNone(second["parent"])

    def test_iteration_buckets_merge_and_non_operating_fields_stay_out_of_the_grid(self):
        gh = export_gh()
        code, out = run_main(export_mod, ["board-export.py", "-o", "acme", "-n", "8"], gh)
        self.assertEqual(0, code, out)
        snap = json.loads(out)
        by_name = {f["name"]: f for f in snap["fields"]}
        self.assertEqual("Labels", by_name["Labels"]["name"], "the field itself is still described")
        self.assertNotIn("Labels", snap["items"][0]["fields"])
        self.assertEqual(["Sprint 2", "Sprint 1"], [i["title"] for i in by_name["Sprint"]["iterations"]])
        self.assertEqual([{"id": "opt_todo", "name": "Todo"}], by_name["Status"]["options"])

    def test_pagination_passes_the_cursor_to_the_second_page(self):
        gh = export_gh()
        code, out = run_main(export_mod, ["board-export.py", "-o", "acme", "-n", "8"], gh)
        self.assertEqual(0, code, out)
        pages = gh.matching("items(first:100")
        self.assertEqual(2, len(pages))
        self.assertNotIn("after=CURSOR1", pages[0])
        self.assertIn("after=CURSOR1", pages[1])
        self.assertIn("id=PVT_board", pages[1])
        self.assertEqual([1, 2], [i["number"] for i in json.loads(out)["items"]])

    def test_out_writes_the_same_json_to_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snapshot.json")
            gh = export_gh()
            code, out = run_main(export_mod, ["board-export.py", "-o", "acme", "-n", "8", "--out", path], gh)
            self.assertEqual(0, code, out)
            self.assertEqual("", out, "stdout stays clean when writing a file")
            with open(path) as fh:
                written = json.load(fh)
        self.assertEqual([1, 2], [i["number"] for i in written["items"]])

    def test_org_owner_type_switches_the_graphql_scope(self):
        gh = export_gh()
        code, out = run_main(
            export_mod, ["board-export.py", "-o", "acme", "-n", "8", "--owner-type", "org"], gh
        )
        self.assertEqual(0, code, out)
        lookup = gh.matching("projectV2(number:$n)")[0]
        self.assertIn("organization(login", gh.query_of(lookup))
        self.assertIn("o=acme", lookup)
        self.assertEqual(["-F", "n=8"], lookup[-2:], "an Int! var needs -F, not -f")
        self.assertEqual("org", json.loads(out)["project"]["owner_type"])


# --- board-fields -----------------------------------------------------------------


def fields_gh(project=project_ok):
    return Gh(graphql=[("projectV2(number:$n)", project), ("fields(first:50)", EXPORT_FIELDS)])


class Fields(unittest.TestCase):
    def test_collect_merges_iteration_buckets_and_keeps_duration(self):
        gh = fields_gh()
        with mock.patch("subprocess.run", gh):
            data = fields_mod.collect("acme", 8, "user")
        by_name = {f["name"]: f for f in data["fields"]}
        self.assertEqual(
            {"owner": "acme", "number": 8, "id": "PVT_board", "title": "widgets board"}, data["project"]
        )
        self.assertEqual(["Sprint 2", "Sprint 1"], [i["title"] for i in by_name["Sprint"]["iterations"]])
        self.assertEqual(14, by_name["Sprint"]["duration"])
        self.assertEqual([{"id": "opt_todo", "name": "Todo"}], by_name["Status"]["options"])
        self.assertNotIn("options", by_name["Est Effort"])
        self.assertNotIn("iterations", by_name["Status"])

    def test_collect_argv_targets_the_org_scope_with_an_int_number(self):
        gh = fields_gh()
        with mock.patch("subprocess.run", gh):
            fields_mod.collect("acme", 8, "org")
        lookup = gh.matching("projectV2(number:$n)")[0]
        self.assertIn("organization(login", gh.query_of(lookup))
        self.assertEqual(["-F", "n=8"], lookup[-2:], "an Int! var needs -F, not -f")
        self.assertIn("o=acme", lookup)

    def test_missing_project_exits_with_a_message(self):
        gh = fields_gh(project_missing)
        with mock.patch("subprocess.run", gh):
            with self.assertRaises(SystemExit) as cm:
                fields_mod.collect("acme", 8, "user")
        self.assertIn("acme#8 not found", str(cm.exception.code))
        self.assertEqual(1, len(gh.calls), "no field query is issued once the project is missing")

    def test_json_output_round_trips_to_collect(self):
        gh = fields_gh()
        with mock.patch("subprocess.run", gh):
            expected = fields_mod.collect("acme", 8, "user")
        code, out = run_main(fields_mod, ["board-fields.py", "-o", "acme", "-n", "8", "--json"], fields_gh())
        self.assertEqual(0, code, out)
        self.assertEqual(expected, json.loads(out))

    def test_human_table_lists_option_and_iteration_values(self):
        code, out = run_main(fields_mod, ["board-fields.py", "-o", "acme", "-n", "8"], fields_gh())
        self.assertEqual(0, code, out)
        self.assertIn("• Status  [SINGLE_SELECT]  id=F_status", out)
        self.assertIn("id=opt_todo", out)
        self.assertIn("Sprint 1", out)
        self.assertIn("start=2026-01-01", out)
        self.assertIn("4 fields.", out)


if __name__ == "__main__":
    unittest.main()
