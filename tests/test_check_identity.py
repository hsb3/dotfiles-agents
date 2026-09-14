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


def _scan(content, requires=frozenset(), skip_identity=False):
    """Write content to a temp file, run scan_file, return the problem strings."""
    d = tempfile.mkdtemp()
    fp = os.path.join(d, "SKILL.md")
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write(content)
    problems = []
    I.scan_file(fp, "fixture/SKILL.md", set(requires), problems,
                skip_identity=skip_identity)
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

    def test_declared_local_tool_still_flagged(self):
        # A covering `requires: cli:<tool>` used to silence this; it is now a finding either way.
        probs = _scan("run cc-project-memory init", requires={"cli:cc-project-memory"})
        self.assertTrue(any("cc-project-memory" in p for p in probs))

    def test_roster_requires_of_local_tool_flagged(self):
        probs = []
        I.check_roster_requires(
            [{"id": "some-skill", "requires": "[cli:cc-project-memory, env:dotfiles]"}], probs)
        self.assertEqual(len(probs), 1)
        self.assertIn("primitives-core.yaml: some-skill requires `cli:cc-project-memory`", probs[0])


class Precision(unittest.TestCase):
    def test_roster_requires_of_public_tool_not_flagged(self):
        probs = []
        I.check_roster_requires([{"id": "x", "requires": "[cli:gh, cli:bun, hosted-mcp]"}], probs)
        self.assertEqual(probs, [])

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


class VendoredBaseExemption(unittest.TestCase):
    """A vendored `base/` holds third-party bytes verbatim: it carries none of OUR
    personalization, and correcting it there is forbidden (a hand-edit registers as
    `diverged` against the pinned ref). So IDENTITY tokens are not scanned inside one --
    but machine paths and secrets, which would be real defects in any bytes we ship, still
    are. The exempt prefixes are derived from the roster, never hardcoded."""

    def test_identity_token_exempt_inside_vendored_base(self):
        # "the #1 source of" is an idiom, not an issue reference
        body = "Unencrypted settings are the #1 source of credential leaks.\n"
        self.assertTrue(_scan(body))                       # red without the exemption
        self.assertFalse(_scan(body, skip_identity=True))  # green inside a vendored base

    def test_secret_literal_still_flagged_inside_vendored_base(self):
        p = _scan("token: ghp_" + "a" * 24 + "\n", skip_identity=True)
        self.assertTrue(any("PAT literal" in x for x in p))

    def test_machine_path_still_flagged_inside_vendored_base(self):
        p = _scan("see /Users/someone/notes\n", skip_identity=True)
        self.assertTrue(any("machine-absolute path" in x for x in p))

    def test_bases_derived_from_roster_not_hardcoded(self):
        bases = I._vendored_bases()
        self.assertTrue(bases, "roster declares vendored entries; none were derived")
        for b in bases:
            self.assertTrue(b.startswith("primitives-core/skills/"), b)
            self.assertTrue(b.endswith("base" + os.sep), b)
            self.assertTrue(os.path.isdir(os.path.join(I.REPO, b)), f"{b} not on disk")

    def test_every_vendored_roster_entry_has_a_base_dir(self):
        """The exemption is only sound if `origin: vendored` really means a base/ tree --
        an entry without one would silently exempt nothing while looking covered."""
        from check_roster import parse_roster
        vendored = [e for e in parse_roster(os.path.join(I.REPO, "primitives-core.yaml"))
                    if (e.get("origin") or "").strip() == "vendored"]
        self.assertTrue(vendored)
        for e in vendored:
            self.assertTrue(
                os.path.isdir(os.path.join(I.REPO, e["source"], "base")),
                f"vendored entry {e['id']} has no base/ dir",
            )


