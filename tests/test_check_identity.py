"""Tests for scripts/check_identity.py -- the identity-neutrality lint (D6 floor check 1).

Proves the lint is demonstrably red-able on seeded violations and green on neutral content,
and guards two precision cases that must NOT fire (a skill-id embedding a name; a checklist
GH-NN id). Also asserts the real shipped tree is clean (the neutralization landed). Stdlib-only;
every fixture is a tempdir, never under primitives-core/.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_identity as I  # noqa: E402


def _scan(content, requires=frozenset()):
    """Write content to a temp file, run scan_file, return the problem strings."""
    d = tempfile.mkdtemp()
    fp = os.path.join(d, "SKILL.md")
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)
    problems = []
    I.scan_file(fp, "fixture/SKILL.md", set(requires), problems)
    return problems


class RedAble(unittest.TestCase):
    def test_personal_name_flagged(self):
        self.assertTrue(any("Henry" in p for p in _scan("Produce Henry's report.")))

    def test_client_token_flagged(self):
        self.assertTrue(any("raptorxai" in p for p in _scan("deploy to raptorxai prod")))

    def test_owner_handle_flagged(self):
        self.assertTrue(any("hsb3" in p for p in _scan("run against hsb3/projects/9")))

    def test_issue_ref_flagged(self):
        self.assertTrue(any("issue" in p for p in _scan("fixes #128 today")))

    def test_multica_key_flagged(self):
        self.assertTrue(any("issue" in p for p in _scan("see DEV-33 and MUL-4252")))

    def test_machine_path_flagged(self):
        self.assertTrue(any("/Users" in p for p in _scan("cd /Users/someone/repo")))

    def test_secret_literal_flagged(self):
        self.assertTrue(any("PAT" in p for p in _scan("token: ghp_" + "a" * 30)))

    def test_undeclared_local_tool_flagged(self):
        self.assertTrue(any("cc-project-memory" in p for p in _scan("run cc-project-memory init")))


class Precision(unittest.TestCase):
    def test_declared_local_tool_exempt(self):
        # Same tool reference, but the roster entry declares it in requires -> not flagged.
        probs = _scan("run cc-project-memory init", requires={"cli:cc-project-memory"})
        self.assertFalse(any("cc-project-memory" in p for p in probs))

    def test_skill_id_with_embedded_name_not_flagged(self):
        # A name embedded in a hyphenated skill id (e.g. foo-henry) is a structural reference,
        # not baked-in identity — the hyphen-boundary rule must not flag the embedded token.
        self.assertEqual([p for p in _scan("compose with the foo-henry skill")], [])

    def test_checklist_gh_id_not_flagged(self):
        # GH-01..GH-09 are repo-meta-structure checklist ids, not issue refs.
        self.assertEqual([p for p in _scan("| GH-08 | .github/ | ci check |")], [])

    def test_hex_colour_not_read_as_issue(self):
        self.assertEqual([p for p in _scan('"color": "#003366"')], [])

    def test_neutral_body_clean(self):
        self.assertEqual(_scan("Produce your recurring reports for the owner."), [])


class Frontmatter(unittest.TestCase):
    def _fm(self, content, is_skill=True):
        d = tempfile.mkdtemp()
        fp = os.path.join(d, "SKILL.md")
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(content)
        problems = []
        I.check_frontmatter(fp, "fixture/SKILL.md", is_skill, problems)
        return problems

    def test_missing_description_flagged(self):
        self.assertTrue(any("description" in p for p in self._fm("---\nname: x\n---\nbody")))

    def test_xml_tag_in_description_flagged(self):
        probs = self._fm("---\nname: x\ndescription: use <example> here\n---\nbody")
        self.assertTrue(any("XML" in p for p in probs))

    def test_clean_frontmatter_ok(self):
        self.assertEqual(self._fm("---\nname: x\ndescription: a clean one-liner\n---\nbody"), [])


class RealTree(unittest.TestCase):
    def test_shipped_tree_is_identity_neutral(self):
        self.assertEqual(I.main(), 0)


class CommandScope(unittest.TestCase):
    """Proves commands are actually inside the identity scan (decision-010): before that
    change, SCAN_ROOTS omitted primitives-core/commands entirely, so the guard printed a
    clean run while scanning zero command bodies."""

    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-identity-command-")
        self.saved_repo = I.REPO
        self.saved_roots = I.SCAN_ROOTS
        # Mirror whatever roots the module itself declares (relative to its real REPO) into
        # the fixture, so this test is genuinely sensitive to a root being added or dropped
        # rather than hand-asserting "commands" belongs in the list.
        rel_roots = [os.path.relpath(p, self.saved_repo) for p in self.saved_roots]
        I.REPO = self.fix
        I.SCAN_ROOTS = tuple(os.path.join(self.fix, r) for r in rel_roots)
        with open(os.path.join(self.fix, "primitives-core.yaml"), "w", encoding="utf-8") as fh:
            fh.write("primitives:\n")

    def tearDown(self):
        I.REPO = self.saved_repo
        I.SCAN_ROOTS = self.saved_roots
        shutil.rmtree(self.fix, ignore_errors=True)

    def test_command_body_identity_violation_is_flagged(self):
        cmd_dir = os.path.join(self.fix, "primitives-core", "commands")
        os.makedirs(cmd_dir)
        with open(os.path.join(cmd_dir, "activate.md"), "w", encoding="utf-8") as fh:
            fh.write("---\ndescription: x\n---\nProduce Henry's report.\n")
        self.assertEqual(I.main(), 1)


if __name__ == "__main__":
    unittest.main()
