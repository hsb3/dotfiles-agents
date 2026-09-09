"""Package role registration derives membership and preserves consumer ownership."""

import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "primitives-core/hooks/_lib"))
import codex_roles as roles


class CodexPackageRoles(unittest.TestCase):
    def package(self, temporary, name):
        package = Path(temporary) / name
        shutil.copytree(ROOT / "plugins" / name, package)
        return package

    def test_standalone_packages_register_only_their_assembled_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name, expected in [
                ("code-desk", ("code-desk-rig-builder",)),
                ("pocketbase", ("pocketbase-pb-builder", "pocketbase-pb-reviewer",
                                "pocketbase-pocketbase-security-auditor")),
            ]:
                package = self.package(temporary, name)
                self.assertEqual(roles.role_names(package), expected)
                consumer = Path(temporary) / (name + "-consumer")
                consumer.mkdir()
                self.assertEqual(len(roles.setup(consumer, package)), len(expected))
                self.assertEqual(roles.setup(consumer, package, check=True), [])
                for native in expected:
                    profile = tomllib.loads((consumer / ".codex/agents" / (native + ".toml")).read_text())
                    self.assertEqual(profile["name"], native)
                    self.assertIn(str(package), profile["developer_instructions"])
                    self.assertNotIn("Codex distribution", profile["developer_instructions"])

    def test_bare_name_that_starts_with_package_name_stays_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = self.package(temporary, "pocketbase")
            self.assertEqual(
                roles.role_instructions("pocketbase-security-auditor", package),
                roles.role_instructions("pocketbase-pocketbase-security-auditor", package))
            with self.assertRaises(ValueError):
                roles.role_instructions("atelier-builder", package)

    def test_missing_manifest_is_not_an_unknown_role(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "manifest missing"):
                roles.role_names(temporary)

    def test_consumer_edit_refuses_package_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = self.package(temporary, "code-desk")
            consumer = Path(temporary) / "consumer"
            consumer.mkdir()
            roles.setup(consumer, package)
            path = consumer / ".codex/agents/code-desk-rig-builder.toml"
            path.write_text(path.read_text() + "# consumer edit\n")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "modified"):
                roles.setup(consumer, package)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
