"""Hermetic tests for the `extenders` prune step in evals/ingest.py.

No PocketBase, no network, no sqlite: fake clients implementing only the methods the code
under test calls stand in for evals/pb.py's PB. The live-slug predicate is derived by
RUNNING both `extenders` writers against a recording fake and reading back what they
upserted — recomputing the predicate's own expression would pass no matter how the writers
drift. The writers read the repo's own primitives-core.yaml / externals.yaml, read-only.
"""

import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
import ingest as I  # noqa: E402


def _as_list(value):
    return list(value) if isinstance(value, (list, tuple)) else ([] if value is None else [value])


class FakePB:
    """Stands in for PB with only what the prune calls: list_all + delete.

    Every filter the prune builds names one extender record id, so a row matches when one of
    its referencing fields holds an id that appears in the filter string.
    """

    def __init__(self, extenders, **dependents):
        self.rows = {"extenders": [dict(r) for r in extenders]}
        for coll in I.PRUNE_DEPENDENTS:
            self.rows[coll] = [dict(r) for r in dependents.get(coll, ())]
        self.deleted = []

    def list_all(self, coll, flt=None):
        rows = self.rows[coll]
        if flt is not None:
            _op, fields = I.PRUNE_DEPENDENTS[coll]
            rows = [r for r in rows
                    if any(v in flt for f in fields for v in _as_list(r.get(f)))]
        return [dict(r) for r in rows]

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

    def slugs(self):
        return {b["slug"] for coll, b in self.upserted if coll == "extenders"}


def row(rec_id, slug, kind="skill", origin="authored"):
    return {"id": rec_id, "slug": slug, "kind": kind, "origin": origin}


