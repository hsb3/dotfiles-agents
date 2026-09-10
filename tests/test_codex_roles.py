"""Codex roles keep canonical doctrine and never overwrite consumer-owned profiles."""

import shutil
import re
import hashlib
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "primitives-core/hooks/_lib"))
import codex_roles as roles


class CodexRoles(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.env = patch.dict("os.environ", {"CODEX_HOME": self.home.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_every_role_renders_its_canonical_contract_and_valid_toml(self):
        for role in roles.ROLES:
            with self.subTest(role=role):
                profile = tomllib.loads(roles.render(role))
                self.assertEqual(profile["name"], "atelier-" + role)
                self.assertTrue(profile["model"].startswith("gpt-"))
                body = profile["developer_instructions"]
                self.assertIn(roles.role_instructions("atelier-" + role), body)
                self.assertIn("Codex distribution", body)
                self.assertNotIn("~/.claude/projects", body)
                self.assertNotIn("They do not carry SendMessage", body)
                self.assertNotIn("model: opus", body)
                self.assertIn("role", body)

    def test_only_atelier_leaf_profiles_disable_apps_and_skill_instructions(self):
        leaves = ("scout", "builder", "reviewer", "code-reviewer")
        sentence = "Caller supplies needed skill and reference absolute paths; missing capability goes back to manager, don't guess."
        for role in leaves:
            with self.subTest(role=role):
                profile = tomllib.loads(roles.render(role))
                self.assertEqual(profile["features"], {"apps": False})
                self.assertEqual(profile["skills"], {"include_instructions": False})
                self.assertIn(sentence, profile["developer_instructions"])

        manager = tomllib.loads(roles.render("manager"))
        self.assertNotIn("features", manager)
        self.assertNotIn("skills", manager)
        self.assertNotIn(sentence, manager["developer_instructions"])
        for package_name in ("code-desk", "pocketbase"):
            package = ROOT / "plugins" / package_name
            for role in roles.roles(package):
                with self.subTest(package=package_name, role=role):
                    profile = tomllib.loads(roles.render(role, package))
                    self.assertNotIn("features", profile)
                    self.assertNotIn("skills", profile)

    def test_setup_check_refresh_and_modified_collision_are_ownership_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve() / "consumer"
            project.mkdir()
            source = Path(tmp) / "package"
            shutil.copytree(ROOT / "plugins/atelier", source)
            planned = roles.setup(project, source, check=True)
            self.assertEqual(len(planned), len(roles.ROLES))
            self.assertEqual(planned, sorted(planned))
            self.assertFalse((project / ".codex").exists())
            self.assertEqual(roles.setup(project, source), planned)
            self.assertEqual(roles.setup(project, source, check=True), [])
            profile = project / ".codex/agents/atelier-builder.toml"
            original = profile.read_text()
            instructions = tomllib.loads(original)["developer_instructions"]
            self.assertIn(str(source.resolve()), instructions)
            agent = source / "agents/builder.md"
            agent.write_text(agent.read_text() + "\nA new canonical instruction.\n")
            self.assertEqual(roles.setup(project, source, check=True), [profile])
            roles.setup(project, source)
            self.assertIn("A new canonical instruction", profile.read_text())
            self.assertNotEqual(profile.read_text(), original)
            profile.write_text(profile.read_text() + "# consumer edit\n")
            before = {p: p.read_bytes() for p in profile.parent.iterdir()}
            with self.assertRaisesRegex(ValueError, "modified"):
                roles.setup(project, source)
            self.assertEqual(before, {p: p.read_bytes() for p in profile.parent.iterdir()})

    def test_unmanaged_or_symlink_collision_never_partially_installs(self):
        for collision in ("file", "symlink", "directory"):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp)
                agents = project / ".codex/agents"
                agents.mkdir(parents=True)
                target = agents / "atelier-scout.toml"
                if collision == "file":
                    target.write_text('name = "mine"\n')
                elif collision == "symlink":
                    target.symlink_to(project / "absent")
                else:
                    target.mkdir()
                with self.assertRaises(ValueError):
                    roles.setup(project)
                self.assertEqual(list(agents.iterdir()), [target])

    def test_symlinked_config_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve() / "consumer"
            project.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (project / ".codex").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                roles.setup(project)
            self.assertEqual(list(outside.iterdir()), [])

    def test_user_profile_with_same_role_under_another_filename_is_a_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            directory = project / ".codex/agents"
            directory.mkdir(parents=True)
            user_profile = directory / "my-builder.toml"
            user_profile.write_text('name = "atelier-builder"\n')
            with self.assertRaisesRegex(ValueError, "role name"):
                roles.setup(project)
            self.assertEqual(list(directory.iterdir()), [user_profile])

    def test_current_global_profiles_avoid_local_copies_and_stale_ones_require_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "consumer"
            home = Path(tmp) / "codex-home"
            project.mkdir()
            home.mkdir()
            with patch.dict("os.environ", {"CODEX_HOME": str(home)}):
                global_paths = roles.setup(home, global_profiles=True)
                self.assertEqual(roles.setup(project, check=True), [])
                self.assertFalse((project / ".codex").exists())
                stale = global_paths[0]
                _, _, body = stale.read_text().partition("\n")
                body = body.replace("Atelier package:", "Old package:")
                stale.write_text(roles._managed() + hashlib.sha256(body.encode()).hexdigest() + "\n" + body)
                with self.assertRaisesRegex(ValueError, "stale global"):
                    roles.setup(project)
                self.assertEqual(roles.setup(project, check=True), [stale])
                self.assertFalse((project / ".codex").exists())
                self.assertEqual(roles.setup(project, refresh_global=True), [stale])
                self.assertEqual(roles.setup(project, check=True), [])

    def test_local_profiles_take_precedence_over_a_stale_global_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "consumer"
            home = Path(tmp) / "codex-home"
            project.mkdir()
            home.mkdir()
            with patch.dict("os.environ", {"CODEX_HOME": str(home)}):
                roles.setup(project)
                global_paths = roles.setup(home, global_profiles=True)
                global_paths[0].write_text(global_paths[0].read_text() + "# stale\n")
                self.assertEqual(roles.setup(project, check=True), [])
                self.assertEqual(roles.setup(project), [])

    def test_local_and_global_profiles_resolve_each_role_without_redundant_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            project, home = Path(tmp) / "consumer", Path(tmp) / "codex-home"
            project.mkdir()
            home.mkdir()
            with patch.dict("os.environ", {"CODEX_HOME": str(home)}):
                roles.setup(home, global_profiles=True)
                local = project / ".codex/agents"
                local.mkdir(parents=True)
                (local / "atelier-builder.toml").write_text(roles.render("builder"))
                self.assertEqual(roles.setup(project), [])
                self.assertEqual(sorted(path.name for path in local.iterdir()), ["atelier-builder.toml"])

    def test_partial_global_profiles_are_validated_before_local_bootstrap(self):
        for name, content in [
                ("custom.toml", "not toml"),
                ("custom.toml", "name = []\n"),
                ("custom.toml", 'name = "atelier-builder"\n'),
                ("atelier-builder.toml", "# atelier managed sha256=wrong\n")]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                project, home = Path(tmp) / "consumer", Path(tmp) / "codex-home"
                project.mkdir()
                home.mkdir()
                with patch.dict("os.environ", {"CODEX_HOME": str(home)}):
                    global_paths = roles.setup(home, global_profiles=True)
                    (home / "agents/atelier-scout.toml").unlink()
                    (home / "agents" / name).write_text(content)
                    with self.assertRaises(ValueError):
                        roles.setup(project)
                    self.assertFalse((project / ".codex").exists())

    def test_unknown_role_is_rejected(self):
        for role in ("../../builder", "atelier-unknown", "", None, 42):
            with self.subTest(role=role), self.assertRaises(ValueError):
                roles.role_instructions(role)

    def test_workflow_entrypoints_resolve_the_bundled_codex_procedures(self):
        package = ROOT / "plugins/atelier"
        for name in ("delegation", "waves", "rubric-panel", "deletion-pass",
                     "layer-cycle", "comment-hygiene"):
            with self.subTest(skill=name):
                skill = package / "skills" / name / "SKILL.md"
                link = re.search(r"\[Codex distribution\]\(([^)#]+)#codex-distribution\)",
                                 skill.read_text())
                self.assertIsNotNone(link)
                reference = (skill.parent / link[1]).resolve()
                self.assertIn("## Codex distribution\n", reference.read_text())


if __name__ == "__main__":
    unittest.main()
