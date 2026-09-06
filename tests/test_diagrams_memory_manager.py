"""diagrams' memory_manager: view/search/add/list against a tempdir memory file.

All functions print rather than return, and `add_entry` mutates a module-level
`MEMORY_FILE` path in place. Every test patches that constant to a tempdir file so a
run of this suite never touches the skill's real `memory/MEMORY.md`.
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "primitives-core", "skills", "diagrams", "scripts")

sys.path.insert(0, SCRIPTS)

import memory_manager as mm  # noqa: E402

FIXTURE = """# Diagrams Memory

## Import Errors

### 2024-01-01 - Missing import
**Problem**: foo import fails
**Solution**: bar fixes it

## Layout Issues

### 2024-01-02 - Broken layout
**Problem**: baz overlaps
**Solution**: qux spaces it out
"""


def run(fn, *args, **kwargs):
    """Call fn, capturing what it printed."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


class MemoryManagerTest(unittest.TestCase):
    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.path = mm.Path(tmpdir.name) / "MEMORY.md"
        self.path.write_text(FIXTURE)
        patcher = patch.object(mm, "MEMORY_FILE", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)


class ViewMemory(MemoryManagerTest):
    def test_view_whole_file(self):
        out = run(mm.view_memory)
        self.assertIn("Import Errors", out)
        self.assertIn("Layout Issues", out)

    def test_view_one_section(self):
        out = run(mm.view_memory, "Import Errors")
        self.assertIn("Missing import", out)
        self.assertNotIn("Broken layout", out)

    def test_view_unknown_section(self):
        out = run(mm.view_memory, "Nonexistent Section")
        self.assertIn("not found", out)

    def test_view_empty_file(self):
        self.path.write_text("")
        out = run(mm.view_memory)
        self.assertEqual("Memory file is empty.\n", out)


class SearchMemory(MemoryManagerTest):
    def test_search_hit_is_case_insensitive(self):
        out = run(mm.search_memory, "MISSING IMPORT")
        self.assertIn("Found 1 matching", out)
        self.assertIn("Missing import", out)

    def test_search_miss(self):
        out = run(mm.search_memory, "nothing like this exists")
        self.assertIn("No entries found", out)


class AddEntry(MemoryManagerTest):
    def test_add_entry_lands_under_its_section_only(self):
        run(mm.add_entry, "Import Errors", "New title", "the problem", "the fix", None)
        content = self.path.read_text()

        today = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(f"### {today} - New title", content)
        self.assertIn("**Problem**: the problem", content)
        self.assertIn("**Solution**: the fix", content)

        # new entry must sit inside "Import Errors", before "Layout Issues" starts
        import_pos = content.index("## Import Errors")
        layout_pos = content.index("## Layout Issues")
        new_pos = content.index("New title")
        self.assertTrue(import_pos < new_pos < layout_pos)

        # the untouched section keeps its original entry verbatim
        self.assertIn("Broken layout", content)

    def test_add_entry_with_example_includes_code_block(self):
        run(mm.add_entry, "Layout Issues", "T", "P", "S", "print('hi')")
        content = self.path.read_text()
        self.assertIn("```python\nprint('hi')\n```", content)

    def test_add_entry_creates_missing_section_at_end(self):
        run(mm.add_entry, "General Best Practices", "T", "P", "S", None)
        content = self.path.read_text()
        self.assertIn("## General Best Practices", content)
        self.assertGreater(
            content.index("## General Best Practices"), content.index("## Layout Issues")
        )

    def test_add_entry_rejects_unknown_section_without_writing(self):
        before = self.path.read_text()
        out = run(mm.add_entry, "Not A Real Section", "T", "P", "S", None)
        self.assertIn("Invalid section", out)
        self.assertEqual(before, self.path.read_text())


class ListSections(MemoryManagerTest):
    def test_lists_every_configured_section(self):
        out = run(mm.list_sections)
        for section in mm.SECTIONS:
            self.assertIn(section, out)


class Main(MemoryManagerTest):
    def test_view_command_routes_to_view_memory(self):
        with patch.object(sys, "argv", ["memory_manager.py", "view", "--section", "Import Errors"]):
            with patch.object(mm, "view_memory") as view:
                mm.main()
        view.assert_called_once_with("Import Errors")

    def test_search_command_routes_to_search_memory(self):
        with patch.object(sys, "argv", ["memory_manager.py", "search", "foo"]):
            with patch.object(mm, "search_memory") as search:
                mm.main()
        search.assert_called_once_with("foo")

    def test_add_command_routes_to_add_entry(self):
        argv = ["memory_manager.py", "add", "-s", "Import Errors", "-t", "T",
                "-p", "P", "-o", "S"]
        with patch.object(sys, "argv", argv):
            with patch.object(mm, "add_entry") as add:
                mm.main()
        add.assert_called_once_with("Import Errors", "T", "P", "S", None)

    def test_sections_command_routes_to_list_sections(self):
        with patch.object(sys, "argv", ["memory_manager.py", "sections"]):
            with patch.object(mm, "list_sections") as sections:
                mm.main()
        sections.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
