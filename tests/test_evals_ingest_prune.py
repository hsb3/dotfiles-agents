"""Hermetic tests for the `extenders` prune step in evals/ingest.py.

No PocketBase, no network, no sqlite: a fake client implementing only the two methods the
prune calls (list_all, delete) stands in for evals/pb.py's PB. The live-slug predicate is
additionally checked against the repo's own primitives-core.yaml / externals.yaml (read
only), because a predicate narrower than what ingest_extenders writes would delete rows the
same run had just created.
"""

import contextlib
import inspect
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
import ingest as I  # noqa: E402


class FakePB:
    """Stands in for evals/pb.py's PB with only what the prune calls.

    `relationships` filters are matched by substring: the prune builds its filter from the
    extender's record id, so an id appearing in the filter string is the edge match.
    """

    def __init__(self, extenders, relationships=()):
        self.rows = {
            "extenders": [dict(r) for r in extenders],
            "relationships": [dict(r) for r in relationships],
        }
        self.deleted = []

    def list_all(self, coll, flt=None):
        rows = self.rows[coll]
        if coll == "relationships" and flt is not None:
            rows = [r for r in rows if r["extender_a"] in flt or r["extender_b"] in flt]
        return [dict(r) for r in rows]

    def delete(self, coll, rec_id):
        self.deleted.append((coll, rec_id))
        self.rows[coll] = [r for r in self.rows[coll] if r["id"] != rec_id]


def row(rec_id, slug, kind="skill", origin="authored"):
    return {"id": rec_id, "slug": slug, "kind": kind, "origin": origin}


def run_prune(pb, slugs, **kw):
    """Call the prune with stdout captured; returns the captured text."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        I.prune_extenders(pb, slugs, **kw)
    return buf.getvalue()


class PruneTest(unittest.TestCase):
    def test_stale_row_is_deleted_and_live_roster_row_is_kept(self):
        pb = FakePB([row("id-live", "handoff"), row("id-stale", "github-project-board")])
        out = run_prune(pb, {"handoff"})
        self.assertEqual(pb.deleted, [("extenders", "id-stale")])
        self.assertEqual([r["slug"] for r in pb.rows["extenders"]], ["handoff"])
        self.assertIn("github-project-board", out)
        self.assertNotIn("handoff", out)

    def test_external_origin_row_in_the_live_set_is_kept(self):
        pb = FakePB([
            row("id-ext", "pptx", kind="plugin", origin="external"),
            row("id-stale", "github-project-board"),
        ])
        run_prune(pb, {"pptx"})
        self.assertEqual(pb.deleted, [("extenders", "id-stale")])
        self.assertEqual([r["slug"] for r in pb.rows["extenders"]], ["pptx"])

    def test_blocking_relationship_edges_are_deleted_before_the_extender(self):
        pb = FakePB(
            [row("id-stale", "github-project-board"), row("id-live", "handoff")],
            [
                {"id": "edge-a", "extender_a": "id-stale", "extender_b": "id-live"},
                {"id": "edge-b", "extender_a": "id-live", "extender_b": "id-stale"},
                {"id": "edge-c", "extender_a": "id-live", "extender_b": "id-live"},
            ],
        )
        run_prune(pb, {"handoff"})
        self.assertEqual(
            pb.deleted,
            [("relationships", "edge-a"), ("relationships", "edge-b"), ("extenders", "id-stale")],
        )
        self.assertEqual([r["id"] for r in pb.rows["relationships"]], ["edge-c"])

    def test_dry_run_deletes_nothing_and_still_reports_the_stale_slug(self):
        pb = FakePB(
            [row("id-live", "handoff"), row("id-stale", "github-project-board")],
            [{"id": "edge-a", "extender_a": "id-stale", "extender_b": "id-live"}],
        )
        out = run_prune(pb, {"handoff"}, dry_run=True)
        self.assertEqual(pb.deleted, [])
        self.assertEqual(len(pb.rows["extenders"]), 2)
        self.assertEqual(len(pb.rows["relationships"]), 1)
        self.assertIn("github-project-board", out)
        self.assertIn("1", out.splitlines()[-1])


class LiveSlugsTest(unittest.TestCase):
    """The predicate must cover everything BOTH writers produce, or a run deletes its own work."""

    def test_covers_every_slug_ingest_extenders_writes(self):
        slugs = I.live_slugs()
        written = [e["id"] for e in I.parse_roster(I.ROSTER)
                   if e.get("type") in I.ROSTER_EXTENDER_TYPES]
        self.assertTrue(written, "roster parsed to zero ingestable entries")
        self.assertEqual(sorted(set(written) - slugs), [])

    def test_covers_every_slug_ingest_externals_writes(self):
        slugs = I.live_slugs()
        written = [e["id"] for e in I.parse_externals(I.EXTERNALS)]
        self.assertTrue(written, "externals.yaml parsed to zero entries")
        self.assertEqual(sorted(set(written) - slugs), [])

    def test_type_filter_cannot_drift_from_ingest_extenders(self):
        for fn in (I.ingest_extenders, I.live_slugs):
            self.assertIn("ROSTER_EXTENDER_TYPES", inspect.getsource(fn))

    def test_excludes_roster_types_neither_writer_ingests(self):
        others = [e["id"] for e in I.parse_roster(I.ROSTER)
                  if e.get("type") not in I.ROSTER_EXTENDER_TYPES]
        externals = {e["id"] for e in I.parse_externals(I.EXTERNALS)}
        self.assertTrue(others, "roster parsed to zero non-ingestable entries")
        self.assertEqual(sorted(set(others) & I.live_slugs() - externals), [])


if __name__ == "__main__":
    unittest.main()
