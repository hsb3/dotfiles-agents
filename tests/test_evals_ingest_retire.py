"""Hermetic tests for the retire-and-filter lifecycle of a dropped `extenders` unit.

No PocketBase, no network, no sqlite: fake clients implementing only the methods the code
under test calls stand in for evals/pb.py's PB, and report.py is driven through the
`list_all(coll)` shape its own FixtureSource uses.

Covers all three halves of the lifecycle: evals/ingest.py flags a slug the tree no longer
defines (`retired=True`, nothing deleted), a re-ingest of a returning slug clears the flag,
and each of the four consumers drops retired rows in Python. The live-slug predicate is
derived by RUNNING both `extenders` writers against a recording fake and reading back what
they upserted — recomputing the predicate's own expression would pass no matter how the
writers drift. The writers read the repo's own primitives-core.yaml / externals.yaml,
read-only.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
import ingest as I  # noqa: E402
import load_assessments  # noqa: E402
import load_coverage  # noqa: E402
import load_eval_run  # noqa: E402
import report  # noqa: E402


class FakePB:
    """Stands in for PB with only what the retire pass calls: list_all, update, delete."""

    def __init__(self, extenders, relationships=()):
        self.rows = {
            "extenders": [dict(r) for r in extenders],
            "relationships": [dict(r) for r in relationships],
        }
        self.updated = []
        self.deleted = []

    def list_all(self, coll, flt=None):
        return [dict(r) for r in self.rows[coll]]

    def update(self, coll, rec_id, body):
        self.updated.append((coll, rec_id, body))
        for r in self.rows[coll]:
            if r["id"] == rec_id:
                r.update(body)
        return dict(next(r for r in self.rows[coll] if r["id"] == rec_id))

    def delete(self, coll, rec_id):
        self.deleted.append((coll, rec_id))
        self.rows[coll] = [r for r in self.rows[coll] if r["id"] != rec_id]


class RecordingPB:
    """Records every upsert body; enough of PB to run the two `extenders` writers."""

    def __init__(self):
        self.upserted = []
        self._n = 0

    def upsert(self, coll, flt, body):
        self._n += 1
        self.upserted.append((coll, body))
        return {"id": f"rec{self._n}"}, True

    def list_all(self, coll, flt=None):
        return []

    def delete(self, coll, rec_id):
        pass

    def bodies(self, coll):
        return [b for c, b in self.upserted if c == coll]

    def slugs(self):
        return {b["slug"] for b in self.bodies("extenders")}


class ReferencePB:
    """Serves whole collections to the three loaders' reference fetches."""

    def __init__(self, **collections):
        self.collections = {k: list(v) for k, v in collections.items()}

    def list_all(self, coll, flt=None):
        return [dict(r) for r in self.collections.get(coll, [])]

    def upsert(self, coll, flt, body):
        self.collections.setdefault(coll, []).append(body)
        return {"id": f"{coll}-1"}, True

    def update(self, coll, rec_id, body):
        return body


class CampaignPB(ReferencePB):
    """Records campaign writes while returning stable run ids for response filters."""

    def __init__(self, **collections):
        super().__init__(**collections)
        self.upserted = []

    def upsert(self, coll, flt, body):
        self.upserted.append((coll, flt, body))
        return {"id": "run-1" if coll == "eval_runs" else "response-1"}, False


def row(rec_id, slug, kind="skill", origin="authored", **extra):
    return {"id": rec_id, "slug": slug, "kind": kind, "origin": origin, **extra}


