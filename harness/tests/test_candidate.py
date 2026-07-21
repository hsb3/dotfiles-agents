"""detect_kind — candidate classification (ported from workbench TestDetectKind)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.candidate import detect_kind  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
