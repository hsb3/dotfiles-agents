"""check_solo_skills.py — the solo-skills membership gate.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's path constants are pointed at them for each test.

Each red-path test asserts on the specific problem string, not merely on non-emptiness,
so a test cannot pass because some unrelated rule happened to fire.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_solo_skills as S  # noqa: E402


class SoloSkillsGate(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-solo-skills-")
        self.saved = {
            k: getattr(S, k)
            for k in (
                "REPO", "SKILLS_DIR", "AGENTS_DIR", "SOLO_SKILLS_DIR",
                "AGENT_EXEMPTIONS", "SYSTEM_EXEMPTIONS",
            )
        }
        S.REPO = self.fix
        S.SKILLS_DIR = os.path.join(self.fix, "primitives-core", "skills")
        S.AGENTS_DIR = os.path.join(self.fix, "primitives-core", "agents")
        S.SOLO_SKILLS_DIR = os.path.join(self.fix, "plugins", "solo-skills", "skills")
        S.AGENT_EXEMPTIONS = {}
        S.SYSTEM_EXEMPTIONS = {}
        os.makedirs(S.SKILLS_DIR)
        os.makedirs(S.AGENTS_DIR)
        os.makedirs(S.SOLO_SKILLS_DIR)
        with open(os.path.join(S.AGENTS_DIR, "manager.md"), "w") as fh:
            fh.write("---\nname: manager\n---\n")
        self.skill("alpha", "Alpha does a thing on its own.")
        self.member("alpha")

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(S, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    # --- fixture helpers -------------------------------------------------

    def skill(self, sid, body="Body.", ref=None, script=None):
        d = os.path.join(S.SKILLS_DIR, sid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "w") as fh:
            fh.write(f"---\nname: {sid}\ndescription: x\n---\n\n{body}\n")
        if ref is not None:
            os.makedirs(os.path.join(d, "references"), exist_ok=True)
            with open(os.path.join(d, "references", "guide.md"), "w") as fh:
                fh.write(ref + "\n")
        if script is not None:
            os.makedirs(os.path.join(d, "scripts"), exist_ok=True)
            with open(os.path.join(d, "scripts", "run.py"), "w") as fh:
                fh.write(script + "\n")

    def member(self, sid):
        os.symlink(
            os.path.join(S.SKILLS_DIR, sid), os.path.join(S.SOLO_SKILLS_DIR, sid)
        )

    def assertProblem(self, needle):
        probs = S.problems()
        self.assertTrue(
            any(needle in p for p in probs),
            f"expected a problem containing {needle!r}, got {probs}",
        )

    # --- green path ------------------------------------------------------

    def test_self_sufficient_member_is_clean(self):
        self.assertEqual(S.problems(), [])

    def test_prose_mention_without_a_path_is_not_a_dependency(self):
        # Naming another skill in prose is a cross-reference, not a requirement; only
        # path- and wikilink-shaped references count.
        self.skill("beta", "See the alpha skill for the standard it applies.")
        self.member("beta")
        self.assertEqual(S.problems(), [])

    def test_own_id_in_own_script_is_not_a_sibling_reference(self):
        self.skill("beta", "Beta.", script="P = 'skills/beta/scripts/run.py'")
        self.member("beta")
        self.assertEqual(S.problems(), [])

    # --- rule 1: sibling reference in prose ------------------------------

    def test_sibling_path_in_skill_md_is_red(self):
        self.skill("beta", "Run ${CLAUDE_PLUGIN_ROOT}/skills/alpha/scripts/go.py first.")
        self.member("beta")
        self.assertProblem("references sibling skill `alpha` by path")

    def test_sibling_path_in_references_is_red(self):
        self.skill("beta", "Beta.", ref="Format is owned by `skills/alpha/references/x.md`.")
        self.member("beta")
        self.assertProblem("references sibling skill `alpha` by path")

    def test_sibling_wikilink_is_red(self):
        self.skill("beta", "Depends on [[alpha]] being present.")
        self.member("beta")
        self.assertProblem("references sibling skill `alpha` by wikilink")

    # --- rule 2: sibling id in bundled code ------------------------------

    def test_sibling_id_in_script_is_red_even_without_a_literal_path(self):
        # The real case this exists for: scaffold.py builds its dependency path with
        # os.path.join, so the literal substring `skills/alpha` never appears.
        self.skill("beta", "Beta.", script='P = os.path.join("skills", "alpha", "x.md")')
        self.member("beta")
        self.assertProblem("bundled script names sibling skill `alpha`")

    # --- rule 3: named-agent dispatch ------------------------------------

    def test_agent_dispatch_is_red(self):
        self.skill("beta", "Dispatch a `manager` for the coupled chain.")
        self.member("beta")
        self.assertProblem("dispatches agent `manager`")

    def test_namespaced_agent_dispatch_is_red(self):
        self.skill("beta", "Dispatch `atelier:manager` for the coupled chain.")
        self.member("beta")
        self.assertProblem("dispatches agent `manager`")

    # --- both directions of membership drift -----------------------------

    def test_eligible_skill_absent_from_solo_skills_is_red(self):
        self.skill("beta", "Beta stands alone.")  # eligible, deliberately not a member
        self.assertProblem("standalone-capable but absent from solo-skills")

    def test_member_with_no_such_skill_is_red(self):
        os.symlink(
            os.path.join(S.SKILLS_DIR, "ghost"),
            os.path.join(S.SOLO_SKILLS_DIR, "ghost"),
        )
        self.assertProblem("no such skill in primitives-core")

    def test_missing_assembly_dir_is_red(self):
        shutil.rmtree(os.path.join(self.fix, "plugins", "solo-skills"))
        self.assertProblem("the solo-skills assembly has no skills directory")

    # --- exemptions ------------------------------------------------------

    def test_exemption_suppresses_a_documented_false_positive(self):
        self.skill("beta", "Built-ins: `build`, `plan`, `manager` (subagents).")
        self.member("beta")
        self.assertProblem("dispatches agent `manager`")  # red without the exemption
        S.AGENT_EXEMPTIONS = {("beta", "manager"): "documents another harness's agent"}
        self.assertEqual(S.problems(), [])

    def test_stale_exemption_is_red(self):
        # beta never mentions the agent, so the exemption suppresses nothing.
        self.skill("beta", "Beta stands alone.")
        self.member("beta")
        S.AGENT_EXEMPTIONS = {("beta", "manager"): "reason that no longer applies"}
        self.assertProblem("stale")

    def test_exemption_for_unknown_skill_is_red(self):
        S.AGENT_EXEMPTIONS = {("ghost", "manager"): "reason"}
        self.assertProblem("no such skill")

    def test_exemption_for_unknown_agent_is_red(self):
        S.AGENT_EXEMPTIONS = {("alpha", "ghost-agent"): "reason"}
        self.assertProblem("no such agent")

    def test_system_exempted_skill_may_stay_out_of_solo_skills(self):
        self.skill("beta", "Beta stands alone but prescribes a system.")
        self.assertProblem("standalone-capable but absent")  # red without the exemption
        S.SYSTEM_EXEMPTIONS = {"beta": "prescribes an opt-in in-repo system"}
        self.assertEqual(S.problems(), [])

    def test_system_exempted_skill_present_in_solo_skills_is_red(self):
        self.skill("beta", "Beta stands alone but prescribes a system.")
        self.member("beta")
        S.SYSTEM_EXEMPTIONS = {"beta": "prescribes an opt-in in-repo system"}
        self.assertProblem("present but SYSTEM_EXEMPTIONS excludes it")

    def test_system_exemption_for_unknown_skill_is_red(self):
        S.SYSTEM_EXEMPTIONS = {"ghost": "reason"}
        self.assertProblem("SYSTEM_EXEMPTIONS['ghost']: no such skill")


if __name__ == "__main__":
    unittest.main()