def quiet(fn, *args, **kwargs):
    """Call `fn` with stdout captured; returns the captured text."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


class RetireTest(unittest.TestCase):
    def test_stale_row_is_flagged_retired_and_not_deleted(self):
        pb = FakePB([row("id-live", "handoff"), row("id-stale", "github-project-board")])
        out = quiet(I.retire_extenders, pb, {"handoff"})
        self.assertEqual(pb.deleted, [])
        self.assertEqual(pb.updated, [("extenders", "id-stale", {"retired": True})])
        self.assertIn("github-project-board", out)
        self.assertNotIn("handoff", out)

    def test_dependent_rows_are_never_touched(self):
        """PROCEDURES.md:18 — ingest never touches non-mechanical assessors, job_coverage
        or relationships. Retiring must not reintroduce a cascade through the back door."""
        pb = FakePB(
            [row("id-stale", "github-project-board"), row("id-live", "handoff")],
            relationships=[{"id": "edge-a", "extender_a": "id-stale", "extender_b": "id-live"}],
        )
        quiet(I.retire_extenders, pb, {"handoff"})
        self.assertEqual(pb.deleted, [])
        self.assertEqual([r["id"] for r in pb.rows["relationships"]], ["edge-a"])
        self.assertEqual([c for c, _i, _b in pb.updated], ["extenders"])

    def test_external_origin_row_in_the_live_set_is_kept_live(self):
        pb = FakePB([
            row("id-ext", "pptx", kind="plugin", origin="external"),
            row("id-stale", "github-project-board"),
        ])
        quiet(I.retire_extenders, pb, {"pptx"})
        self.assertEqual([u[1] for u in pb.updated], ["id-stale"])

    def test_dry_run_writes_nothing_and_still_reports_the_stale_slug(self):
        pb = FakePB([row("id-live", "handoff"), row("id-stale", "github-project-board")])
        out = quiet(I.retire_extenders, pb, {"handoff"}, dry_run=True)
        self.assertEqual(pb.updated, [])
        self.assertEqual(pb.deleted, [])
        self.assertIn("github-project-board", out)
        self.assertIn("extenders to retire: 1", out)

    def test_an_already_retired_row_is_not_rewritten(self):
        pb = FakePB([row("id-stale", "github-project-board", retired=True)])
        out = quiet(I.retire_extenders, pb, set())
        self.assertEqual(pb.updated, [])
        self.assertIn("extenders retired: 0", out)


class ReingestClearsFlagTest(unittest.TestCase):
    """A slug that comes back must go live again, or it stays invisible forever."""

    def test_both_writers_upsert_retired_false(self):
        pb = RecordingPB()
        quiet(I.ingest_extenders, pb)
        quiet(I.ingest_externals, pb, {})
        bodies = pb.bodies("extenders")
        self.assertTrue(bodies, "the writers upserted no extenders at all")
        self.assertEqual([b["slug"] for b in bodies if b.get("retired") is not False], [])


class LiveSlugsTest(unittest.TestCase):
    """A predicate narrower than what the writers produce retires rows the same run created;
    a wider one leaves stale rows live. Both directions are pinned by running the writers."""

    def test_matches_exactly_what_the_two_writers_upsert(self):
        pb = RecordingPB()
        quiet(I.ingest_extenders, pb)
        quiet(I.ingest_externals, pb, {})
        written = pb.slugs()
        self.assertTrue(written, "the writers upserted no extenders at all")
        self.assertEqual(sorted(written), sorted(I.live_slugs()))


class MainWiringTest(unittest.TestCase):
    """AC#1: the retire pass runs in the same run that upserts the rest, after both writers."""

    def _run_main(self):
        calls = []

        def record(name, result=None):
            def fn(*args, **kwargs):
                calls.append(name)
                return result
            return fn

        stubs = {
            "PB": record("PB", object()),
            "ingest_frameworks": record("ingest_frameworks", ({}, {})),
            "ingest_extenders": record("ingest_extenders", ({}, {})),
            "ingest_distributions": record("ingest_distributions"),
            "ingest_dimensions": record("ingest_dimensions"),
            "ingest_assessments": record("ingest_assessments"),
            "ingest_sources": record("ingest_sources", {}),
            "ingest_externals": record("ingest_externals"),
            "live_slugs": record("live_slugs", set()),
            "retire_extenders": record("retire_extenders"),
        }
        with contextlib.ExitStack() as stack:
            for name, fn in stubs.items():
                stack.enter_context(mock.patch.object(I, name, fn))
            quiet(I.main)
        return calls

    def test_main_retires(self):
        self.assertIn("retire_extenders", self._run_main())

    def test_main_retires_after_both_extenders_writers(self):
        calls = self._run_main()
        retired = calls.index("retire_extenders")
        self.assertGreater(retired, calls.index("ingest_extenders"))
        self.assertGreater(retired, calls.index("ingest_externals"))


LIVE = row("id-live", "handoff")
RETIRED = row("id-gone", "github-project-board", retired=True)


