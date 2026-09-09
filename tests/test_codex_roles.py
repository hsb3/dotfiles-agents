"""Codex roles keep canonical doctrine and never overwrite consumer-owned profiles."""

import shutil
import re
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "primitives-core/hooks/_lib"))
import codex_roles as roles


class CodexRoles(unittest.TestCase):
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

    def test_setup_check_refresh_and_modified_collision_are_ownership_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve() / "consumer"
            project.mkdir()
            source = Path(tmp) / "package"
            shutil.copytree(ROOT / "plugins/atelier", source)
            planned = roles.setup(project, source, check=True)
            self.assertEqual(len(planned), len(roles.ROLES))
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
