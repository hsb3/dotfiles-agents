"""Diagram learnings belong to the consumer project, not a replaceable plugin cache."""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "diagram_memory_location", ROOT / "primitives-core/skills/diagrams/scripts/memory_manager.py")
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)


class ProjectMemory(unittest.TestCase):
    def test_detect_override_and_reject_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            default = root / ".claude/diagrams-memory.md"
            self.assertEqual(memory.resolve_memory_file(root), default)
            directory = root / ".claude/memory"
            directory.mkdir(parents=True)
            self.assertEqual(memory.resolve_memory_file(root), directory / "diagrams.md")
            config = root / ".claude/diagrams.local.md"
            config.write_text('---\nmemory-path: "notes/diagram learnings.md"\n---\n')
            self.assertEqual(memory.resolve_memory_file(root), root / "notes/diagram learnings.md")
            for bad in ("../outside.md", "", "[]", '"unterminated', "'unterminated", '"ok.md" trailing'):
                config.write_text(f"---\nmemory-path: {bad}\n---\n")
                self.assertEqual(memory.resolve_memory_file(root), directory / "diagrams.md")

    def test_first_learning_creates_parent_and_never_mutates_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "new/memory.md"
            seed = ROOT / "primitives-core/skills/diagrams/memory/MEMORY.md"
            before = seed.read_bytes()
            self.addCleanup(setattr, memory, "MEMORY_FILE", memory.MEMORY_FILE)
            memory.MEMORY_FILE = target
            memory.add_entry("Layout Issues", "Spacing", "Overlap", "Increase nodesep")
            self.assertIn("Increase nodesep", target.read_text())
            self.assertEqual(seed.read_bytes(), before)

    def test_learnings_survive_replacement_of_an_installed_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer = root / "consumer"
            consumer.mkdir()
            source = ROOT / "primitives-core/skills/diagrams"
            installed = root / "cache-v1"
            shutil.copytree(source, installed)
            subprocess.run([sys.executable, str(installed / "scripts/memory_manager.py"),
                            "add", "-s", "Layout Issues", "-t", "Portable learning",
                            "-p", "Overlap", "-o", "Use nodesep"], cwd=consumer,
                           check=True, capture_output=True)
            self.assertEqual((installed / "memory/MEMORY.md").read_bytes(),
                             (source / "memory/MEMORY.md").read_bytes())
            shutil.rmtree(installed)
            refreshed = root / "cache-v2"
            shutil.copytree(source, refreshed)
            result = subprocess.run([sys.executable, str(refreshed / "scripts/memory_manager.py"),
                                     "view"], cwd=consumer, check=True, capture_output=True, text=True)
            self.assertIn("Portable learning", result.stdout)


if __name__ == "__main__":
    unittest.main()