def quiet(fn, *args, **kwargs):
    """Call `fn` with stdout captured; returns the captured text."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


class PruneTest(unittest.TestCase):
    def test_stale_row_is_deleted_and_live_roster_row_is_kept(self):
        pb = FakePB([row("id-live", "handoff"), row("id-stale", "github-project-board")])
        out = quiet(I.prune_extenders, pb, {"handoff"})
        self.assertEqual(pb.deleted, [("extenders", "id-stale")])
        self.assertEqual([r["slug"] for r in pb.rows["extenders"]], ["handoff"])
        self.assertIn("github-project-board", out)
        self.assertNotIn("handoff", out)

    def test_external_origin_row_in_the_live_set_is_kept(self):
        pb = FakePB([
            row("id-ext", "pptx", kind="plugin", origin="external"),
            row("id-stale", "github-project-board"),
        ])
        quiet(I.prune_extenders, pb, {"pptx"})
        self.assertEqual(pb.deleted, [("extenders", "id-stale")])
        self.assertEqual([r["slug"] for r in pb.rows["extenders"]], ["pptx"])

    def test_blocking_relationship_edges_are_deleted_before_the_extender(self):
        pb = FakePB(
            [row("id-stale", "github-project-board"), row("id-live", "handoff")],
            relationships=[
                {"id": "edge-a", "extender_a": "id-stale", "extender_b": "id-live"},
                {"id": "edge-b", "extender_a": "id-live", "extender_b": "id-stale"},
                {"id": "edge-c", "extender_a": "id-live", "extender_b": "id-live"},
            ],
        )
        quiet(I.prune_extenders, pb, {"handoff"})
        self.assertEqual(
            pb.deleted,
            [("relationships", "edge-a"), ("relationships", "edge-b"), ("extenders", "id-stale")],
        )
        self.assertEqual([r["id"] for r in pb.rows["relationships"]], ["edge-c"])

    def test_dry_run_deletes_nothing_and_still_reports_the_stale_slug(self):
        pb = FakePB(
            [row("id-live", "handoff"), row("id-stale", "github-project-board")],
            relationships=[{"id": "edge-a", "extender_a": "id-stale", "extender_b": "id-live"}],
        )
        out = quiet(I.prune_extenders, pb, {"handoff"}, dry_run=True)
        self.assertEqual(pb.deleted, [])
        self.assertEqual(len(pb.rows["extenders"]), 2)
        self.assertEqual(len(pb.rows["relationships"]), 1)
        self.assertIn("github-project-board", out)
        self.assertIn("extenders to prune: 1", out)


class BlastRadiusTest(unittest.TestCase):
    """The accounting is the operator's only warning that unrebuildable rows are going."""

    def _pb(self):
        return FakePB(
            [row("id-stale", "github-project-board"), row("id-2", "foreman"),
             row("id-live", "handoff")],
            assessments=[
                {"id": "a1", "extender": "id-stale", "assessor": "coverage-v1"},
                {"id": "a2", "extender": "id-stale", "assessor": "coverage-v1"},
                {"id": "a3", "extender": "id-stale", "assessor": "mechanical-v1"},
                {"id": "a4", "extender": "id-2", "assessor": "judged-v1"},
                {"id": "a5", "extender": "id-live", "assessor": "coverage-v1"},
            ],
            relationships=[
                {"id": "e1", "extender_a": "id-stale", "extender_b": "id-2"},
                {"id": "e2", "extender_a": "id-live", "extender_b": "id-live"},
            ],
            eval_responses=[
                {"id": "r1", "extenders": ["id-stale", "id-2"]},
                {"id": "r2", "extenders": ["id-live"]},
            ],
            distributions=[{"id": "d1", "members": ["id-stale", "id-live"]}],
        )

    def _lines(self, dry_run):
        return quiet(I.prune_extenders, self._pb(), {"handoff"}, dry_run=dry_run).splitlines()

    def test_totals_are_reported_on_both_the_dry_and_the_real_run(self):
        for dry_run, verb in ((True, "to prune"), (False, "pruned")):
            with self.subTest(dry_run=dry_run):
                lines = self._lines(dry_run)
                self.assertIn(f"extenders {verb}: 2", lines)
                self.assertIn(
                    f"assessments {verb} by cascade: 4 "
                    "(coverage-v1 2, judged-v1 1, mechanical-v1 1)",
                    lines,
                )
                self.assertIn(f"relationships {verb}: 1", lines)
                self.assertIn("eval_responses losing a reference: 1 rows / 2 references", lines)
                self.assertIn("distributions losing a member: 1 rows / 1 references", lines)

    def test_a_row_referenced_by_two_pruned_extenders_counts_once_as_a_row(self):
        lines = self._lines(True)
        self.assertIn("eval_responses losing a reference: 1 rows / 2 references", lines)
        self.assertIn("relationships to prune: 1", lines)

    def test_each_stale_row_names_its_own_dependent_counts(self):
        lines = self._lines(True)
        self.assertIn(
            "extender stale: skill/github-project-board "
            "(assessments 3, relationships 1, eval_responses 1, distributions 1)",
            lines,
        )


class LiveSlugsTest(unittest.TestCase):
    """A predicate narrower than what the writers produce deletes rows the same run created;
    a wider one leaves stale rows behind. Both directions are pinned by running the writers."""

    def test_matches_exactly_what_the_two_writers_upsert(self):
        pb = RecordingPB()
        quiet(I.ingest_extenders, pb)
        quiet(I.ingest_externals, pb, {})
        written = pb.slugs()
        self.assertTrue(written, "the writers upserted no extenders at all")
        self.assertEqual(sorted(written), sorted(I.live_slugs()))


class MainWiringTest(unittest.TestCase):
    """AC#1: the prune runs in the same run that upserts the rest, after both writers."""

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
            "prune_extenders": record("prune_extenders"),
        }
        with contextlib.ExitStack() as stack:
            for name, fn in stubs.items():
                stack.enter_context(mock.patch.object(I, name, fn))
            quiet(I.main)
        return calls

    def test_main_prunes(self):
        self.assertIn("prune_extenders", self._run_main())

    def test_main_prunes_after_both_extenders_writers(self):
        calls = self._run_main()
        pruned = calls.index("prune_extenders")
        self.assertGreater(pruned, calls.index("ingest_extenders"))
        self.assertGreater(pruned, calls.index("ingest_externals"))


if __name__ == "__main__":
    unittest.main()
