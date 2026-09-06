"""The planning-desk toolkit: parsing, transforms, JSON shapes, and gating exit codes.

Both boundaries are faked: `subprocess.run` becomes an argv dispatcher (so a test
pins the argv a script BUILT, not just the value it got back), and the plans tree is
a tempdir wired in by patching each module's `PLANS_DIR` / `README`.

Those globals are not shared the way the imports suggest -- `coverage.py` loads its
OWN reconcile/conformance via `_load_sibling` and `sync-bodies.py` rebinds
`PLANS_DIR` -- so `point_reconcile_at` patches every live copy.

`sequence.py` and `deps-suggest.py` return 0 unconditionally; the tests assert that,
not SKILL.md's "each with a gating exit code".
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

import _repo  # noqa: E402
import conformance  # noqa: E402
import reconcile  # noqa: E402
import sequence  # noqa: E402


def _load(name: str, filename: str):
    """Load a script whose filename is not a legal module name (or would shadow a
    well-known package). Registered in sys.modules before exec so relative state
    inside the module is stable."""
    spec = importlib.util.spec_from_file_location(name, UTILS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# `coverage` would collide with the well-known third-party package name.
pd_coverage = _load("pd_coverage", "coverage.py")
deps_suggest = _load("deps_suggest", "deps-suggest.py")
sync_bodies = _load("sync_bodies", "sync-bodies.py")
evidence_audit = _load("evidence_audit", "evidence-audit.py")


# --------------------------------------------------------------------------- fakes


class _Completed:
    def __init__(self, stdout: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class FakeGh:
    """One dispatcher for every `gh` shape the toolkit issues. Records argv."""

    def __init__(
        self,
        *,
        repo: str = "acme/widgets",
        issues_open=(),
        issues_closed=(),
        issues_all=(),
        bodies=None,
        milestones_tsv: str = "",
        graphql_pages=(),
    ):
        self.repo = repo
        self.issues = {
            "open": list(issues_open),
            "closed": list(issues_closed),
            "all": list(issues_all),
        }
        self.bodies = bodies or {}
        self.milestones_tsv = milestones_tsv
        self.graphql_pages = list(graphql_pages)
        self.calls: list[list[str]] = []

    def __call__(self, args, **_kwargs):
        args = list(args)
        self.calls.append(args)
        return _Completed(self._stdout(args))

    def argv_starting(self, prefix: list[str]) -> list[list[str]]:
        return [c for c in self.calls if c[: len(prefix)] == prefix]

    def _stdout(self, args: list[str]) -> str:
        if args[:3] == ["gh", "repo", "view"]:
            return self.repo + "\n"
        if args[:3] == ["gh", "issue", "list"]:
            state = args[args.index("--state") + 1]
            return json.dumps(self.issues[state])
        if args[:3] == ["gh", "issue", "view"]:
            return self.bodies[int(args[3])]
        if args[:3] == ["gh", "issue", "edit"]:
            return ""
        if args[:3] == ["gh", "api", "graphql"]:
            return json.dumps(self.graphql_pages.pop(0))
        if args[:2] == ["gh", "api"] and args[2].endswith("/milestones"):
            return self.milestones_tsv
        raise AssertionError(f"unexpected gh call: {args}")


def run_main(module, argv: list[str]):
    """Invoke a script's main() under a faked argv; returns (exit code, stdout)."""
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["script", *argv]):
        with contextlib.redirect_stdout(buf):
            code = module.main()
    return code, buf.getvalue()


class GhCase(unittest.TestCase):
    """Base: `gh` is never reachable, and `repo_slug`'s cache never leaks between tests."""

    def install_gh(self, fake: FakeGh) -> FakeGh:
        _repo.repo_slug.cache_clear()
        self.addCleanup(_repo.repo_slug.cache_clear)
        patcher = mock.patch("subprocess.run", fake)
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def tmpdir(self) -> Path:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return Path(d.name)


# ------------------------------------------------------------------------ fixtures


def write_plan(plans: Path, slug: str, tracking: str | None, body: str | None = None):
    folder = plans / slug
    folder.mkdir(parents=True, exist_ok=True)
    text = f"# {slug}\n\n## Context\n\nSome prose.\n"
    if tracking is not None:
        text += f"\n## Tracking\n\n{tracking}\n"
    text += "\n## Scope\n\nMore prose.\n"
    (folder / "plan.md").write_text(text)
    if body is not None:
        (folder / "issue-body.md").write_text(body)
    return folder


DRIFT_README = """# Plans desk

| Plan | Issue | Notes |
| ---- | ----- | ----- |
| stray-before-marker | #30 | outside any section, must be ignored |

## ACTIVE plans

| Plan | Issue | Notes |
| ---- | ----- | ----- |
| alpha-rollout | #1 | clean |
| beta-widget | (none yet) | no number |
| gamma-probe | #7 | unknown issue |
| delta-sweep | #8 | closed issue |
| epsilon-ghost | #9 | no folder |
| zeta-mismatch | #10 | body says another |
| eta-warned | #12 | epic-flagged lead ref |
| theta-notrack | #13 | no tracking section |

## ARCHIVED (done)

| Plan (archived path) | Issue | Notes |
| --- | --- | --- |
| kappa-old | #20 | properly closed |
| lambda-open | #21 | still open |
| mu-none | enablement (no issue) | nothing to check |
| nu-gone | #22 | unknown issue |
"""

