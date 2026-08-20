"""Tests for scripts/check_vendored_drift.py — the vendored-drift gate.

Offline by design: the gate needs network, `make ci` does not have it, so every test here
exercises the pure parts (externals indexing, hashing/pruning, status classification) with
the network boundary stubbed. The live check is a CI step and `make vendored-drift`.

Stdlib-only; every fixture is a tempdir, never under primitives-core/.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_vendored_drift as D  # noqa: E402
from check_roster import parse_roster  # noqa: E402


def _tree(root, files):
    for rel, content in files.items():
        fp = os.path.join(root, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(content)


class Hashing(unittest.TestCase):
    def test_identical_trees_hash_identically(self):
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        for d in (a, b):
            _tree(d, {"SKILL.md": "x\n", "rules/one.md": "y\n"})
        self.assertEqual(D._walk_hashes(a), D._walk_hashes(b))

    def test_content_difference_is_visible(self):
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        _tree(a, {"SKILL.md": "x\n"})
        _tree(b, {"SKILL.md": "x modified\n"})
        self.assertNotEqual(D._walk_hashes(a), D._walk_hashes(b))

    def test_untracked_noise_pruned_from_comparison(self):
        """__pycache__/*.pyc/.DS_Store are produced by checkout but never committed —
        left unpruned they would read as drift on every run."""
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        _tree(a, {"SKILL.md": "x\n"})
        _tree(b, {"SKILL.md": "x\n", "__pycache__/m.pyc": "junk", ".DS_Store": "junk",
                  "sub/m.pyc": "junk"})
        self.assertEqual(D._walk_hashes(a), D._walk_hashes(b))

    def test_missing_dir_hashes_empty_not_raises(self):
        self.assertEqual(D._walk_hashes(os.path.join(tempfile.mkdtemp(), "nope")), {})


class ExternalsIndexing(unittest.TestCase):
    def test_real_externals_indexed_by_upstream_and_ref(self):
        idx = D._externals_paths()
        self.assertTrue(idx, "externals.yaml yielded no (upstream, ref) pairs")
        for (up, ref) in idx:
            self.assertTrue(up.startswith("http"), up)
            self.assertRegex(ref, r"^[0-9a-f]{40}$")

    def test_every_vendored_entry_resolves_to_an_externals_subtree(self):
        """The gate cannot verify an entry whose subtree it cannot locate. Indexed by
        (upstream, ref) because the roster id and the externals id differ in general —
        `pptx` is vendored under the `pptx-themes` entry."""
        idx = D._externals_paths()
        vendored = [e for e in parse_roster(os.path.join(D.REPO, "primitives-core.yaml"))
                    if (e.get("origin") or "").strip() == "vendored"]
        self.assertTrue(vendored)
        for e in vendored:
            self.assertIn((e.get("upstream"), e.get("ref")), idx,
                          f"{e['id']}: no externals.yaml entry pins its upstream+ref")


class StatusClassification(unittest.TestCase):
    """The network boundary is _fetch_at_ref/_upstream_head; stub both and drive the rest."""

    def setUp(self):
        self._fetch, self._head = D._fetch_at_ref, D._upstream_head
        self.tmp = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp, "primitives-core", "skills", "thing")
        os.makedirs(os.path.join(self.src, "base"))
        _tree(os.path.join(self.src, "base"), {"SKILL.md": "vendored\n"})
        self._repo = D.REPO
        D.REPO = self.tmp
        self.entry = {"id": "thing", "source": "primitives-core/skills/thing",
                      "upstream": "https://example.invalid/x", "ref": "a" * 40}
        self.ext = {("https://example.invalid/x", "a" * 40): ""}

    def tearDown(self):
        D._fetch_at_ref, D._upstream_head, D.REPO = self._fetch, self._head, self._repo

    def _run(self, upstream_files, fetch="ok", head=None):
        def fake_fetch(upstream, ref, dest):
            if fetch == "ok":
                os.makedirs(dest, exist_ok=True)
                _tree(dest, upstream_files)
            return fetch
        D._fetch_at_ref = fake_fetch
        D._upstream_head = lambda upstream, dest: head or self.entry["ref"]
        return D.drift_status(self.entry, self.ext, tempfile.mkdtemp())

    def test_match_at_head_is_up_to_date(self):
        self.assertEqual(self._run({"SKILL.md": "vendored\n"})[0], "up_to_date")

    def test_match_but_upstream_moved_is_behind_not_a_failure(self):
        status, _ = self._run({"SKILL.md": "vendored\n"}, head="b" * 40)
        self.assertEqual(status, "behind")

    def test_hand_edit_in_base_is_diverged(self):
        status, detail = self._run({"SKILL.md": "vendored but upstream differs\n"})
        self.assertEqual(status, "diverged")
        self.assertIn("SKILL.md", detail)

    def test_file_only_in_ours_is_diverged(self):
        """Verbatim is bidirectional — an ADDED file is drift too."""
        _tree(os.path.join(self.src, "base"), {"extra.md": "ours\n"})
        self.assertEqual(self._run({"SKILL.md": "vendored\n"})[0], "diverged")

    def test_file_only_upstream_is_diverged(self):
        status, detail = self._run({"SKILL.md": "vendored\n", "theirs.md": "up\n"})
        self.assertEqual(status, "diverged")
        self.assertIn("only upstream", detail)

    def test_unreachable_upstream_skips_rather_than_failing(self):
        """A network blip is not evidence of drift; hard-failing on one blocks every PR."""
        self.assertEqual(self._run({}, fetch="no_net")[0], "skipped")

    def test_reachable_upstream_missing_ref_is_not_found(self):
        """Distinct from a blip: the host answered and the ref is gone."""
        self.assertEqual(self._run({}, fetch="no_ref")[0], "not_found")

    def test_missing_base_dir_is_diverged(self):
        import shutil
        shutil.rmtree(os.path.join(self.src, "base"))
        self.assertEqual(self._run({"SKILL.md": "x\n"})[0], "diverged")

    def test_unpinned_subtree_is_not_found(self):
        self.assertEqual(D.drift_status(self.entry, {}, tempfile.mkdtemp())[0], "not_found")


if __name__ == "__main__":
    unittest.main()
