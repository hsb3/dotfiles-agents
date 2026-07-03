"""Tests for scripts/validate_primitives.py -- it must CATCH broken primitives, not just pass.

Drives the validator's functions over good + deliberately broken fixtures. The validator's
path-joining uses os.path.join(REPO, src), which returns the second arg unchanged when it's
absolute -- so temp fixtures with absolute paths exercise the real code paths.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import validate_primitives as V  # noqa: E402


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class Frontmatter(unittest.TestCase):
    def test_extracts_keys(self):
        self.assertEqual(
            V.frontmatter_keys("---\nname: x\ndescription: y\n---\nbody"),
            {"name", "description"},
        )

    def test_no_frontmatter_is_empty(self):
        self.assertEqual(V.frontmatter_keys("# just a heading\n"), set())


class SecretValues(unittest.TestCase):
    def test_literal_secret_flagged(self):
        problems = []
        V.check_secret_values(
            {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_REALLOOKINGTOKEN1234"}, "x", problems
        )
        self.assertEqual(len(problems), 1)

    def test_placeholder_ok(self):
        problems = []
        V.check_secret_values(
            {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"},
            "x",
            problems,
        )
        self.assertEqual(problems, [])

    def test_non_secret_key_ignored(self):
        problems = []
        V.check_secret_values({"GITHUB_TOOLSETS": "all"}, "x", problems)
        self.assertEqual(problems, [])


class McpSpec(unittest.TestCase):
    def _spec(self, obj):
        p = os.path.join(tempfile.mkdtemp(), "spec.json")
        _write(p, json.dumps(obj))
        return p

    def test_valid_stdio(self):
        problems = []
        V.validate_mcp_spec(
            self._spec({"name": "x", "transport": "stdio", "command": "x"}),
            "x",
            problems,
        )
        self.assertEqual(problems, [])

    def test_missing_transport(self):
        problems = []
        V.validate_mcp_spec(self._spec({"name": "x"}), "x", problems)
        self.assertTrue(any("transport" in p for p in problems))

    def test_http_missing_url(self):
        problems = []
        V.validate_mcp_spec(
            self._spec({"name": "x", "transport": "http"}), "x", problems
        )
        self.assertTrue(any("url" in p for p in problems))

    def test_literal_secret_in_env(self):
        problems = []
        spec = {
            "name": "x",
            "transport": "stdio",
            "command": "x",
            "env": {"API_TOKEN": "literal-abc123"},
        }
        V.validate_mcp_spec(self._spec(spec), "x", problems)
        self.assertTrue(any("placeholder" in p for p in problems))


class Entry(unittest.TestCase):
    def _skill(self, skill_md_text):
        d = tempfile.mkdtemp()
        _write(os.path.join(d, "SKILL.md"), skill_md_text)
        return {
            "id": "t",
            "type": "skill",
            "source": d,
            "shelf": "core",
            "origin": "authored",
            "targets": ["claude-code"],
            "plugins": [],
            "summary": "ok",
        }

    def test_skill_missing_description_flagged(self):
        problems = []
        V.validate_entry(self._skill("---\nname: t\n---\nbody"), problems)
        self.assertTrue(any("description" in p for p in problems))

    def test_good_skill_clean(self):
        problems = []
        V.validate_entry(
            self._skill("---\nname: t\ndescription: d\n---\nbody"), problems
        )
        self.assertEqual(problems, [])

    def test_xml_tag_in_description_flagged(self):
        problems = []
        V.validate_entry(
            self._skill(
                '---\nname: t\ndescription: spin up a "<project>-x" desk\n---\nbody'
            ),
            problems,
        )
        self.assertTrue(
            any("XML tag" in p and "<project>" in p for p in problems),
            f"expected an XML-tag blocker, got: {problems}",
        )

    def test_xml_tag_in_block_scalar_description_flagged(self):
        # Multiline block-scalar description — pins frontmatter_field's block-scalar capture.
        problems = []
        V.validate_entry(
            self._skill(
                "---\nname: t\ndescription: |\n  spin up a <project>-x desk\n---\nbody"
            ),
            problems,
        )
        self.assertTrue(
            any("XML tag" in p and "<project>" in p for p in problems),
            f"expected an XML-tag blocker on a block-scalar description, got: {problems}",
        )

    def test_angle_bracket_in_body_not_flagged(self):
        # Only the description field is checked; body angle brackets are fine.
        problems = []
        V.validate_entry(
            self._skill("---\nname: t\ndescription: d\n---\nName it <project>-x/."),
            problems,
        )
        self.assertEqual(problems, [])

    def test_bad_origin_target_summary(self):
        e = self._skill("---\nname: t\ndescription: d\n---\nbody")
        e.update(origin="bogus", targets=["claude-code", "not-a-target"], summary="  ")
        problems = []
        V.validate_entry(e, problems)
        self.assertTrue(any("origin" in p for p in problems))
        self.assertTrue(any("unknown target" in p for p in problems))
        self.assertTrue(any("summary" in p for p in problems))

    def test_origin_enum_is_authored_sourced(self):
        self.assertEqual(V.VALID_ORIGIN, {"authored", "sourced"})

    def test_old_vocabulary_internal_rejected(self):
        e = self._skill("---\nname: t\ndescription: d\n---\nbody")
        e.update(origin="internal")
        problems = []
        V.validate_entry(e, problems)
        self.assertTrue(
            any("origin" in p and "authored" in p and "sourced" in p for p in problems)
        )

    def test_sourced_origin_accepted(self):
        e = self._skill("---\nname: t\ndescription: d\n---\nbody")
        e.update(origin="sourced")
        problems = []
        V.validate_entry(e, problems)
        self.assertEqual(problems, [])


class RealTree(unittest.TestCase):
    def test_main_passes_on_real_tree(self):
        self.assertEqual(V.main(), 0)


if __name__ == "__main__":
    unittest.main()
