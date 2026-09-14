"""Tests for scripts/check_agent_refs.py -- no shipped body names a nonexistent agent.

Proves the extractor pulls the two reference shapes it claims (an `agent`/`subagent_type`
key with a literal value, and a backticked name adjacent to the word agent/subagent),
that it goes RED on a fixture naming an agent that does not exist, and that it is GREEN
on the live tree. The fixture is built in a tempdir -- never under `primitives-core/`,
which the roster guard would flag as an orphan.

The red fixture reproduces the shape of the real defect (`board-analyst`, fixed in
f7a1f3a): a bolded, backticked name followed by the word "agent" in skill prose.

Stdlib-only.
"""

import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_agent_refs as A  # noqa: E402


def _tree(spec):
    """Build {relpath: text} under a tempdir's `primitives-core/` and check it.

    The fixture mirrors the real layout so reported paths are repo-shaped
    (`primitives-core/skills/...`), which is what `EXEMPTIONS` is keyed by.
    Returns (scan_root, problems).
    """
    base = tempfile.mkdtemp()
    scan_root = os.path.join(base, "primitives-core")
    for rel, text in spec.items():
        full = os.path.join(scan_root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)
    return scan_root, A.check_tree(scan_root, base, A.roster_agents())


def _names(text, rel="primitives-core/skills/x/SKILL.md"):
    return sorted({r.name for r in A.references(text, rel)})


class Extraction(unittest.TestCase):
    def test_key_forms(self):
        self.assertEqual(["reviewer"], _names('"subagent_type": "reviewer"'))
        self.assertEqual(["reviewer"], _names("subagent_type='reviewer'"))
        self.assertEqual(["builder"], _names('{"agent_type":"builder"}'))
        self.assertEqual(["builder"], _names("agent: builder"))

    def test_unquoted_value_that_is_not_a_yaml_scalar_is_not_a_reference(self):
        """Code reading the field, and prose with a colon, are not dispatches."""
        self.assertEqual([], _names('    "agent_type": agent_type,'))
        self.assertEqual([], _names('agent_type = payload.get("agent_type")'))
        self.assertEqual([], _names("Two kinds of row settle an agent: its delegation row"))
        self.assertEqual([], _names("sys.exit(0)  # not our agent: silent, nothing logged"))
        # A bare value is a YAML scalar only when it is the whole rest of the line.
        self.assertEqual([], _names("agent: its delegation row settles the question"))

    def test_backtick_adjacent_forms(self):
        self.assertEqual(["scout"], _names("Fan out `scout` agents wherever it pays."))
        self.assertEqual(["manager"], _names("a `manager` subagent ends its turn"))

    def test_bold_wrapped_backticks_are_read(self):
        """The real defect was written `**`board-analyst`** agent`."""
        self.assertEqual(
            ["board-analyst"],
            _names("the **`board-analyst`** agent (this plugin) produces the changeset"),
        )

    def test_plugin_namespace_is_stripped(self):
        self.assertEqual(["builder"], _names("`atelier:builder` agent"))
        self.assertEqual(["pb-builder"], _names('"subagent_type": "pocketbase:pb-builder"'))

    def test_prose_without_backticks_is_not_a_reference(self):
        self.assertEqual([], _names("dispatch a scout agent to read the tree"))
        self.assertEqual([], _names("the reviewer agent re-derives the claim"))

    def test_unrelated_backticks_are_not_references(self):
        self.assertEqual([], _names("Cite `path:line` and a canonical doc."))
        self.assertEqual([], _names("`default_agent` is an opencode field"))
        self.assertEqual([], _names('agent_type = tool_input.get("subagent_type")'))

    def test_backtick_after_the_noun_is_not_a_reference(self):
        """`agent `X`` is ambiguous English: the backticked token qualifies nothing."""
        self.assertEqual([], _names("Each agent `must` obey the covenant."))
        self.assertEqual([], _names("See the agent `path:line` convention."))
        self.assertEqual([], _names("dispatch the agent `reviewer` for that"))

    def test_the_noun_matches_case_insensitively(self):
        self.assertEqual(["scout"], _names("dispatch the `scout` Agent now"))
        self.assertEqual(["explore"], _names("parallel `explore` AGENTS run"))
        self.assertEqual(["manager"], _names("a `manager` SubAgent ends its turn"))

    def test_line_numbers_are_reported(self):
        refs = A.references("one\ntwo\n`scout` agents\n", "p.md")
        self.assertEqual([(3, "scout")], [(r.lineno, r.name) for r in refs])


