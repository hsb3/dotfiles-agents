"""Keep shared repo tooling single-sourced and wired into both native harnesses."""

import json
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AgentConfigParityTests(unittest.TestCase):
    def test_native_hook_links_share_one_source(self):
        for name in ("board-health", "no-main-checkout"):
            shared = ROOT / ".agents" / "hooks" / name
            for native in (".claude", ".codex"):
                link = ROOT / native / "hooks" / name
                self.assertTrue(link.is_symlink(), link)
                self.assertTrue(os.path.samefile(link, shared), link)

    def test_claude_skill_links_share_agent_sources(self):
        for name in ("author-primitive", "publish-to-main"):
            link = ROOT / ".claude" / "skills" / name
            shared = ROOT / ".agents" / "skills" / name
            self.assertTrue(link.is_symlink(), link)
            self.assertTrue(os.path.samefile(link, shared), link)

    def test_common_hooks_are_wired_in_both_harnesses(self):
        claude = json.loads((ROOT / ".claude" / "settings.json").read_text())
        codex = json.loads((ROOT / ".codex" / "hooks.json").read_text())

        def commands(config, event):
            return "\n".join(
                hook["command"]
                for group in config["hooks"][event]
                for hook in group["hooks"]
            )

        for name, event in (("board-health", "SessionStart"),
                            ("no-main-checkout", "PreToolUse")):
            self.assertIn(f"/hooks/{name}/hook.py", commands(claude, event))
            self.assertIn(f"/hooks/{name}/hook.py", commands(codex, event))
        self.assertIn("kata attention-hook end", commands(claude, "SessionEnd"))
        self.assertIn("kata attention-hook end", commands(codex, "SessionEnd"))


if __name__ == "__main__":
    unittest.main()