DRIFT_STATES = [
    {"number": 1, "state": "OPEN"},
    {"number": 8, "state": "CLOSED"},
    {"number": 9, "state": "OPEN"},
    {"number": 10, "state": "OPEN"},
    {"number": 11, "state": "OPEN"},
    {"number": 12, "state": "OPEN"},
    {"number": 13, "state": "OPEN"},
    {"number": 14, "state": "OPEN"},
    {"number": 20, "state": "CLOSED"},
    {"number": 21, "state": "OPEN"},
]


def build_drift_tree(base: Path) -> Path:
    plans = base / "plans"
    plans.mkdir()
    (plans / "README.md").write_text(DRIFT_README)
    write_plan(plans, "alpha-rollout", "Tracking issue: #1")
    write_plan(plans, "beta-widget", "Tracking issue: #2")
    write_plan(plans, "gamma-probe", "Tracking issue: #7")
    write_plan(plans, "delta-sweep", "Tracking issue: #8")
    write_plan(plans, "zeta-mismatch", "Tracking issue: #11")
    write_plan(plans, "eta-warned", "Epic #12 owns this stream")
    write_plan(plans, "theta-notrack", None)
    write_plan(plans, "iota-orphan", "Tracking issue: #14")
    return plans


def build_clean_tree(base: Path) -> Path:
    plans = base / "plans"
    plans.mkdir()
    (plans / "README.md").write_text(
        "## ACTIVE plans\n\n"
        "| Plan | Issue |\n| --- | --- |\n| alpha-rollout | #1 |\n\n"
        "## ARCHIVED (done)\n\n| Plan (archived path) | Issue |\n| --- | --- |\n"
    )
    write_plan(plans, "alpha-rollout", "Tracking issue: #1")
    return plans


def point_reconcile_at(case: unittest.TestCase, plans: Path):
    """Patch every live copy of reconcile's globals -- coverage.py holds its own."""
    for mod in (reconcile, pd_coverage.reconcile):
        case.enterContext(mock.patch.object(mod, "PLANS_DIR", plans))
        case.enterContext(mock.patch.object(mod, "README", plans / "README.md"))
    case.enterContext(mock.patch.object(sync_bodies, "PLANS_DIR", plans))


# ---------------------------------------------------------------------- conformance


class ConformanceEpicDetection(unittest.TestCase):
    def test_epic_label_marks_an_issue_epic_type(self):
        issue = {"title": "Ship the widget", "labels": [{"name": "epic"}]}
        self.assertTrue(conformance.is_epic_type(issue))

    def test_tracker_title_marks_an_issue_epic_type_without_a_label(self):
        self.assertTrue(conformance.is_epic_type({"title": "Tracking: rollout", "labels": []}))
        self.assertTrue(conformance.is_epic_type({"title": "Epic outline", "labels": []}))

    def test_plain_issue_is_not_epic_type(self):
        issue = {"title": "Fix the widget latch", "labels": [{"name": "bug"}]}
        self.assertFalse(conformance.is_epic_type(issue))


class ConformanceAudit(unittest.TestCase):
    def test_body_with_no_headings_reports_missing_structure(self):
        missing = conformance.audit_issue({"title": "t", "labels": [], "body": "just prose"})
        self.assertEqual(missing, ["no headings / no template structure"])

    def test_missing_acceptance_criteria_only(self):
        body = "## Summary\n\nx\n\n## Dependencies & gates\n\n- none\n"
        missing = conformance.audit_issue({"title": "t", "labels": [], "body": body})
        self.assertEqual(missing, ["Acceptance criteria"])

    def test_missing_gates_only(self):
        body = "## Summary\n\nx\n\n## Acceptance criteria\n\n- it works\n"
        missing = conformance.audit_issue({"title": "t", "labels": [], "body": body})
        self.assertEqual(missing, ["Dependencies & gates"])

    def test_definition_of_done_counts_as_acceptance_criteria(self):
        body = "## Definition of done\n\n- x\n\n## Dependencies & gates\n\n- none\n"
        self.assertEqual(conformance.audit_issue({"title": "t", "labels": [], "body": body}), [])

    def test_epic_is_judged_on_close_when_not_acceptance_criteria(self):
        epic = {"title": "t", "labels": [{"name": "epic"}], "body": "## Close when\n\n- all children done\n"}
        self.assertEqual(conformance.audit_issue(epic), [])
        bare = {"title": "t", "labels": [{"name": "epic"}], "body": "## Summary\n\nx\n"}
        self.assertEqual(conformance.audit_issue(bare), ["Close when (epic acceptance)"])


class ConformanceSeverity(unittest.TestCase):
    def test_missing_acceptance_or_structure_is_critical(self):
        self.assertEqual(conformance.severity(["Acceptance criteria"], False), "CRITICAL")
        self.assertEqual(conformance.severity(["no headings / no template structure"], True), "CRITICAL")

    def test_epic_missing_close_when_is_its_own_band(self):
        # The band name matters: the string carries a lowercase "acceptance", which
        # must NOT be read as the CRITICAL "Acceptance criteria" signal.
        self.assertEqual(conformance.severity(["Close when (epic acceptance)"], True), "EPIC")

    def test_gates_only_gap_is_minor(self):
        self.assertEqual(conformance.severity(["Dependencies & gates"], False), "MINOR")


