"""check_symlinks.py — the ADR 0017 symlink-assembly lint.

Fixture repos are built under a tempdir (never under primitives-core/, per the roster
guard's orphan rule) and the module's REPO/PLUGINS_DIR/MARKETPLACE constants are pointed
at them for the duration of each test.
"""

import contextlib
import io
import json
import os
import re
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
        # alpha is a standalone (1 skill, no agents/hooks): give it a compliant README
        # symlink so the baseline fixture stays healthy once the README check exists.
        with open(os.path.join(self.fix, "primitives-core", "skills", "alpha", "README.md"), "w") as fh:
            fh.write("# alpha\n")
        os.symlink(
            "../../primitives-core/skills/alpha/README.md",
            os.path.join(self.fix, "plugins", "alpha", "README.md"),
        )
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


class ReadmeConvention(unittest.TestCase):
    """Standalone (1 skill, no agents/hooks) plugins must symlink README.md to the
    skill's own README; bundles (>1 skill, or any agent/hook) may hand-author it."""

    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-symlinks-readme-")
        self.saved = {k: getattr(S, k) for k in ("REPO", "PLUGINS_DIR", "MARKETPLACE")}
        S.REPO = self.fix
        S.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        S.MARKETPLACE = os.path.join(self.fix, ".claude-plugin", "marketplace.json")
        os.makedirs(os.path.join(self.fix, "primitives-core", "skills"))
        os.makedirs(self.fix, exist_ok=True)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(S, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def _make_plugin(self, plugin_id, skill_ids, agents=False, hooks=False, commands=False, readme=None):
        pdir = os.path.join(S.PLUGINS_DIR, plugin_id)
        os.makedirs(os.path.join(pdir, ".claude-plugin"))
        with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": plugin_id}, fh)
        skills_dir = os.path.join(pdir, "skills")
        os.makedirs(skills_dir)
        for sid in skill_ids:
            src = os.path.join(self.fix, "primitives-core", "skills", sid)
            os.makedirs(src, exist_ok=True)
            with open(os.path.join(src, "SKILL.md"), "w") as fh:
                fh.write(f"---\nname: {sid}\ndescription: x\n---\n")
            os.symlink(os.path.relpath(src, skills_dir), os.path.join(skills_dir, sid))
        if agents:
            agents_dir = os.path.join(pdir, "agents")
            os.makedirs(agents_dir)
            with open(os.path.join(agents_dir, "helper.md"), "w") as fh:
                fh.write("helper agent\n")
        if hooks:
            hooks_dir = os.path.join(pdir, "hooks")
            os.makedirs(hooks_dir)
            with open(os.path.join(hooks_dir, "hooks.json"), "w") as fh:
                fh.write("{}\n")
        if commands:
            commands_dir = os.path.join(pdir, "commands")
            os.makedirs(commands_dir)
            with open(os.path.join(commands_dir, "go.md"), "w") as fh:
                fh.write("---\ndescription: x\n---\ndo the thing\n")
        readme_path = os.path.join(pdir, "README.md")
        if readme == "regular":
            with open(readme_path, "w") as fh:
                fh.write(f"# {plugin_id}\n")
        elif readme == "correct":
            skill_readme = os.path.join(self.fix, "primitives-core", "skills", skill_ids[0], "README.md")
            with open(skill_readme, "w") as fh:
                fh.write(f"# {skill_ids[0]}\n")
            os.symlink(os.path.relpath(skill_readme, pdir), readme_path)
        elif readme and readme.startswith("symlink:"):
            target = readme.split(":", 1)[1]
            os.symlink(target, readme_path)
        elif readme is not None:
            raise ValueError(f"unknown readme mode {readme!r}")
        return pdir

    def test_standalone_regular_file_readme_is_red(self):
        self._make_plugin("gamma", ["gamma"], readme="regular")
        problems = S.readme_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugins/gamma/README.md", problems[0])
        self.assertIn("regular file", problems[0])

    def test_standalone_correct_symlink_readme_is_clean(self):
        self._make_plugin("delta", ["delta"], readme="correct")
        self.assertEqual(S.readme_problems(), [])

    def test_bundle_multi_skill_regular_readme_is_clean(self):
        self._make_plugin("epsilon", ["epsilon-one", "epsilon-two"], readme="regular")
        self.assertEqual(S.readme_problems(), [])

    def test_bundle_with_agent_regular_readme_is_clean(self):
        self._make_plugin("zeta", ["zeta"], agents=True, readme="regular")
        self.assertEqual(S.readme_problems(), [])

    def test_bundle_with_hooks_regular_readme_is_clean(self):
        self._make_plugin("eta", ["eta"], hooks=True, readme="regular")
        self.assertEqual(S.readme_problems(), [])

    def test_standalone_missing_readme_is_red(self):
        self._make_plugin("theta", ["theta"], readme=None)
        problems = S.readme_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugins/theta/README.md", problems[0])
        self.assertIn("missing", problems[0])

    def test_standalone_dangling_readme_symlink_is_red(self):
        self._make_plugin("iota", ["iota"], readme="symlink:../../primitives-core/skills/iota/README.md")
        problems = S.readme_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugins/iota/README.md", problems[0])
        self.assertIn("dangling", problems[0])
        # the generic symlink walk also independently flags the same dangling target
        generic = S.symlink_problems()
        self.assertTrue(any("broken symlink" in p for p in generic))

    def test_standalone_readme_symlink_wrong_skill_is_red(self):
        # kappa's README points at a *different* skill's README (alpha), not its own
        os.makedirs(os.path.join(self.fix, "primitives-core", "skills", "alpha"))
        with open(os.path.join(self.fix, "primitives-core", "skills", "alpha", "README.md"), "w") as fh:
            fh.write("# alpha\n")
        self._make_plugin("kappa", ["kappa"], readme="symlink:../../primitives-core/skills/alpha/README.md")
        problems = S.readme_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugins/kappa/README.md", problems[0])
        self.assertIn("does not match", problems[0])

    def test_standalone_readme_symlink_outside_primitives_core_is_red(self):
        outside_target = os.path.join(self.fix, "OUTSIDE.md")
        with open(outside_target, "w") as fh:
            fh.write("not a skill readme\n")
        self._make_plugin("lambda", ["lambda"], readme="symlink:../../OUTSIDE.md")
        problems = S.readme_problems()
        self.assertEqual(len(problems), 1)
        self.assertIn("plugins/lambda/README.md", problems[0])
        self.assertIn("does not match", problems[0])

    def test_commands_dir_makes_assembly_a_bundle(self):
        """A one-skill assembly with a commands/ entry is a bundle (decision-010: a command
        is a shipped surface beyond the one skill); with no commands it's still standalone."""
        with_cmd = self._make_plugin("nu", ["nu"], commands=True)
        self.assertFalse(S.is_standalone(with_cmd))
        without_cmd = self._make_plugin("xi", ["xi"])
        self.assertTrue(S.is_standalone(without_cmd))


class StandaloneCountReporting(unittest.TestCase):
    """main()'s success line must report the is_standalone() count at runtime, so the
    docstring can never again drift from the gate the way the retired "check 4 has no
    subjects" note did once a standalone assembly was added."""

    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-symlinks-count-")
        self.saved = {k: getattr(S, k) for k in ("REPO", "PLUGINS_DIR", "MARKETPLACE")}
        S.REPO = self.fix
        S.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        S.MARKETPLACE = os.path.join(self.fix, ".claude-plugin", "marketplace.json")
        os.makedirs(os.path.join(self.fix, "primitives-core", "skills"))
        os.makedirs(os.path.join(self.fix, ".claude-plugin"))

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(S, k, v)
        shutil.rmtree(self.fix, ignore_errors=True)

    def _make_plugin(self, plugin_id, skill_ids, bundle_readme=False):
        """Standalone (1 skill) gets a compliant README symlink; a bundle (>1 skill)
        gets a hand-authored regular-file README."""
        pdir = os.path.join(S.PLUGINS_DIR, plugin_id)
        skills_dir = os.path.join(pdir, "skills")
        os.makedirs(os.path.join(pdir, ".claude-plugin"))
        os.makedirs(skills_dir)
        with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump({"name": plugin_id}, fh)
        for sid in skill_ids:
            src = os.path.join(self.fix, "primitives-core", "skills", sid)
            os.makedirs(src)
            with open(os.path.join(src, "SKILL.md"), "w") as fh:
                fh.write(f"---\nname: {sid}\ndescription: x\n---\n")
            os.symlink(os.path.relpath(src, skills_dir), os.path.join(skills_dir, sid))
        readme_path = os.path.join(pdir, "README.md")
        if bundle_readme:
            with open(readme_path, "w") as fh:
                fh.write(f"# {plugin_id}\n")
        else:
            skill_readme = os.path.join(self.fix, "primitives-core", "skills", skill_ids[0], "README.md")
            with open(skill_readme, "w") as fh:
                fh.write(f"# {skill_ids[0]}\n")
            os.symlink(os.path.relpath(skill_readme, pdir), readme_path)
        return pdir

    def test_reported_count_matches_is_standalone(self):
        self._make_plugin("solo-one", ["solo-one"])
        self._make_plugin("solo-two", ["solo-two"])
        self._make_plugin("bundle-one", ["bundle-a", "bundle-b"], bundle_readme=True)
        plugins = sorted(os.listdir(S.PLUGINS_DIR))
        with open(S.MARKETPLACE, "w") as fh:
            json.dump(
                {"plugins": [{"name": p, "source": f"./plugins/{p}"} for p in plugins]},
                fh,
            )
        # independently derived — never hard-code a plugin name or a count here
        expected = sum(1 for p in plugins if S.is_standalone(os.path.join(S.PLUGINS_DIR, p)))
        self.assertGreater(expected, 0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = S.main()
        self.assertEqual(code, 0, buf.getvalue())

        match = re.search(r"(\d+) standalone", buf.getvalue())
        self.assertIsNotNone(match, buf.getvalue())
        self.assertEqual(int(match.group(1)), expected)


if __name__ == "__main__":
    unittest.main()