class ExamplesIssueRefCarveOut(unittest.TestCase):
    """The examples/ carve-out exempts the ISSUE-REFERENCE rule only. A bare #NNN in an
    examples/ file is sample data demonstrating ref-linkify (self-evident, not real
    personalization); every other identity rule still applies there unchanged."""

    def _scan_at(self, rel, content):
        d = tempfile.mkdtemp()
        fp = os.path.join(d, os.path.basename(rel))
        with open(fp, "w", encoding="utf-8") as fh:
            fh.write(content)
        problems = []
        I.scan_file(fp, rel, set(), problems, skip_issue_ref=I._in_examples_dir(rel))
        return problems

    def test_bare_issue_ref_in_skill_body_still_flagged(self):
        probs = self._scan_at("primitives-core/skills/comms/SKILL.md", "fixes #123 today")
        self.assertTrue(any("issue" in p for p in probs))

    def test_bare_issue_ref_in_scripts_still_flagged(self):
        probs = self._scan_at(
            "primitives-core/skills/comms/scripts/deliver.py", "# see #123 for context"
        )
        self.assertTrue(any("issue" in p for p in probs))

    def test_bare_issue_ref_in_examples_dir_passes(self):
        probs = self._scan_at(
            "primitives-core/skills/comms/examples/morning-briefing/sample.spec.json",
            '{"footer": "tracked on #123"}',
        )
        self.assertFalse(any("issue" in p for p in probs))

    def test_personal_name_in_examples_dir_still_flagged(self):
        # The carve-out is issue-ref-only — every other identity rule still applies.
        probs = self._scan_at(
            "primitives-core/skills/comms/examples/morning-briefing/sample.spec.json",
            "Produce Henry's report.",
        )
        self.assertTrue(any("Henry" in p for p in probs))

    def test_org_token_in_examples_dir_still_flagged(self):
        probs = self._scan_at(
            "primitives-core/skills/comms/examples/morning-briefing/sample.spec.json",
            '{"note": "deploy to raptorxai prod"}',
        )
        self.assertTrue(any("raptorxai" in p for p in probs))


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

    def test_overlong_description_flagged(self):
        desc = "a" * (I.MAX_DESCRIPTION + 1)
        probs = self._fm(f"---\nname: x\ndescription: {desc}\n---\nbody")
        self.assertTrue(any(str(I.MAX_DESCRIPTION) in p and "description" in p for p in probs),
                        probs)

    def test_description_at_cap_ok(self):
        desc = "a" * I.MAX_DESCRIPTION
        self.assertEqual(self._fm(f"---\nname: x\ndescription: {desc}\n---\nbody"), [])

    def test_block_scalar_description_measured_folded(self):
        """A `>-` block scalar folds to one line before measuring, same as gen_opencode.

        Line count derived from the cap, so the fixture stays over it if the cap moves.
        """
        line = "a" * 100
        desc = "\n  ".join([line] * (I.MAX_DESCRIPTION // len(line) + 2))
        probs = self._fm(f"---\nname: x\ndescription: >-\n  {desc}\n---\nbody")
        self.assertTrue(any(str(I.MAX_DESCRIPTION) in p for p in probs), probs)


class PlainScalarParseability(unittest.TestCase):
    """The manager agent shipped published for weeks with an unquoted description
    containing ': '. YAML ended the scalar at the colon, Claude Code dropped every
    frontmatter field without erroring, and the agent ran with no model and no tool
    allowlist while `make ci` stayed green. These prove the gate that closes it."""

    def _faults(self, fm):
        return [why for _key, why in I._plain_scalar_faults(fm)]

    def test_colon_space_in_unquoted_value_flagged(self):
        fm = "name: manager\ndescription: owns a chain end to end: turns done into briefs"
        self.assertTrue(any("nested mapping" in w for w in self._faults(fm)))

    def test_quoting_the_value_clears_it(self):
        fm = 'name: manager\ndescription: "owns a chain end to end: turns done into briefs"'
        self.assertEqual(self._faults(fm), [])

    def test_trailing_colon_flagged(self):
        self.assertTrue(self._faults("name: x\ndescription: use it when:"))

    def test_inline_comment_truncation_flagged(self):
        self.assertTrue(any("truncates" in w for w in self._faults("name: x\nprotected: Makefile # note")))

    def test_folded_block_scalar_is_valid_yaml_not_a_fault(self):
        # 15 shipped SKILL.md files open their description with `>-`; the content lives on
        # the indented lines below, which are not top-level keys.
        fm = "name: x\ndescription: >-\n  a folded description with a colon: right here"
        self.assertEqual(self._faults(fm), [])

    def test_list_and_mapping_children_not_scanned(self):
        self.assertEqual(self._faults("handoff:\n  mode: external\n  location: a board: really"), [])

    def test_real_agents_and_skills_parse(self):
        """The shipped tree itself — the regression this gate exists to prevent."""
        self.assertEqual(I.main(), 0)


class RealTree(unittest.TestCase):
    def test_shipped_tree_is_identity_neutral(self):
        self.assertEqual(I.main(), 0)

    def test_the_two_description_caps_are_the_same_number(self):
        """check_identity and gen_opencode each hold their own MAX_DESCRIPTION. Nothing but
        this test stops them drifting: raise one alone and both gates stay green while
        disagreeing about every description in the gap between them."""
        import gen_opencode
        self.assertEqual(I.MAX_DESCRIPTION, gen_opencode.MAX_DESCRIPTION)

    def test_every_shipped_skill_description_is_under_the_cap(self):
        """Derived by walking the tree, never from a recorded file list or count.

        A forward-guard with zero real subjects today — the longest shipped description is
        well under the cap, so this passes even with the check disabled. Red-ability lives in
        the two Frontmatter fixture tests; this one only catches a future over-long skill.
        """
        root = os.path.join(I.REPO, "primitives-core", "skills")
        cap = str(I.MAX_DESCRIPTION)
        checked, over = 0, []
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                fp = os.path.join(dirpath, f)
                if f != "SKILL.md" or os.path.islink(fp):
                    continue
                checked += 1
                problems = []
                I.check_frontmatter(fp, os.path.relpath(fp, I.REPO), True, problems)
                over += [p for p in problems if cap in p]
        self.assertEqual(over, [])
        self.assertGreater(checked, 0)


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
