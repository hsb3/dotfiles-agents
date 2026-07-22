"""gen_opencode unit tests (ADR 0008 W4).

Covers the agent frontmatter transform (the real mapping rules, not just shape), the
opencode skill-name/description validators, the exclusion-vs-roster conflict guard, and
build determinism against the real roster (two temp builds must be byte-identical).
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import gen_opencode as G  # noqa: E402
from check_roster import parse_roster  # noqa: E402

ALIASES = {"haiku": "anthropic/claude-haiku-4-5", "opus": "anthropic/claude-opus-4-8"}

CC_AGENT = """---
name: scout
description: Read-only recon.
model: haiku
effort: low
maxTurns: 15
tools: Read, Grep, Glob
color: cyan
---

Body text survives verbatim.
"""


class TestTransformAgent(unittest.TestCase):
    def test_mapping_rules(self):
        out = G.transform_agent(CC_AGENT, ALIASES)
        fm, body = G.split_frontmatter(out)
        self.assertNotIn("name", fm)  # filename carries identity
        self.assertEqual(fm["mode"], "subagent")
        self.assertEqual(fm["model"], "anthropic/claude-haiku-4-5")
        self.assertEqual(fm["steps"], "15")
        self.assertNotIn("effort", fm)  # CC-only knob dropped
        self.assertIn("Body text survives verbatim.", body)

    def test_permission_inversion(self):
        read_only = G.transform_agent(CC_AGENT, ALIASES)
        self.assertIn("write: deny", read_only)
        self.assertIn("bash: deny", read_only)
        self.assertIn("read: allow", read_only)
        builder = G.transform_agent(
            CC_AGENT.replace("tools: Read, Grep, Glob", "tools: Read, Edit, Write, Bash"),
            ALIASES,
        )
        self.assertIn("write: allow", builder)
        self.assertIn("bash: allow", builder)

    def test_unmapped_bare_model_is_dropped(self):
        out = G.transform_agent(CC_AGENT.replace("model: haiku", "model: mystery"), {})
        fm, _ = G.split_frontmatter(out)
        self.assertNotIn("model", fm)  # bare alias with no pin: drop, never ship unprefixed


class TestSkillValidators(unittest.TestCase):
    def _skill(self, name, desc):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = os.path.join(d, name)
        os.makedirs(src)
        with open(os.path.join(src, "SKILL.md"), "w") as fh:
            fh.write(f"---\nname: {name}\ndescription: {desc}\n---\nbody\n")
        return src

    def test_bad_name_flagged(self):
        src = self._skill("Bad_Name", "fine")
        self.assertTrue(any("regex" in p for p in G.skill_problems("Bad_Name", src)))

    def test_long_description_flagged(self):
        src = self._skill("fine-name", "x" * 1100)
        self.assertTrue(any("1024" in p for p in G.skill_problems("fine-name", src)))

    def test_clean_skill_passes(self):
        src = self._skill("fine-name", "a normal description")
        self.assertEqual(G.skill_problems("fine-name", src), [])


class TestExclusionConflict(unittest.TestCase):
    def test_excluded_id_with_opencode_target_is_a_problem(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        translation = {
            "matrix": [{"type": "skill", "target": "opencode", "treatment": "native"}],
            "model_aliases": [],
            "exclusions": [{"id": "update-config", "reason": "cc-specific"}],
        }
        entries = [{
            "id": "update-config", "type": "skill",
            "source": "primitives-core/skills/update-config",
            "targets": "[claude-code, opencode]",
        }]
        problems = G.build(d, entries, translation)
        self.assertTrue(any("resolve the disagreement" in p for p in problems))


class TestDeterminism(unittest.TestCase):
    def test_two_builds_identical(self):
        entries = parse_roster(os.path.join(REPO, "primitives-core.yaml"))
        translation = G.parse_translation(os.path.join(REPO, "translation.yaml"))
        a = tempfile.mkdtemp()
        b = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        self.assertEqual(G.build(a, entries, translation), [])
        self.assertEqual(G.build(b, entries, translation), [])
        self.assertTrue(G._identical(a, b))


if __name__ == "__main__":
    unittest.main()
