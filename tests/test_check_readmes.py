"""check_readmes.py — the per-unit README gate.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's REPO/SKILLS_DIR/PLUGINS_DIR constants are pointed at
them for the duration of each test.

Every check has a fixture that makes it go RED, plus one asserting the live tree is green.
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_readmes as R  # noqa: E402


class ReadmeGate(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-readmes-")
        self.saved = {k: getattr(R, k) for k in ("REPO", "SKILLS_DIR", "PLUGINS_DIR")}
        R.REPO = self.fix
        R.SKILLS_DIR = os.path.join(self.fix, "primitives-core", "skills")
        R.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        os.makedirs(R.SKILLS_DIR)
        os.makedirs(R.PLUGINS_DIR)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(R, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def _unit(self, kind, name, readme="# alpha\n\nWhat it does.\n"):
        root = R.SKILLS_DIR if kind == "skill" else R.PLUGINS_DIR
        d = os.path.join(root, name)
        os.makedirs(d)
        if readme is not None:
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
                fh.write(readme)
        return d

    def test_healthy_tree_is_clean(self):
        self._unit("skill", "alpha")
        self._unit("plugin", "beta")
        self.assertEqual(R.problems(), [])

    def test_missing_skill_readme_is_red(self):
        self._unit("skill", "alpha", readme=None)
        found = R.problems()
        self.assertEqual(len(found), 1)
        self.assertIn("skill 'alpha': no README.md", found[0])

    def test_missing_plugin_readme_is_red(self):
        self._unit("plugin", "beta", readme=None)
        found = R.problems()
        self.assertEqual(len(found), 1)
        self.assertIn("plugin 'beta': no README.md", found[0])

    def test_empty_readme_is_red(self):
        self._unit("skill", "alpha", readme="\n   \n\t\n")
        self.assertIn("is empty", "\n".join(R.problems()))

    def test_readme_without_h1_is_red(self):
        self._unit("skill", "alpha", readme="\nSome prose with no title.\n")
        self.assertIn("does not open with an H1", "\n".join(R.problems()))

    def test_setext_and_h2_do_not_count_as_a_title(self):
        self._unit("skill", "alpha", readme="## alpha\n\nWhat it does.\n")
        self.assertIn("does not open with an H1", "\n".join(R.problems()))

    def test_dangling_symlink_readme_is_red(self):
        d = self._unit("plugin", "beta", readme=None)
        os.symlink(os.path.join(self.fix, "nowhere", "README.md"), os.path.join(d, "README.md"))
        self.assertIn("no README.md", "\n".join(R.problems()))

    def test_symlinked_readme_is_accepted(self):
        src = self._unit("skill", "alpha")
        d = self._unit("plugin", "beta", readme=None)
        os.symlink(os.path.join(src, "README.md"), os.path.join(d, "README.md"))
        self.assertEqual(R.problems(), [])

    def test_dotted_dirs_and_loose_files_are_not_units(self):
        os.makedirs(os.path.join(R.SKILLS_DIR, ".hidden"))
        with open(os.path.join(R.SKILLS_DIR, "loose.md"), "w", encoding="utf-8") as fh:
            fh.write("not a unit\n")
        self.assertEqual(R.problems(), [])


class InstallAndMembership(ReadmeGate):
    """Checks 4 and 5 — the install block and the bundle table are derived from the assemblies."""

    def _ship(self, plugin, skill):
        d = os.path.join(R.PLUGINS_DIR, plugin, "skills")
        os.makedirs(d, exist_ok=True)
        os.symlink(os.path.join(R.SKILLS_DIR, skill), os.path.join(d, skill))

    def test_install_block_naming_a_plugin_that_does_not_ship_it_is_red(self):
        self._unit("skill", "alpha", readme="# alpha\n\n```\nclaude plugin install ghost@dotfiles-agents\n```\n")
        self.assertIn("install block names ['ghost'] but the skill ships in []", "\n".join(R.problems()))

    def test_install_block_missing_a_second_home_is_red(self):
        self._unit("skill", "alpha", readme="# alpha\n\n```\nclaude plugin install one@dotfiles-agents\n```\n")
        self._unit("plugin", "one", readme="# one\n\n`alpha`\n")
        self._unit("plugin", "two", readme="# two\n\n`alpha`\n")
        self._ship("one", "alpha")
        self._ship("two", "alpha")
        self.assertIn("names ['one'] but the skill ships in ['one', 'two']", "\n".join(R.problems()))

    def test_install_block_matching_both_homes_is_clean(self):
        self._unit("skill", "alpha", readme="# alpha\n\n```\nclaude plugin install one@dotfiles-agents\nclaude plugin install two@dotfiles-agents\n```\n")
        self._unit("plugin", "one", readme="# one\n\n`alpha`\n")
        self._unit("plugin", "two", readme="# two\n\n| `skills/alpha/` | row |\n")
        self._ship("one", "alpha")
        self._ship("two", "alpha")
        self.assertEqual(R.problems(), [])

    def test_bundle_readme_omitting_a_shipped_member_is_red(self):
        self._unit("skill", "alpha", readme="# alpha\n\n```\nclaude plugin install one@dotfiles-agents\n```\n")
        self._unit("plugin", "one", readme="# one\n\nNo table here.\n")
        self._ship("one", "alpha")
        hooks = os.path.join(R.PLUGINS_DIR, "one", "hooks", "guard")
        os.makedirs(hooks)
        os.makedirs(os.path.join(R.PLUGINS_DIR, "one", "hooks", "_lib"))
        found = "\n".join(R.problems())
        self.assertIn("never names shipped member `alpha`", found)
        self.assertIn("never names shipped member `guard`", found)
        self.assertNotIn("_lib", found)

    def test_standalone_readme_names_itself_by_h1(self):
        self._unit("skill", "alpha", readme="# alpha\n\n```\nclaude plugin install alpha@dotfiles-agents\n```\n")
        d = self._unit("plugin", "alpha", readme=None)
        os.symlink(os.path.join(R.SKILLS_DIR, "alpha", "README.md"), os.path.join(d, "README.md"))
        self._ship("alpha", "alpha")
        self.assertEqual(R.problems(), [])


class LiveTree(unittest.TestCase):
    def test_repo_is_green(self):
        self.assertEqual(R.problems(), [])

    def test_every_skill_and_plugin_dir_is_covered(self):
        kinds = {k for k, _, _ in R._units()}
        self.assertEqual(kinds, {"skill", "plugin"})
        self.assertGreater(len(R._units()), 40)


if __name__ == "__main__":
    unittest.main()
