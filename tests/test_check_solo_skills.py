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

# The hook-resolution core of primitives-core/skills/activation/scripts/activation.py,
# copied here with its two sibling-skill mentions (`delegation`, `handoff`) stripped so
# the only coupling left is the hook directory. It carries no literal `hooks/<name>`
# either: the path is assembled with os.path.join, exactly as the real file does.
ACTIVATION_HOOK_RESOLUTION = '''\
import os

HOOK_NAMES = (
    "worker-context",
    "config-custody",
    "worktree-isolation",
    "session-handoff-surfacer",
    "handoff-freshness-guard",
    "worker-git-scope-guard",
)


def _hook_roots():
    seen = []
    for base in (os.path.dirname(os.path.abspath(__file__)),
                 os.path.dirname(os.path.realpath(__file__))):
        root = os.path.normpath(os.path.join(base, "..", "..", "..", "hooks"))
        if root not in seen:
            seen.append(root)
    return seen


def load_hooks():
    for root in _hook_roots():
        paths = {n: os.path.join(root, n, "hook.py") for n in HOOK_NAMES}
        if all(os.path.isfile(p) for p in paths.values()):
            return paths
    return None
'''


class SoloSkillsGate(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-solo-skills-")
        self.saved = {
            k: getattr(S, k)
            for k in (
                "REPO", "SKILLS_DIR", "AGENTS_DIR", "HOOKS_DIR", "SOLO_SKILLS_DIR",
                "PLUGINS_DIR", "AGENT_EXEMPTIONS", "SYSTEM_EXEMPTIONS",
            )
        }
        S.REPO = self.fix
        S.SKILLS_DIR = os.path.join(self.fix, "primitives-core", "skills")
        S.AGENTS_DIR = os.path.join(self.fix, "primitives-core", "agents")
        S.HOOKS_DIR = os.path.join(self.fix, "primitives-core", "hooks")
        S.SOLO_SKILLS_DIR = os.path.join(self.fix, "plugins", "solo-skills", "skills")
        S.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        S.AGENT_EXEMPTIONS = {}
        S.SYSTEM_EXEMPTIONS = {}
        os.makedirs(S.SKILLS_DIR)
        os.makedirs(S.AGENTS_DIR)
        os.makedirs(S.HOOKS_DIR)
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

    def skill(self, sid, body="Body.", ref=None, script=None, example=None):
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
        if example is not None:
            os.makedirs(os.path.join(d, "examples", "demo"), exist_ok=True)
            with open(os.path.join(d, "examples", "demo", "sample.js"), "w") as fh:
                fh.write(example + "\n")

    def hook(self, name):
        d = os.path.join(S.HOOKS_DIR, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "hook.py"), "w") as fh:
            fh.write("# hook\n")

    def member(self, sid):
        os.symlink(
            os.path.join(S.SKILLS_DIR, sid), os.path.join(S.SOLO_SKILLS_DIR, sid)
        )

    def topical(self, sid, plugin):
        """Link a skill into some OTHER plugin's assembly — its topical home."""
        d = os.path.join(S.PLUGINS_DIR, plugin, "skills")
        os.makedirs(d, exist_ok=True)
        os.symlink(os.path.join(S.SKILLS_DIR, sid), os.path.join(d, sid))

    def assertProblem(self, needle):
        probs = S.problems()
        self.assertTrue(
            any(needle in p for p in probs),
            f"expected a problem containing {needle!r}, got {probs}",
        )

    def assertNoProblem(self, needle):
        probs = S.problems()
        self.assertFalse(
            any(needle in p for p in probs),
            f"expected no problem containing {needle!r}, got {probs}",
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

    def test_sibling_path_in_example_markdown_is_red(self):
        # examples/*.md is a playbook/write-up (comms' playbook.md, activation's
        # atelier.local.md) — narrative prose like SKILL.md and references/, not
        # bundled code. A sibling path there is the same signal rule 1 already catches
        # elsewhere, just currently blind to this directory.
        self.skill("beta", "Beta.")
        d = os.path.join(S.SKILLS_DIR, "beta", "examples", "demo")
        os.makedirs(d)
        with open(os.path.join(d, "playbook.md"), "w") as fh:
            fh.write("Shared machinery: `skills/alpha/references/x.md`.\n")
        self.member("beta")
        self.assertProblem("references sibling skill `alpha` by path")

    # --- rule 2: sibling id in bundled code ------------------------------

    def test_sibling_id_in_script_is_red_even_without_a_literal_path(self):
        # The real case this exists for: scaffold.py builds its dependency path with
        # os.path.join, so the literal substring `skills/alpha` never appears.
        self.skill("beta", "Beta.", script='P = os.path.join("skills", "alpha", "x.md")')
        self.member("beta")
        self.assertProblem("bundled script names sibling skill `alpha`")

    def test_sibling_id_in_bundled_example_code_is_red(self):
        # examples/ ships runnable code the same way scripts/ does — a cross-skill
        # require in a bundled sample is a dependency a consumer hits on first run.
        self.skill(
            "beta", "Beta.",
            example='const { T } = require("~/.claude/skills/alpha/assets/t.js");',
        )
        self.member("beta")
        self.assertProblem("bundled script names sibling skill `alpha`")

    def test_non_code_example_asset_is_not_scanned(self):
        # Only source extensions are read: sample DATA carrying a sibling id is not
        # shipped code and cannot import anything.
        self.skill("beta", "Beta.")
        d = os.path.join(S.SKILLS_DIR, "beta", "examples", "demo")
        os.makedirs(d)
        with open(os.path.join(d, "sample.slides.json"), "w") as fh:
            fh.write('{"note": "alpha"}\n')
        self.member("beta")
        self.assertEqual(S.problems(), [])

    # --- rule 3: named-agent dispatch ------------------------------------

    def test_agent_dispatch_is_red(self):
        self.skill("beta", "Dispatch a `manager` for the coupled chain.")
        self.member("beta")
        self.assertProblem("dispatches agent `manager`")

    def test_namespaced_agent_dispatch_is_red(self):
        self.skill("beta", "Dispatch `atelier:manager` for the coupled chain.")
        self.member("beta")
        self.assertProblem("dispatches agent `manager`")

    # --- rule 4: hook coupling in bundled code ---------------------------

    def test_hook_id_in_code_is_red_with_no_sibling_mention_anywhere(self):
        # Prose and code name no sibling skill at all; the only coupling is the hook.
        self.hook("worker-context")
        self.skill(
            "beta", "Beta stands alone.",
            script='P = os.path.join(ROOT, "worker-context", "hook.py")',
        )
        self.member("beta")
        self.assertProblem("bundled script resolves hook `worker-context`")
        self.assertNoProblem("names sibling skill")

    def test_literal_hook_path_in_code_is_red(self):
        self.hook("config-custody")
        self.skill("beta", "Beta.", script='P = "hooks/config-custody/hook.py"')
        self.member("beta")
        self.assertProblem("bundled script resolves hook `config-custody`")

    def test_hook_id_in_prose_alone_is_not_a_dependency(self):
        # Naming a hook in prose is documentation; only shipped code couples.
        self.hook("worker-context")
        self.skill("beta", "The `worker-context` hook explains the covenant.")
        self.member("beta")
        self.assertEqual(S.problems(), [])

    def test_activation_stays_excluded_on_the_hook_rule_alone(self):
        # AC: with `delegation` and `handoff` stripped from activation.py's code, the
        # gate must still exclude it. Proven on a copy, never by editing the real file.
        for name in (
            "worker-context", "config-custody", "worktree-isolation",
            "session-handoff-surfacer", "handoff-freshness-guard",
            "worker-git-scope-guard",
        ):
            self.hook(name)
        self.skill("delegation", "Delegation stands alone.")
        self.member("delegation")
        self.skill("handoff", "Handoff stands alone.")
        self.member("handoff")
        self.skill("activation", "Audit what the enforcement hooks resolve.",
                   script=ACTIVATION_HOOK_RESOLUTION)
        self.member("activation")
        self.assertNotIn(
            "delegation", ACTIVATION_HOOK_RESOLUTION,
            "the fixture must not carry the sibling mention it is stripping",
        )
        self.assertProblem("bundled script resolves hook `worker-context`")
        # Rule 2 alone would now find nothing — that is the hole this rule closes.
        self.assertNoProblem("names sibling skill")

    # --- both directions of membership drift -----------------------------

    def test_eligible_skill_absent_from_solo_skills_is_red(self):
        self.skill("beta", "Beta stands alone.")  # eligible, deliberately not a member
        # No other plugin's assembly ships it, so solo-skills is its only possible home.
        self.assertEqual(S._topical_homes(), set())
        self.assertProblem("standalone-capable but absent from solo-skills")

    def test_eligible_skill_with_a_topical_home_may_be_absent(self):
        # decision-020: the topical plugin owns a skill; solo-skills is the home for
        # skills with NO topical plugin. `beta` ships from `gamma-plugin`, so its
        # absence from solo-skills is the rule, not drift.
        self.skill("beta", "Beta stands alone.")
        self.topical("beta", "gamma-plugin")
        self.assertNoProblem("standalone-capable but absent from solo-skills")
        self.assertEqual(S.problems(), [])

    def test_eligible_skill_with_no_topical_home_is_still_red(self):
        # The relaxation is narrow: another plugin shipping a DIFFERENT skill grants
        # `beta` nothing.
        self.skill("beta", "Beta stands alone.")
        self.skill("delta", "Delta stands alone.")
        self.member("delta")
        self.topical("delta", "gamma-plugin")
        self.assertProblem("standalone-capable but absent from solo-skills")

    def test_dual_homed_member_stays_legal(self):
        # PERMISSIVE only: a skill with a topical home that ALSO stays in solo-skills is
        # still clean — ~20 skills are dual-homed and this ruling is executed per-skill.
        self.skill("beta", "Beta stands alone.")
        self.member("beta")
        self.topical("beta", "gamma-plugin")
        self.assertEqual(S.problems(), [])

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
