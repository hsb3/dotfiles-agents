"""check_symlinks.py — the ADR 0017 symlink-assembly lint.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's REPO/PLUGINS_DIR/MARKETPLACE constants are pointed
at them for the duration of each test.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_symlinks as S  # noqa: E402


class SymlinkLint(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-symlinks-")
        self.saved = {k: getattr(S, k) for k in ("REPO", "PLUGINS_DIR", "MARKETPLACE")}
        S.REPO = self.fix
        S.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        S.MARKETPLACE = os.path.join(self.fix, ".claude-plugin", "marketplace.json")
        # minimal healthy repo: one skill source, one assembly linking to it
        os.makedirs(os.path.join(self.fix, "primitives-core", "skills", "alpha"))
        with open(os.path.join(self.fix, "primitives-core", "skills", "alpha", "SKILL.md"), "w") as fh:
            fh.write("---\nname: alpha\ndescription: x\n---\n")
        pdir = os.path.join(self.fix, "plugins", "alpha", "skills")
        os.makedirs(os.path.join(self.fix, "plugins", "alpha", ".claude-plugin"))
        os.makedirs(pdir)
        with open(os.path.join(self.fix, "plugins", "alpha", ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": "alpha"}, fh)
        os.symlink("../../../primitives-core/skills/alpha", os.path.join(pdir, "alpha"))
        os.makedirs(os.path.join(self.fix, ".claude-plugin"))
        with open(S.MARKETPLACE, "w") as fh:
            json.dump({"plugins": [{"name": "alpha", "source": "./plugins/alpha"}]}, fh)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(S, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def test_healthy_assembly_is_clean(self):
        self.assertEqual(S.symlink_problems(), [])
        self.assertEqual(S.marketplace_problems(), [])
        self.assertEqual(S.main(), 0)

    def test_broken_symlink_is_red(self):
        os.symlink(
            "../../../primitives-core/skills/gone",
            os.path.join(self.fix, "plugins", "alpha", "skills", "gone"),
        )
        problems = S.symlink_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("broken symlink", problems[0])

    def test_escaping_symlink_is_red(self):
        outside = tempfile.mkdtemp(prefix="outside-")
        self.addCleanup(shutil.rmtree, outside, True)
        os.symlink(outside, os.path.join(self.fix, "plugins", "alpha", "skills", "escape"))
        problems = S.symlink_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("escapes the repo", problems[0])

    def test_unlisted_assembly_is_red(self):
        os.makedirs(os.path.join(self.fix, "plugins", "orphan", ".claude-plugin"))
        problems = S.marketplace_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("orphan", problems[0])
        self.assertIn("not listed", problems[0])

    def test_listed_but_missing_source_is_red(self):
        with open(S.MARKETPLACE, "w") as fh:
            json.dump(
                {"plugins": [
                    {"name": "alpha", "source": "./plugins/alpha"},
                    {"name": "ghost", "source": "./plugins/ghost"},
                ]},
                fh,
            )
        problems = S.marketplace_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("ghost", problems[0])
        self.assertIn("does not exist", problems[0])

    def test_missing_plugin_json_is_red(self):
        os.remove(os.path.join(self.fix, "plugins", "alpha", ".claude-plugin", "plugin.json"))
        problems = S.marketplace_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugin.json", problems[0])

    def test_non_relative_source_is_red(self):
        with open(S.MARKETPLACE, "w") as fh:
            json.dump({"plugins": [{"name": "alpha", "source": "github:foo/bar"}]}, fh)
        problems = S.marketplace_problems()
        self.assertTrue(any("not a relative" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
