"""detect_kind — candidate classification (ported from workbench TestDetectKind)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.candidate import agent_identities, detect_kind, resolved_candidate_dir  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class TestDetectKind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def _candidate(self, name):
        p = os.path.join(self.tmp, name)
        os.makedirs(p)
        return p

    def test_skill(self):
        p = self._candidate("s")
        _write(os.path.join(p, "SKILL.md"), "---\nname: s\n---\nbody")
        self.assertEqual(detect_kind(p), "skill")

    def test_plugin(self):
        p = self._candidate("p")
        _write(os.path.join(p, ".claude-plugin", "plugin.json"), "{}")
        self.assertEqual(detect_kind(p), "plugin")

    def test_agent(self):
        p = self._candidate("a")
        _write(os.path.join(p, "AGENTS.md"), "---\ndescription: d\n---\nprompt")
        self.assertEqual(detect_kind(p), "agent")

    def test_unrecognizable(self):
        p = self._candidate("x")
        _write(os.path.join(p, "README.md"), "readme only")
        self.assertIsNone(detect_kind(p))

    def test_skill_beats_plugin_when_both_present(self):
        p = self._candidate("sp")
        _write(os.path.join(p, "SKILL.md"), "---\nname: sp\n---\nbody")
        _write(os.path.join(p, ".claude-plugin", "plugin.json"), "{}")
        self.assertEqual(detect_kind(p), "skill")


class TestResolvedCandidateDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_dir_is_passed_through_unchanged_no_copy(self):
        p = os.path.join(self.tmp, "a")
        os.makedirs(p)
        _write(os.path.join(p, "AGENTS.md"), "---\ndescription: d\n---\nprompt")
        with resolved_candidate_dir(p) as resolved:
            self.assertEqual(resolved, p)
            self.assertEqual(detect_kind(resolved), "agent")
        # Passthrough dir is untouched (not removed) after the context exits.
        self.assertTrue(os.path.isdir(p))
        self.assertTrue(os.path.isfile(os.path.join(p, "AGENTS.md")))

    def test_flat_md_file_is_staged_into_a_new_dir_and_cleaned_up(self):
        md = os.path.join(self.tmp, "solo-agent.md")
        _write(md, "---\nname: solo-agent\n---\nprompt")
        with resolved_candidate_dir(md) as staged:
            self.assertNotEqual(staged, self.tmp)
            self.assertTrue(os.path.isdir(staged))
            staged_file = os.path.join(staged, "solo-agent.md")
            self.assertTrue(os.path.isfile(staged_file))
            with open(staged_file, encoding="utf-8") as fh:
                self.assertIn("name: solo-agent", fh.read())
            self.assertEqual(detect_kind(staged), "agent")
        # Cleaned up after normal exit; original file untouched.
        self.assertFalse(os.path.exists(staged))
        self.assertTrue(os.path.isfile(md))

    def test_flat_md_staged_dir_cleaned_up_on_exception(self):
        md = os.path.join(self.tmp, "solo-agent.md")
        _write(md, "---\nname: solo-agent\n---\nprompt")
        staged_holder = {}
        with self.assertRaises(RuntimeError):
            with resolved_candidate_dir(md) as staged:
                staged_holder["path"] = staged
                raise RuntimeError("boom")
        self.assertFalse(os.path.exists(staged_holder["path"]))

    def test_nonexistent_path_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            with resolved_candidate_dir(os.path.join(self.tmp, "nope")):
                pass  # pragma: no cover

    def test_non_md_file_raises_value_error(self):
        f = os.path.join(self.tmp, "notes.txt")
        _write(f, "not markdown")
        with self.assertRaises(ValueError):
            with resolved_candidate_dir(f):
                pass  # pragma: no cover


class TestAgentIdentities(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_unique_frontmatter_and_fallback_names_are_retained(self):
        # Removing the shared identity loader or changing fallback resolution
        # would make this mapping wrong.
        _write(os.path.join(self.tmp, "fallback.md"), "fallback body")
        _write(
            os.path.join(self.tmp, "renamed.md"),
            "---\nname: explicit\ndescription: d\n---\nexplicit body",
        )
        self.assertEqual(
            agent_identities(self.tmp),
            {"fallback": "fallback.md", "explicit": "renamed.md"},
        )

    def test_duplicate_explicit_names_fail_before_classification(self):
        # Removing duplicate validation would let the later file overwrite the
        # first agent definition in both adapters.
        _write(os.path.join(self.tmp, "first.md"), "---\nname: same\n---\none")
        _write(os.path.join(self.tmp, "second.md"), "---\nname: same\n---\ntwo")
        with self.assertRaisesRegex(ValueError, "duplicate agent name 'same'.*first.md.*second.md"):
            detect_kind(self.tmp)

    def test_explicit_name_and_filename_fallback_collision_fail(self):
        # A missing explicit-name/fallback collision guard would silently
        # overwrite the fallback agent with this frontmatter-defined one.
        _write(os.path.join(self.tmp, "same.md"), "fallback body")
        _write(os.path.join(self.tmp, "other.md"), "---\nname: same\n---\nother body")
        with self.assertRaisesRegex(ValueError, "duplicate agent name 'same'.*other.md.*same.md"):
            agent_identities(self.tmp)

    def test_quoted_empty_names_fall_back_to_distinct_filenames(self):
        # Retaining the post-quote empty string would falsely reject these as
        # duplicate '' identities instead of using the adapters' filename fallback.
        _write(os.path.join(self.tmp, "one.md"), "---\nname: \"\"\n---\none")
        _write(os.path.join(self.tmp, "two.md"), "---\nname: \"\"\n---\ntwo")
        self.assertEqual(
            agent_identities(self.tmp), {"one": "one.md", "two": "two.md"}
        )

if __name__ == "__main__":
    unittest.main()