class RedOnADanglingName(unittest.TestCase):
    def test_fixture_naming_a_nonexistent_agent_is_flagged(self):
        _root, probs = _tree({
            "skills/board-triage/SKILL.md":
                "split the loop: the **`board-analyst`** agent produces the changeset\n",
        })
        self.assertTrue(probs, "a made-up agent name must be a violation")
        self.assertIn("board-analyst", probs[0])
        self.assertIn("skills/board-triage/SKILL.md:1", probs[0])

    def test_dangling_name_in_a_hook_body_is_flagged(self):
        _root, probs = _tree({
            "hooks/h/hook.py": 'DISPATCH = {"subagent_type": "ghost-writer"}\n',
        })
        self.assertTrue(any("ghost-writer" in p for p in probs))

    def test_dangling_name_in_a_command_is_flagged(self):
        _root, probs = _tree({"commands/go.md": "agent: nobody-here\n"})
        self.assertTrue(any("nobody-here" in p for p in probs))

    def test_main_exits_nonzero_on_the_fixture(self):
        root, _probs = _tree({"skills/s/SKILL.md": "`board-analyst` agent\n"})
        self.assertEqual(1, A.main(["--root", root]))

    def test_report_exits_nonzero_when_it_prints_a_dangling_row(self):
        """A --report that always exits 0 is a false green the moment anyone wires it."""
        root, _probs = _tree({"skills/s/SKILL.md": "`board-analyst` agent\n"})
        self.assertEqual(1, A.main(["--report", "--root", root]))


class GreenOnLegitimateNames(unittest.TestCase):
    def test_roster_agent_is_clean(self):
        _root, probs = _tree({"skills/s/SKILL.md": "dispatch the `reviewer` agent\n"})
        self.assertEqual([], probs)

    def test_namespaced_roster_agent_is_clean(self):
        _root, probs = _tree({"skills/s/SKILL.md": "the `atelier:builder` agent\n"})
        self.assertEqual([], probs)

    def test_harness_builtins_are_clean(self):
        _root, probs = _tree({
            "skills/s/SKILL.md":
                "dispatch parallel `Explore` agents; the built-in is "
                "`general-purpose`. The `fork` agent continues the caller's context.\n",
        })
        self.assertEqual([], probs)

    def test_main_exits_zero_on_a_clean_fixture(self):
        root, _probs = _tree({"skills/s/SKILL.md": "the `scout` agent reads\n"})
        self.assertEqual(0, A.main(["--root", root]))

    def test_report_exits_zero_on_a_clean_fixture(self):
        root, _probs = _tree({"skills/s/SKILL.md": "the `scout` agent reads\n"})
        self.assertEqual(0, A.main(["--report", "--root", root]))

    def test_unscanned_suffixes_are_ignored(self):
        _root, probs = _tree({"skills/s/schema.xsd": "`board-analyst` agent\n"})
        self.assertEqual([], probs)


class Exemptions(unittest.TestCase):
    def test_every_exempt_reference_is_suppressed(self):
        """Rebuild each exempted file in a tempdir with its exempted name; expect silence."""
        for (rel, name) in sorted(A.EXEMPTIONS):
            with self.subTest(path=rel, agent=name):
                inner = os.path.relpath(rel, "primitives-core")
                _root, probs = _tree({inner: "the `%s` agent\n" % name})
                self.assertEqual([], probs)

    def test_every_exemption_still_suppresses_something_live(self):
        self.assertEqual([], A.stale_exemptions())

    def test_a_stale_exemption_is_a_gate_violation(self):
        """Detecting staleness is useless unless `problems()` actually surfaces it."""
        bogus = ("primitives-core/skills/nowhere/SKILL.md", "ghost-writer")
        with unittest.mock.patch.dict(A.EXEMPTIONS, {bogus: "fixture"}):
            probs = A.problems()
        self.assertTrue(any("ghost-writer" in p and "stale" in p for p in probs), probs)


class RealTree(unittest.TestCase):
    def test_live_tree_names_no_nonexistent_agent(self):
        self.assertEqual([], A.problems())

    def test_live_tree_gate_exits_zero(self):
        self.assertEqual(0, A.main([]))

    def test_roster_agents_are_derived_not_hardcoded(self):
        agents = A.roster_agents()
        self.assertIn("builder", agents)
        self.assertIn("scout", agents)
        self.assertNotIn("readme", agents)

    def test_both_derivation_sources_are_live_and_agree(self):
        """The valid set unions disk and roster; assert neither branch is dead weight."""
        disk, manifest = A.disk_agents(), A.manifest_agents()
        self.assertTrue(disk, "no agent bodies found on disk")
        self.assertTrue(manifest, "roster declares no type: agent entries")
        self.assertEqual(disk, manifest, "roster <-> disk agent drift (make check owns the fix)")

    def test_live_tree_has_references_to_check(self):
        """A gate over an empty extraction proves nothing -- assert it has real subjects."""
        found = A.scan()
        self.assertTrue(found, "extractor found no agent references at all")


if __name__ == "__main__":
    unittest.main()