class ConsumerFilterTest(unittest.TestCase):
    """Retiring only helps if every consumer drops the flagged row; nothing deletes it."""

    def test_report_load_drops_the_retired_unit(self):
        data = report.load(self._report_source())
        self.assertEqual([e["slug"] for e in data["extenders"]], ["handoff"])
        self.assertNotIn("id-gone", data["ext_by_id"])

    def test_report_load_drops_rows_that_reference_the_retired_unit(self):
        """report.py joins through `ext_by_id[...]` unguarded, so a surviving assessment or
        relationship pointing at a filtered-out unit is a KeyError, not a stray row."""
        data = report.load(self._report_source())
        self.assertEqual([a["id"] for a in data["assessments"]], ["a-live"])
        self.assertEqual([r["id"] for r in data["relationships"]], ["e-live"])

    def test_report_renders_without_the_retired_unit(self):
        data = report.load(self._report_source())
        lines, _stats = report.render_coverage_matrix(data)
        self.assertNotIn("github-project-board", "\n".join(lines))

    def _report_source(self):
        fw = {"id": "fw-1", "slug": report.FRAMEWORK_SLUG, "name": "jobs"}
        el = {"id": "el-1", "framework": "fw-1", "slug": "plan-work", "name": "Plan work",
              "sort_order": 0, "element_kind": "job", "description": "", "criteria": "",
              "category": "build-software"}
        return ReferenceSource(
            frameworks=[fw],
            framework_elements=[el],
            extenders=[LIVE, RETIRED],
            sources=[],
            job_coverage=[],
            eval_runs=[],
            assessments=[
                {"id": "a-live", "extender": "id-live", "framework": "fw-1",
                 "element": "el-1", "assessor": report.ASSESSOR, "verdict": "present"},
                {"id": "a-gone", "extender": "id-gone", "framework": "fw-1",
                 "element": "el-1", "assessor": report.ASSESSOR, "verdict": "present"},
            ],
            relationships=[
                {"id": "e-live", "extender_a": "id-live", "extender_b": "id-live",
                 "kind": "duplicative", "evidence": ""},
                {"id": "e-gone", "extender_a": "id-gone", "extender_b": "id-live",
                 "kind": "duplicative", "evidence": ""},
            ],
        )

    def test_load_coverage_reference_drops_the_retired_unit(self):
        pb = ReferencePB(
            frameworks=[{"id": "fw-1", "slug": load_coverage.FRAMEWORK_SLUG}],
            framework_elements=[{"id": "el-1", "framework": "fw-1", "slug": "plan-work"}],
            extenders=[LIVE, RETIRED],
        )
        _fw_id, _elements, extenders = load_coverage.fetch_reference(pb)
        self.assertEqual([e["slug"] for e in extenders], ["handoff"])

    def test_load_assessments_reference_drops_the_retired_unit(self):
        pb = ReferencePB(
            frameworks=[{"id": "fw-1", "slug": "hsb3-skill-archetypes"}],
            framework_elements=[{"id": "el-1", "framework": "fw-1", "slug": "workflow-procedure"}],
            extenders=[LIVE, RETIRED],
        )
        _fws, _els, exts = load_assessments.fetch_reference(pb)
        self.assertEqual(sorted(exts), ["handoff"])

    def test_load_coverage_says_retired_not_not_in_db(self):
        """The row is in the DB; `(not in DB)` would send the operator looking for a
        deleted unit."""
        pb = ReferencePB(
            frameworks=[{"id": "fw-1", "slug": load_coverage.FRAMEWORK_SLUG}],
            framework_elements=[{"id": "el-1", "framework": "fw-1", "slug": "plan-work"}],
            extenders=[LIVE, RETIRED],
        )
        _fw_id, elements, extenders = load_coverage.fetch_reference(pb)
        data = {"mappings": [{"extender": "github-project-board", "jobs": []},
                             {"extender": "never-existed", "jobs": []}]}
        errs = load_coverage.validate_against_db(pb, data, elements, extenders)
        self.assertIn("mappings[0]: unknown extender 'github-project-board' (retired)", errs)
        self.assertIn("mappings[1]: unknown extender 'never-existed' (not in DB)", errs)

    def _eval_run_manifest(self, slug):
        return {
            "run": {"slug": "r1", "kind": "coverage"},
            "responses": [{"role": "scout", "extenders": [slug]}],
        }

    def _load_manifest(self, pb, manifest):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "manifest.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh)
            return quiet(load_eval_run.load_manifest, pb, path)

    def test_load_eval_run_refuses_a_response_naming_a_retired_unit(self):
        pb = ReferencePB(frameworks=[], extenders=[LIVE, RETIRED])
        with self.assertRaises(SystemExit) as caught:
            self._load_manifest(pb, self._eval_run_manifest("github-project-board"))
        self.assertIn("github-project-board", str(caught.exception))
        self.assertIn("retired", str(caught.exception))

    def test_load_eval_run_says_no_such_extender_when_the_slug_is_absent(self):
        pb = ReferencePB(frameworks=[], extenders=[LIVE])
        with self.assertRaises(SystemExit) as caught:
            self._load_manifest(pb, self._eval_run_manifest("never-existed"))
        self.assertIn("no such extender", str(caught.exception))

    def test_load_eval_run_writes_nothing_when_a_response_cannot_resolve(self):
        """The run upsert precedes the response loop, so failing late orphans an eval_runs
        row with no responses that a re-run then silently reuses."""
        pb = ReferencePB(frameworks=[], extenders=[LIVE, RETIRED])
        with self.assertRaises(SystemExit):
            self._load_manifest(pb, self._eval_run_manifest("github-project-board"))
        self.assertEqual(pb.collections.get("eval_runs", []), [])
        self.assertEqual(pb.collections.get("eval_responses", []), [])


