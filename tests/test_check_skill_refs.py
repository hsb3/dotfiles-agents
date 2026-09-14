"""check_skill_refs.py — the cross-bundle skill-citation gate.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule): a miniature roster, a few skill bodies, and plugin assemblies made
of real symlinks, which is what the live tree ships.

Each red-path test asserts on the specific problem string, not merely on non-emptiness,
so a test cannot pass because some unrelated rule happened to fire.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_skill_refs as R  # noqa: E402


class SkillRefsGate(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-skill-refs-")
        self.saved = R.EXEMPTIONS
        R.EXEMPTIONS = {}
        os.makedirs(os.path.join(self.fix, "primitives-core", "skills"))
        os.makedirs(os.path.join(self.fix, "plugins"))
        self.ids = []

    def tearDown(self):
        R.EXEMPTIONS = self.saved
        shutil.rmtree(self.fix, ignore_errors=True)

    # --- fixture helpers -------------------------------------------------

    def skill(self, sid, body="Body.", reference=None, example=None, readme=None):
        d = os.path.join(self.fix, "primitives-core", "skills", sid)
        os.makedirs(d, exist_ok=True)
        self._write(os.path.join(d, "SKILL.md"), body)
        self._write(os.path.join(d, "README.md"), readme if readme is not None else "# %s\n" % sid)
        if reference is not None:
            os.makedirs(os.path.join(d, "references"), exist_ok=True)
            self._write(os.path.join(d, "references", "notes.md"), reference)
        if example is not None:
            os.makedirs(os.path.join(d, "examples"), exist_ok=True)
            self._write(os.path.join(d, "examples", "worked.md"), example)
        if sid not in self.ids:
            self.ids.append(sid)
        self._roster()

    def plugin(self, pid, *skill_ids):
        d = os.path.join(self.fix, "plugins", pid, "skills")
        os.makedirs(d, exist_ok=True)
        for sid in skill_ids:
            link = os.path.join(d, sid)
            if not os.path.islink(link):
                os.symlink(os.path.join("..", "..", "..", "primitives-core", "skills", sid), link)

    def _roster(self):
        lines = ["version: 1", "", "primitives:"]
        for sid in self.ids:
            lines += [
                "  - id: %s" % sid,
                "    type: skill",
                "    source: primitives-core/skills/%s" % sid,
                "    origin: authored",
                "    disposition: qualified",
                "    targets: [claude-code]",
            ]
        self._write(os.path.join(self.fix, "primitives-core.yaml"), "\n".join(lines) + "\n")

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def problems(self):
        return R.problems(self.fix)

    # --- the red case ----------------------------------------------------

    def test_citation_a_bundle_cannot_resolve_is_red(self):
        self.skill("alpha", "Go and use the `beta` skill for the second half.")
        self.skill("beta", "Beta stands alone.")
        self.plugin("wide", "alpha", "beta")
        self.plugin("narrow", "alpha")
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("primitives-core/skills/alpha/SKILL.md:1", probs[0])
        self.assertIn("`beta`", probs[0])
        self.assertIn("plugins/narrow", probs[0])
        self.assertNotIn("plugins/wide", probs[0])

    def test_backticked_sibling_path_is_a_citation(self):
        # `skills/<id>/...` is how a bundled script's own doc names a sibling's asset, and
        # it is a hard dependency: the file is only there if the bundle ships the sibling.
        # The English-word objection to bare names does not apply once `skills/` prefixes
        # the id.
        self.skill("alpha", "Pass a root holding `skills/beta/references/checklist.md`.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("`beta`", probs[0])
        self.assertIn("plugins/narrow", probs[0])

    def test_path_form_matches_the_bare_directory_too(self):
        self.skill("alpha", "a root that contains `skills/beta/`.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        self.assertEqual(len(self.problems()), 1)

    def test_path_form_does_not_match_a_longer_id(self):
        self.skill("alpha", "See `skills/beta-extended/`.")
        self.skill("beta", "Beta.")
        self.skill("beta-extended", "Beta extended.")
        self.plugin("narrow", "alpha", "beta")
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("`beta-extended`", probs[0])

    def test_references_and_examples_are_scanned(self):
        self.skill("alpha", "Body.", reference="See the `beta` skill.", example="Also `beta`.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        probs = self.problems()
        self.assertEqual(len(probs), 2, probs)
        self.assertTrue(any("references/notes.md:1" in p for p in probs), probs)
        self.assertTrue(any("examples/worked.md:1" in p for p in probs), probs)

    # --- the green case --------------------------------------------------

    def test_every_bundle_shipping_the_citer_ships_the_cited(self):
        self.skill("alpha", "Go and use the `beta` skill for the second half.")
        self.skill("beta", "Beta stands alone.")
        self.plugin("wide", "alpha", "beta")
        self.plugin("also", "alpha", "beta")
        self.assertEqual(self.problems(), [])

    def test_citer_in_no_assembly_has_no_consumer(self):
        # `gamma`'s bundle ships neither skill, so a gate that stopped requiring the
        # bundle to actually SHIP the citing skill would report it — which is what makes
        # this test able to fail.
        self.skill("alpha", "Go and use the `beta` skill.")
        self.skill("beta", "Beta.")
        self.skill("gamma", "Gamma.")
        self.plugin("narrow", "beta")
        self.plugin("other", "gamma")
        self.assertEqual(self.problems(), [])

    def test_self_citation_is_not_a_reference(self):
        # Asserted on the extractor, not only on problems(): a self-citation can never be
        # a violation anyway, so only the citation list — the audit surface --report
        # prints — can tell whether the guard is still there.
        self.skill("alpha", "This is the `alpha` skill, see `skills/alpha/`.")
        self.plugin("narrow", "alpha")
        self.assertEqual(R.citations(self.fix), [])
        self.assertEqual(self.problems(), [])

    def test_readme_is_not_scanned(self):
        self.skill("alpha", "Body.", readme="# alpha\n\nSee the `beta` skill.\n")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        self.assertEqual(self.problems(), [])

    # --- mention, not dependency -----------------------------------------

    def test_bare_prose_name_is_not_a_citation(self):
        # Roster ids like `handoff`, `waves` and `comms` are ordinary English words, so
        # only the backticked form can carry a citation.
        self.skill("handoff", "Handoff rules.")
        self.skill("alpha", "Write the handoff before you stop; a clean handoff is short.")
        self.plugin("narrow", "alpha")
        self.assertEqual(self.problems(), [])

    # --- exemptions ------------------------------------------------------

    def test_exemption_with_its_anchor_present_is_clean(self):
        self.skill("alpha", "Boundary: data charts are not this skill's job.\nUse `beta`.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {
            ("alpha", "beta"): ("scope boundary, not a dependency", "not this skill's job"),
        }
        self.assertEqual(self.problems(), [])

    def test_exemption_is_inactive_when_its_anchor_is_gone(self):
        # The anchor is the sentence that justifies the exemption. Without it the
        # exemption suppresses nothing, which is what keeps a pair-keyed entry from
        # covering an earlier state of the prose where the citation WAS a dependency.
        self.skill("alpha", "Use `beta` for the second half.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {
            ("alpha", "beta"): ("scope boundary, not a dependency", "not this skill's job"),
        }
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("anchor", probs[0])

    def test_exemption_that_suppresses_nothing_is_stale(self):
        self.skill("alpha", "Body with no citation.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {
            ("alpha", "beta"): ("scope boundary, not a dependency", "not this skill's job"),
        }
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("stale", probs[0])

    def test_exemption_naming_a_skill_that_does_not_exist_is_stale(self):
        self.skill("alpha", "Body.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {("alpha", "ghost"): ("reason", "anchor")}
        probs = self.problems()
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("no such skill", probs[0])

    def test_anchor_with_no_substance_is_rejected(self):
        # The gate's whole safety property is the anchor. A one-letter anchor matches any
        # prose, so an exemption carrying one certifies text it never read.
        self.skill("alpha", "Use `beta`.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {("alpha", "beta"): ("reason", "e")}
        probs = self.problems()
        self.assertTrue(any("substance" in p for p in probs), probs)
        self.assertNotEqual(R.main(["--repo", self.fix]), 0)

    def test_anchor_that_is_just_the_cited_id_is_rejected(self):
        # The citation itself contains the cited id, so such an anchor is self-satisfying.
        self.skill("alpha", "Use `beta-with-a-long-name`.")
        self.skill("beta-with-a-long-name", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {
            ("alpha", "beta-with-a-long-name"): ("reason", "beta-with-a-long-name"),
        }
        probs = self.problems()
        self.assertTrue(any("substance" in p for p in probs), probs)

    def test_anchor_at_the_floor_is_accepted(self):
        anchor = "x" * R.ANCHOR_MIN_CHARS
        self.skill("alpha", "Use `beta`. %s" % anchor)
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        R.EXEMPTIONS = {("alpha", "beta"): ("reason", anchor)}
        self.assertEqual(self.problems(), [])

    # --- entry point -----------------------------------------------------

    def test_main_exit_codes(self):
        self.skill("alpha", "Use the `beta` skill.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        self.assertEqual(R.main(["--repo", self.fix]), 1)
        self.plugin("narrow", "beta")
        self.assertEqual(R.main(["--repo", self.fix]), 0)

    def test_report_mode_lists_every_citation(self):
        self.skill("alpha", "Use the `beta` skill; this is `alpha`.")
        self.skill("beta", "Beta.")
        self.plugin("wide", "alpha", "beta")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(R.main(["--repo", self.fix, "--report"]), 0)
        text = out.getvalue()
        rows = [ln for ln in text.splitlines() if ln.startswith("alpha")]
        self.assertEqual(len(rows), 1, text)
        self.assertIn("beta", rows[0])
        self.assertIn("shipped", rows[0])
        self.assertIn("1 citation(s)", text)

    def test_report_mode_flags_an_unresolved_citation(self):
        self.skill("alpha", "Use the `beta` skill.")
        self.skill("beta", "Beta.")
        self.plugin("narrow", "alpha")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(R.main(["--repo", self.fix, "--report"]), 1)
        self.assertIn("MISSING", out.getvalue())


class LiveTree(unittest.TestCase):
    """The shipped tree is green, and every exemption still earns its place."""

    # This test is what enforces the gate in CI (make ci -> make test). A truncated diff
    # would hide the contributor's own violations behind "Diff is N characters long".
    maxDiff = None

    def test_repo_is_clean(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertEqual(R.problems(repo), [])


if __name__ == "__main__":
    unittest.main()