CONFORMANCE_ISSUES = [
    {"number": 4, "title": "Fix the latch", "labels": [], "body": "## Acceptance criteria\n\n- x\n"},
    {"number": 5, "title": "Add a knob", "labels": [], "body": "no structure at all"},
    {"number": 6, "title": "Tracking: the rollout", "labels": [], "body": "## Summary\n\nx\n"},
    {"number": 7, "title": "Good one", "labels": [], "body": "## Acceptance criteria\n\n- x\n\n## Dependencies & gates\n\n- none\n"},
]


class ConformanceMain(GhCase):
    def test_json_shape_and_descending_order(self):
        gh = self.install_gh(FakeGh(issues_open=CONFORMANCE_ISSUES))
        code, out = run_main(conformance, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(payload["total"], 4)
        self.assertEqual([b["number"] for b in payload["bad"]], [6, 5, 4])
        self.assertEqual(
            payload["bad"][0],
            {
                "number": 6,
                "title": "Tracking: the rollout",
                "epic": True,
                "missing": ["Close when (epic acceptance)"],
                "severity": "EPIC",
            },
        )
        self.assertEqual(payload["bad"][2]["missing"], ["Dependencies & gates"])
        self.assertEqual(payload["bad"][2]["severity"], "MINOR")
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--state") + 1], "open")
        self.assertEqual(listed[listed.index("--limit") + 1], "1000")
        self.assertEqual(listed[listed.index("--json") + 1], "number,title,labels,body")

    def test_all_conformant_exits_zero(self):
        self.install_gh(FakeGh(issues_open=[CONFORMANCE_ISSUES[3]]))
        code, out = run_main(conformance, ["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["bad"], [])

    def test_saturated_issue_list_warns_on_stderr(self):
        rows = [{"number": n, "title": "t", "labels": [], "body": "## Acceptance criteria\n\n## Gates\n"} for n in (1, 2, 3)]
        self.install_gh(FakeGh(issues_open=rows))
        with mock.patch.object(conformance, "ISSUE_LIST_LIMIT", 3):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                conformance.fetch_open_issues()
        self.assertIn("hit the 3-issue limit", err.getvalue())

    def test_unsaturated_issue_list_does_not_warn(self):
        self.install_gh(FakeGh(issues_open=CONFORMANCE_ISSUES))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            conformance.fetch_open_issues()
        self.assertEqual(err.getvalue(), "")


# ------------------------------------------------------------------------- coverage


class CoverageTrivialTagging(unittest.TestCase):
    def test_documentation_label_is_maybe_trivial(self):
        self.assertTrue(pd_coverage.maybe_trivial({"title": "Rewrite the guide", "labels": [{"name": "documentation"}]}))

    def test_small_titled_bug_is_maybe_trivial(self):
        self.assertTrue(pd_coverage.maybe_trivial({"title": "Latch sticks", "labels": [{"name": "bug"}]}))

    def test_broad_scope_bug_is_not_trivial(self):
        self.assertFalse(pd_coverage.maybe_trivial({"title": "Refactor the latch engine", "labels": [{"name": "bug"}]}))

    def test_feature_without_labels_is_not_trivial(self):
        self.assertFalse(pd_coverage.maybe_trivial({"title": "Latch sticks", "labels": []}))


class CoverageCompute(GhCase):
    def setUp(self):
        self.plans = build_drift_tree(self.tmpdir())
        point_reconcile_at(self, self.plans)

    def test_planned_set_comes_from_plan_folder_tracking_refs(self):
        self.assertEqual(pd_coverage.planned_issue_numbers(), {1, 2, 7, 8, 11, 12, 14})

    def test_json_shape_excludes_epics_and_planned_issues(self):
        issues = [
            {"number": 1, "title": "Already planned", "labels": [], "milestone": None},
            {"number": 25, "title": "Tracking: an epic", "labels": [], "milestone": None},
            {"number": 26, "title": "Latch sticks", "labels": [{"name": "bug"}], "milestone": {"title": "m1"}},
            {"number": 27, "title": "Build a new thing", "labels": [], "milestone": None},
        ]
        gh = self.install_gh(FakeGh(issues_open=issues))
        code, out = run_main(pd_coverage, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(payload["planned_count"], 7)
        self.assertEqual(payload["non_epic_count"], 3)
        self.assertEqual(
            payload["unplanned"],
            [
                {"number": 27, "title": "Build a new thing", "milestone": "(no milestone)", "maybe_trivial": False},
                {"number": 26, "title": "Latch sticks", "milestone": "m1", "maybe_trivial": True},
            ],
        )
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--limit") + 1], "1000")
        self.assertEqual(listed[listed.index("--json") + 1], "number,title,labels,milestone")

    def test_fully_covered_backlog_exits_zero(self):
        self.install_gh(FakeGh(issues_open=[{"number": 1, "title": "Planned", "labels": [], "milestone": None}]))
        code, out = run_main(pd_coverage, ["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["unplanned"], [])


# ------------------------------------------------------------------------ reconcile


class ReconcileReadmeParsing(GhCase):
    def setUp(self):
        self.plans = build_drift_tree(self.tmpdir())
        point_reconcile_at(self, self.plans)

    def test_rows_split_on_the_section_markers(self):
        active, archived = reconcile.parse_readme_rows()
        self.assertEqual(
            [r["plan"] for r in active],
            ["alpha-rollout", "beta-widget", "gamma-probe", "delta-sweep",
             "epsilon-ghost", "zeta-mismatch", "eta-warned", "theta-notrack"],
        )
        self.assertEqual([r["plan"] for r in archived], ["kappa-old", "lambda-open", "mu-none", "nu-gone"])

    def test_header_separator_and_pre_marker_rows_are_skipped(self):
        active, archived = reconcile.parse_readme_rows()
        names = {r["plan"] for r in active} | {r["plan"] for r in archived}
        self.assertNotIn("stray-before-marker", names)
        self.assertNotIn("Plan", names)
        self.assertNotIn("Plan (archived path)", names)
        self.assertFalse([n for n in names if set(n) <= {"-", " ", ":"}])

    def test_issue_numbers_are_extracted_per_row(self):
        active, archived = reconcile.parse_readme_rows()
        by_plan = {r["plan"]: r["issues"] for r in active + archived}
        self.assertEqual(by_plan["alpha-rollout"], [1])
        self.assertEqual(by_plan["beta-widget"], [])
        self.assertEqual(by_plan["mu-none"], [])
        self.assertEqual(by_plan["nu-gone"], [22])


class ReconcilePlanBodyIssue(GhCase):
    def setUp(self):
        self.plans = build_drift_tree(self.tmpdir())
        point_reconcile_at(self, self.plans)

    def test_clean_tracking_section_yields_the_issue_and_no_warning(self):
        self.assertEqual(reconcile.plan_body_issue("alpha-rollout"), (1, None))

    def test_epic_signal_before_the_lead_ref_still_parses_but_warns(self):
        issue, warn = reconcile.plan_body_issue("eta-warned")
        self.assertEqual(issue, 12)
        self.assertIn("epic-flagged", warn)

    def test_missing_tracking_section_yields_no_issue(self):
        self.assertEqual(reconcile.plan_body_issue("theta-notrack"), (None, "no `## Tracking` section"))

    def test_missing_folder_yields_no_plan_md(self):
        self.assertEqual(reconcile.plan_body_issue("epsilon-ghost"), (None, "no plan.md"))


class ReconcileDrift(GhCase):
    def setUp(self):
        self.plans = build_drift_tree(self.tmpdir())
        point_reconcile_at(self, self.plans)
        self.gh = self.install_gh(FakeGh(issues_all=DRIFT_STATES))

    def test_every_drift_kind_is_reported_once(self):
        code, out = run_main(reconcile, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        found = {(d["kind"], d["plan"]) for d in payload["drift"]}
        self.assertEqual(len(payload["drift"]), 8)  # set() alone would hide a duplicate
        self.assertEqual(
            found,
            {
                ("active-no-issue", "beta-widget"),
                ("issue-missing", "gamma-probe"),
                ("active-but-closed", "delta-sweep"),
                ("row-no-folder", "epsilon-ghost"),
                ("body-mismatch", "zeta-mismatch"),
                ("archived-but-open", "lambda-open"),
                ("issue-missing", "nu-gone"),
                ("folder-no-row", "iota-orphan"),
            },
        )

    def test_body_mismatch_names_both_numbers(self):
        _code, out = run_main(reconcile, ["--json"])
        d = next(d for d in json.loads(out)["drift"] if d["kind"] == "body-mismatch")
        self.assertEqual(d["issue"], 10)
        self.assertIn("#11", d["detail"])

    def test_json_shape_carries_ok_warns_and_counts(self):
        _code, out = run_main(reconcile, ["--json"])
        payload = json.loads(out)
        self.assertEqual(sorted(payload), ["counts", "drift", "ok", "warns"])
        self.assertEqual(payload["counts"], {"active": 8, "archived": 4, "folders": 8})
        self.assertEqual(
            {w["plan"] for w in payload["warns"]},
            {"epsilon-ghost", "eta-warned", "theta-notrack"},
        )
        # `ok` records only the "tracking issue is OPEN" check, so a row can be OK there
        # and still carry folder/body drift.
        self.assertEqual(
            [line.split()[0] for line in payload["ok"]],
            ["alpha-rollout", "epsilon-ghost", "zeta-mismatch", "eta-warned", "theta-notrack"],
        )

    def test_it_asks_gh_for_every_state(self):
        run_main(reconcile, ["--json"])
        listed = self.gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--state") + 1], "all")
        self.assertEqual(listed[listed.index("--limit") + 1], "1000")
        self.assertEqual(listed[listed.index("--json") + 1], "number,state")


class ReconcileClean(GhCase):
    def test_no_drift_exits_zero(self):
        plans = build_clean_tree(self.tmpdir())
        point_reconcile_at(self, plans)
        self.install_gh(FakeGh(issues_all=[{"number": 1, "state": "OPEN"}]))
        code, out = run_main(reconcile, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["drift"], [])
        self.assertEqual(payload["counts"], {"active": 1, "archived": 0, "folders": 1})


# ------------------------------------------------------------------------- sequence


def _issue(number, title="Work item", labels=(), milestone=None):
    return {
        "number": number,
        "title": title,
        "labels": [{"name": n} for n in labels],
        "milestone": {"title": milestone} if milestone else None,
    }


def _graph(blocked_by=(), blocking=(), children=()):
    return {"blocked_by": list(blocked_by), "blocking": list(blocking), "children": list(children)}


class SequenceClassify(unittest.TestCase):
    DUE = {"m1": "2026-07-01"}

    def test_on_hold_beats_a_blocking_edge(self):
        tiers, _ = sequence.classify(
            [_issue(1, labels=("on-hold:owner",), milestone="m1")],
            self.DUE,
            {1: _graph(blocked_by=[2])},
            {1},
        )
        self.assertEqual([r["number"] for r in tiers["DEFERRED"]], [1])
        self.assertEqual(tiers["BLOCKED"], [])

    def test_an_open_blocker_sends_a_dated_planned_issue_to_blocked(self):
        tiers, _ = sequence.classify([_issue(1, milestone="m1")], self.DUE, {1: _graph(blocked_by=[2])}, {1})
        self.assertEqual([r["number"] for r in tiers["BLOCKED"]], [1])
        self.assertEqual(tiers["NOW"], [])

    def test_now_needs_a_dated_milestone_and_a_plan(self):
        tiers, _ = sequence.classify([_issue(1, milestone="m1")], self.DUE, {}, {1})
        self.assertEqual([r["number"] for r in tiers["NOW"]], [1])

    def test_dated_milestone_without_a_plan_falls_to_next(self):
        tiers, _ = sequence.classify([_issue(1, milestone="m1")], self.DUE, {}, set())
        self.assertEqual([r["number"] for r in tiers["NEXT"]], [1])

    def test_plan_on_an_undated_milestone_falls_to_next(self):
        tiers, _ = sequence.classify([_issue(1, milestone="m9")], self.DUE, {}, {1})
        self.assertEqual([r["number"] for r in tiers["NEXT"]], [1])

    def test_epics_are_excluded_from_every_tier_and_listed(self):
        tiers, epics = sequence.classify(
            [_issue(1, title="Tracking: the rollout", milestone="m1"), _issue(2, milestone="m1")],
            self.DUE,
            {},
            {1, 2},
        )
        self.assertEqual(epics, [1])
        self.assertEqual([r["number"] for r in tiers["NOW"]], [2])

    def test_row_carries_gates_leverage_and_due(self):
        tiers, _ = sequence.classify(
            [_issue(3, labels=("gate:owner", "chore"), milestone="m1")],
            self.DUE,
            {3: _graph(blocking=[4, 5], children=[6])},
            {3},
        )
        row = tiers["NOW"][0]
        self.assertEqual(row["gates"], ["gate:owner"])
        self.assertEqual(row["leverage"], 3)
        self.assertEqual(row["due"], "2026-07-01")

    def test_undated_milestone_row_gets_the_sentinel_due(self):
        tiers, _ = sequence.classify([_issue(1)], self.DUE, {}, set())
        self.assertEqual(tiers["NEXT"][0]["due"], sequence.UNDATED)


class SequenceSortKey(unittest.TestCase):
    def _row(self, number, due=sequence.UNDATED, gates=(), leverage=0, planned=False):
        return {"number": number, "due": due, "gates": list(gates), "leverage": leverage, "planned": planned}

    def test_ordering_is_due_then_gates_then_leverage_then_plan_then_number(self):
        rows = [
            self._row(5, due="2026-07-01"),
            self._row(4, due="2026-06-01"),
            self._row(3, due="2026-07-01", gates=["gate:owner"]),
            self._row(2, due="2026-07-01", leverage=9),
            self._row(1, due="2026-07-01", planned=True),
        ]
        self.assertEqual([r["number"] for r in sorted(rows, key=sequence.sort_key)], [4, 3, 2, 1, 5])

    def test_number_breaks_an_otherwise_exact_tie(self):
        rows = [self._row(9), self._row(2)]
        self.assertEqual([r["number"] for r in sorted(rows, key=sequence.sort_key)], [2, 9])


def _graph_page(nodes, has_next=False, cursor=None):
    return {
        "data": {
            "repository": {
                "issues": {"nodes": nodes, "pageInfo": {"hasNextPage": has_next, "endCursor": cursor}}
            }
        }
    }


def _graph_node(number, blocked_by=(), blocking=(), children=()):
    return {
        "number": number,
        "blockedBy": {"nodes": [{"number": n, "state": s} for n, s in blocked_by]},
        "blocking": {"nodes": [{"number": n} for n in blocking]},
        "subIssues": {"nodes": [{"number": n} for n in children]},
    }


class SequenceFetching(GhCase):
    def test_graph_paginates_and_keeps_only_open_blockers(self):
        gh = self.install_gh(
            FakeGh(
                graphql_pages=[
                    _graph_page([_graph_node(1, blocked_by=[(2, "OPEN"), (3, "CLOSED")])], has_next=True, cursor="C1"),
                    _graph_page([_graph_node(4, blocking=[5], children=[6])]),
                ]
            )
        )
        graph = sequence.fetch_graph()
        self.assertEqual(graph[1]["blocked_by"], [2])
        self.assertEqual(graph[4], {"blocked_by": [], "blocking": [5], "children": [6]})
        pages = gh.argv_starting(["gh", "api", "graphql"])
        self.assertEqual(len(pages), 2)
        self.assertIn("-F", pages[0])
        self.assertEqual(pages[0][pages[0].index("-F") + 1], "cursor=null")
        self.assertIn("cursor=C1", pages[1])

    def test_milestone_due_dates_are_parsed_from_tsv_and_truncated(self):
        gh = self.install_gh(FakeGh(milestones_tsv="m1\t2026-07-01T00:00:00Z\nm2\t2026-08-15T12:00:00Z\n"))
        self.assertEqual(sequence.fetch_milestone_due(), {"m1": "2026-07-01", "m2": "2026-08-15"})
        api = gh.argv_starting(["gh", "api"])[0]
        self.assertEqual(api[2], "repos/acme/widgets/milestones")


class SequenceMain(GhCase):
    def test_json_shape_and_exit_zero_even_with_blocked_work(self):
        plans = build_clean_tree(self.tmpdir())
        point_reconcile_at(self, plans)
        gh = self.install_gh(
            FakeGh(
                issues_open=[_issue(1, milestone="m1"), _issue(2, title="Tracking: epic")],
                milestones_tsv="m1\t2026-07-01T00:00:00Z\n",
                graphql_pages=[_graph_page([_graph_node(1, blocked_by=[(3, "OPEN")])])],
            )
        )
        code, out = run_main(sequence, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(payload), ["epics", "tiers"])
        self.assertEqual(payload["epics"], [2])
        self.assertEqual([r["number"] for r in payload["tiers"]["BLOCKED"]], [1])
        self.assertEqual(sorted(payload["tiers"]), ["BLOCKED", "DEFERRED", "NEXT", "NOW"])
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--limit") + 1], "1000")
        self.assertEqual(listed[listed.index("--json") + 1], "number,title,labels,milestone")


# --------------------------------------------------------------------- deps-suggest


class DepsHarvest(unittest.TestCase):
    ISSUES = [
        {"number": 1, "title": "a", "body": "This one is blocked by #1 somehow."},
        {"number": 2, "title": "b", "body": "It depends on #5 for the latch."},
        {"number": 3, "title": "c", "body": "Part of it; requires #6 for the latch."},
        {"number": 4, "title": "d", "body": "Work is blocked by #9 today and still waiting on #9 tomorrow."},
        {"number": 5, "title": "e", "body": "This one needs #2 before it starts."},
    ]

    def harvest(self, native=frozenset()):
        return deps_suggest.harvest(self.ISSUES, set(native))

    def test_self_reference_is_dropped(self):
        self.assertNotIn((1, 1), [(c["blocked"], c["blocker"]) for c in self.harvest()])

    def test_an_existing_native_edge_is_dropped(self):
        self.assertNotIn((2, 5), [(c["blocked"], c["blocker"]) for c in self.harvest({(2, 5)})])

    def test_the_same_edge_without_a_native_record_is_kept(self):
        self.assertIn((2, 5), [(c["blocked"], c["blocker"]) for c in self.harvest()])

    def test_hierarchy_phrasing_near_the_ref_is_dropped(self):
        self.assertNotIn((3, 6), [(c["blocked"], c["blocker"]) for c in self.harvest()])

    def test_a_repeated_edge_is_emitted_once(self):
        pairs = [(c["blocked"], c["blocker"]) for c in self.harvest()]
        self.assertEqual(pairs.count((4, 9)), 1)

    def test_blocker_open_flag_tracks_the_open_set(self):
        by_pair = {(c["blocked"], c["blocker"]): c for c in self.harvest()}
        self.assertFalse(by_pair[(4, 9)]["blocker_open"])
        self.assertTrue(by_pair[(5, 2)]["blocker_open"])

    def test_candidates_are_sorted_by_blocked_then_blocker(self):
        pairs = [(c["blocked"], c["blocker"]) for c in self.harvest()]
        self.assertEqual(pairs, sorted(pairs))

class DepsSnippet(unittest.TestCase):
    """The context window is +/-24 chars around the match, and EPIC_RE is applied to
    that window -- so how far the window reaches decides which candidates survive."""

    SIGNAL = "blocked by #9"
    NEAR, FAR = "NEARMARK", "FARMARK"
    # FAR starts 40 chars before the match, NEAR 20; the newline proves the collapse.
    BODY = (
        FAR
        + "." * (40 - 20 - len(FAR))
        + NEAR
        + "." * (20 - len(NEAR) - 1)
        + "\n"
        + SIGNAL
        + " and some trailing prose that runs past the window"
    )

    def snippet(self):
        start = self.BODY.index(self.SIGNAL)
        self.assertEqual(start, 40)
        return deps_suggest.snippet(self.BODY, start, start + len(self.SIGNAL))

    def test_context_20_chars_before_the_match_is_kept(self):
        self.assertIn(self.NEAR, self.snippet())

    def test_context_40_chars_before_the_match_is_outside_the_window(self):
        self.assertNotIn(self.FAR, self.snippet())

    def test_context_after_the_match_stops_at_the_window_too(self):
        snip = self.snippet()
        self.assertIn("and some trailing", snip)
        self.assertNotIn("past the window", snip)

    def test_the_snippet_is_collapsed_to_one_line(self):
        self.assertNotIn("\n", self.snippet())


class DepsFetchNativeEdges(GhCase):
    def test_edges_accumulate_across_pages(self):
        gh = self.install_gh(
            FakeGh(
                graphql_pages=[
                    {"data": {"repository": {"issues": {
                        "nodes": [{"number": 1, "blockedBy": {"nodes": [{"number": 2}]}}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "C1"}}}}},
                    {"data": {"repository": {"issues": {
                        "nodes": [{"number": 3, "blockedBy": {"nodes": [{"number": 4}, {"number": 5}]}}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None}}}}},
                ]
            )
        )
        self.assertEqual(deps_suggest.fetch_native_edges(), {(1, 2), (3, 4), (3, 5)})
        pages = gh.argv_starting(["gh", "api", "graphql"])
        self.assertEqual(pages[0][pages[0].index("-F") + 1], "cursor=null")
        self.assertIn("cursor=C1", pages[1])


class DepsMain(GhCase):
    def test_json_is_the_candidate_list_and_the_advisory_never_gates(self):
        gh = self.install_gh(
            FakeGh(
                issues_open=[{"number": 7, "title": "t", "body": "This is blocked by #8 for now."}],
                graphql_pages=[{"data": {"repository": {"issues": {
                    "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}],
            )
        )
        code, out = run_main(deps_suggest, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload[0]["blocked"], 7)
        self.assertEqual(payload[0]["blocker"], 8)
        self.assertFalse(payload[0]["blocker_open"])
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--limit") + 1], "1000")
        self.assertEqual(listed[listed.index("--json") + 1], "number,title,body")

    def test_exit_is_zero_with_no_candidates_too(self):
        self.install_gh(
            FakeGh(
                issues_open=[{"number": 7, "title": "t", "body": "nothing here"}],
                graphql_pages=[{"data": {"repository": {"issues": {
                    "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}],
            )
        )
        code, out = run_main(deps_suggest, ["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [])


# ---------------------------------------------------------------------- sync-bodies


class SyncNormalize(unittest.TestCase):
    def test_crlf_becomes_lf(self):
        self.assertEqual(sync_bodies.normalize("a\r\nb\r\n"), "a\nb\n")

    def test_trailing_whitespace_per_line_is_stripped(self):
        self.assertEqual(sync_bodies.normalize("a   \nb\t\n"), "a\nb\n")

    def test_trailing_blank_lines_collapse_to_one_newline(self):
        self.assertEqual(sync_bodies.normalize("a\n\n\n\n"), "a\n")

    def test_a_body_with_no_trailing_newline_gains_one(self):
        self.assertEqual(sync_bodies.normalize("a"), "a\n")


class SyncShortDiff(unittest.TestCase):
    def test_a_long_diff_is_capped_with_a_remainder_line(self):
        local = "\n".join(f"local {n}" for n in range(40)) + "\n"
        remote = "\n".join(f"remote {n}" for n in range(40)) + "\n"
        lines = sync_bodies.short_diff(local, remote)
        self.assertEqual(len(lines), sync_bodies.DIFF_CAP + 1)
        self.assertTrue(lines[-1].startswith("... ("))
        self.assertTrue(lines[-1].endswith("more diff lines)"))

    def test_a_short_diff_is_returned_whole(self):
        lines = sync_bodies.short_diff("a\n", "b\n")
        self.assertLessEqual(len(lines), sync_bodies.DIFF_CAP)
        self.assertIn("+b", lines)


def build_sync_tree(base: Path) -> Path:
    plans = base / "plans"
    plans.mkdir()
    (plans / "README.md").write_text("## ACTIVE plans\n")
    write_plan(plans, "s-clean", "Tracking issue: #1", body="Same body\n")
    write_plan(plans, "s-drift", "Tracking issue: #2", body="Local body\n")
    write_plan(plans, "s-nofile", "Tracking issue: #3")
    write_plan(plans, "s-noissue", None)
    return plans


SYNC_BODIES = {1: "Same body\n", 2: "Remote body\n", 3: "Seeded from remote\n"}


class SyncBodies(GhCase):
    def setUp(self):
        self.plans = build_sync_tree(self.tmpdir())
        point_reconcile_at(self, self.plans)
        self.gh = self.install_gh(FakeGh(bodies=SYNC_BODIES))

    def test_classify_covers_all_four_statuses(self):
        statuses = {slug: sync_bodies.classify(slug)["status"] for slug in sorted(reconcile.disk_folders())}
        self.assertEqual(
            statuses,
            {
                "s-clean": "in-sync",
                "s-drift": "DIFFERS",
                "s-nofile": "no issue-body.md",
                "s-noissue": "no tracking issue",
            },
        )

    def test_json_shape_and_gate_on_drift(self):
        code, out = run_main(sync_bodies, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(
            payload,
            [
                {"slug": "s-clean", "issue": 1, "status": "in-sync"},
                {"slug": "s-drift", "issue": 2, "status": "DIFFERS"},
                {"slug": "s-nofile", "issue": 3, "status": "no issue-body.md"},
                {"slug": "s-noissue", "issue": None, "status": "no tracking issue"},
            ],
        )

    def test_no_drift_exits_zero(self):
        (self.plans / "s-drift" / "issue-body.md").write_text("Remote body\n")
        code, _out = run_main(sync_bodies, ["--json"])
        self.assertEqual(code, 0)

    def test_push_edits_only_the_drifting_issue(self):
        code, _out = run_main(sync_bodies, ["--push"])
        edits = self.gh.argv_starting(["gh", "issue", "edit"])
        self.assertEqual(code, 0)
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0][3], "2")
        self.assertEqual(edits[0][edits[0].index("--body-file") + 1], str(self.plans / "s-drift" / "issue-body.md"))

    def test_the_body_read_is_the_exact_documented_gh_invocation(self):
        sync_bodies.classify("s-drift")
        self.assertEqual(
            self.gh.argv_starting(["gh", "issue", "view"])[0],
            ["gh", "issue", "view", "2", "--json", "body", "--jq", ".body"],
        )

    def test_pull_seeds_every_folder_that_has_a_tracking_issue(self):
        code, _out = run_main(sync_bodies, ["--pull"])
        self.assertEqual(code, 0)
        self.assertEqual((self.plans / "s-drift" / "issue-body.md").read_text(), "Remote body\n")
        self.assertEqual((self.plans / "s-nofile" / "issue-body.md").read_text(), "Seeded from remote\n")
        self.assertFalse((self.plans / "s-noissue" / "issue-body.md").exists())
        self.assertEqual(self.gh.argv_starting(["gh", "issue", "edit"]), [])


# ------------------------------------------------------------------- evidence-audit


def _closed(number, closed_at, prs=(), comments=()):
    return {
        "number": number,
        "title": f"Closed item {number}",
        "closedAt": closed_at,
        "closedByPullRequestsReferences": [{"number": p} for p in prs],
        "comments": [{"body": c} for c in comments],
    }


CLOSED_ISSUES = [
    _closed(11, "2026-07-05T10:00:00Z", prs=[100]),
    _closed(12, "2026-07-04T10:00:00Z", comments=["verified against staging"]),
    _closed(13, "2026-07-03T10:00:00Z", comments=["looks fine to me"]),
    _closed(14, "2026-06-01T10:00:00Z"),
    _closed(15, "2026-07-02T10:00:00Z", comments=[]),
]


class EvidenceDetection(unittest.TestCase):
    def test_a_closing_pr_is_strong_evidence(self):
        self.assertTrue(evidence_audit.closed_with_evidence(CLOSED_ISSUES[0]))

    def test_an_evidence_bearing_comment_is_soft_evidence(self):
        self.assertTrue(evidence_audit.closed_with_evidence(CLOSED_ISSUES[1]))

    def test_a_bare_comment_is_not_evidence(self):
        self.assertFalse(evidence_audit.closed_with_evidence(CLOSED_ISSUES[2]))

    def test_no_pr_and_no_comments_is_not_evidence(self):
        self.assertFalse(evidence_audit.closed_with_evidence(CLOSED_ISSUES[4]))


class EvidenceAudit(unittest.TestCase):
    def test_flagged_is_sorted_by_descending_number(self):
        result = evidence_audit.audit(CLOSED_ISSUES, None)
        self.assertEqual(result["checked"], 5)
        self.assertEqual([f["number"] for f in result["flagged"]], [15, 14, 13])

    def test_since_filters_on_the_closed_date(self):
        result = evidence_audit.audit(CLOSED_ISSUES, "2026-07-01")
        self.assertEqual(result["checked"], 4)
        self.assertEqual([f["number"] for f in result["flagged"]], [15, 13])

    def test_the_boundary_date_is_inclusive(self):
        result = evidence_audit.audit(CLOSED_ISSUES, "2026-06-01")
        self.assertEqual(result["checked"], 5)


class EvidenceMain(GhCase):
    def test_json_shape_and_gate_on_flags(self):
        gh = self.install_gh(FakeGh(issues_closed=CLOSED_ISSUES))
        code, out = run_main(evidence_audit, ["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(sorted(payload), ["checked", "flagged"])
        self.assertEqual(payload["flagged"][0], {"number": 15, "title": "Closed item 15", "closedAt": "2026-07-02T10:00:00Z"})
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--state") + 1], "closed")
        self.assertEqual(listed[listed.index("--limit") + 1], str(evidence_audit.DEFAULT_LIMIT))
        self.assertEqual(
            listed[listed.index("--json") + 1],
            "number,title,closedAt,closedByPullRequestsReferences,comments",
        )

    def test_limit_reaches_the_gh_argv(self):
        gh = self.install_gh(FakeGh(issues_closed=CLOSED_ISSUES))
        run_main(evidence_audit, ["--limit", "7", "--json"])
        listed = gh.argv_starting(["gh", "issue", "list"])[0]
        self.assertEqual(listed[listed.index("--limit") + 1], "7")

    def test_all_covered_exits_zero(self):
        self.install_gh(FakeGh(issues_closed=[CLOSED_ISSUES[0], CLOSED_ISSUES[1]]))
        code, out = run_main(evidence_audit, ["--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["flagged"], [])


# ---------------------------------------------------------------------------- _repo


class RepoSlug(GhCase):
    def test_a_slug_with_no_slash_is_refused(self):
        self.install_gh(FakeGh(repo="widgets"))
        with self.assertRaises(RuntimeError):
            _repo.repo_slug()

    def test_owner_and_name_split_on_the_first_slash(self):
        self.install_gh(FakeGh(repo="acme/widgets"))
        self.assertEqual(_repo.owner_name(), ("acme", "widgets"))

    def test_the_slug_read_is_the_exact_documented_gh_invocation(self):
        gh = self.install_gh(FakeGh(repo="acme/widgets"))
        _repo.repo_slug()
        self.assertEqual(
            gh.calls[0],
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        )

    def test_the_slug_is_fetched_once_and_cached(self):
        gh = self.install_gh(FakeGh(repo="acme/widgets"))
        _repo.repo_slug()
        _repo.repo_slug()
        self.assertEqual(len(gh.argv_starting(["gh", "repo", "view"])), 1)


class RepoGraphql(GhCase):
    def test_none_is_sent_as_typed_null_and_values_as_raw_strings(self):
        gh = self.install_gh(FakeGh(graphql_pages=[{"data": {}}]))
        _repo.graphql("query($cursor: String){x}", owner="acme", cursor=None)
        args = gh.argv_starting(["gh", "api", "graphql"])[0]
        self.assertEqual(args[:5], ["gh", "api", "graphql", "-f", "query=query($cursor: String){x}"])
        self.assertEqual(args[5:], ["-f", "owner=acme", "-F", "cursor=null"])

    def test_the_response_is_parsed_as_json(self):
        self.install_gh(FakeGh(graphql_pages=[{"data": {"ok": True}}]))
        self.assertEqual(_repo.graphql("{x}"), {"data": {"ok": True}})


if __name__ == "__main__":
    unittest.main()