class CampaignMeasurementProjectionTest(unittest.TestCase):
    def _load(self, pb, manifest, raw=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "manifest.json")
            with open(path, "wb") as fh:
                fh.write(raw if raw is not None else json.dumps(manifest).encode())
            quiet(load_eval_run.load_manifest, pb, path)

    def _manifest(self, response):
        return {"run": {"slug": "campaign", "kind": "judged"}, "responses": [response]}

    def test_projects_observed_zero_metrics_and_exact_manifest_sha(self):
        raw = b'{"run":{"slug":"campaign","kind":"judged"},"responses":[{"role":"judge","tokens":0,"duration_ms":0}]}'
        pb = CampaignPB(frameworks=[], extenders=[])
        self._load(pb, None, raw)
        body = pb.upserted[-1][2]
        self.assertEqual(body["tokens"], 0)
        self.assertEqual(body["duration_ms"], 0)
        self.assertEqual(body["measurement"], {
            "version": 1,
            "source": "eval-run-manifest",
            "available": {"tokens": True, "duration_ms": True},
            "provenance": {"tokens": "manifest", "duration_ms": "manifest"},
            "execution": {
                "validity": "unknown",
                "reason": "manifest does not attest execution validity",
                "preconditions": None,
            },
            "source_identity": {
                "manifest_file_sha256": "f9adff88286e0986fbde2ae0059d3a39dfd82726ec2579d018830dc30685c121",
                "revision": {"value": None, "available": False},
            },
        })

    def test_reingestion_missing_metric_clears_number_and_marks_it_unavailable(self):
        pb = CampaignPB(frameworks=[], extenders=[])
        self._load(pb, self._manifest({"role": "judge", "tokens": 7, "duration_ms": 11}))
        self._load(pb, self._manifest({"role": "judge", "tokens": 7}))
        body = pb.upserted[-1][2]
        self.assertEqual(body["tokens"], 7)
        self.assertEqual(body["duration_ms"], 0)
        self.assertEqual(body["measurement"]["available"],
                         {"tokens": True, "duration_ms": False})
        self.assertEqual(body["measurement"]["provenance"],
                         {"tokens": "manifest", "duration_ms": None})

    def test_invalid_metric_in_any_response_leaves_no_partial_writes(self):
        for field, value in (("tokens", True), ("tokens", float("inf")),
                             ("duration_ms", -1), ("duration_ms", "1")):
            with self.subTest(field=field, value=value):
                pb = CampaignPB(frameworks=[], extenders=[])
                manifest = {"run": {"slug": "campaign", "kind": "judged"}, "responses": [
                    {"role": "valid", "tokens": 1}, {"role": "invalid", field: value},
                ]}
                with self.assertRaises(SystemExit) as caught:
                    self._load(pb, manifest)
                self.assertIn(field, str(caught.exception))
                self.assertEqual(pb.upserted, [])


class ReferenceSource:
    """report.py's data-source shape: `list_all(coll)`, no filter argument (FixtureSource)."""

    def __init__(self, **collections):
        self.collections = {k: list(v) for k, v in collections.items()}

    def list_all(self, coll):
        return [dict(r) for r in self.collections.get(coll, [])]


if __name__ == "__main__":
    unittest.main()
