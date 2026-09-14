"""Adapter registry / dispatch — the vendor seam Wave 2 extends."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.adapters import (  # noqa: E402
    ClaudeAdapter,
    UnknownHarness,
    get_adapter,
    list_adapters,
)


class TestRegistry(unittest.TestCase):
    def test_claude_is_registered(self):
        self.assertIn("claude", list_adapters())

    def test_get_adapter_returns_instance(self):
        a = get_adapter("claude")
        self.assertIsInstance(a, ClaudeAdapter)
        self.assertEqual(a.name, "claude")

    def test_allow_bash_flows_through_constructor(self):
        self.assertTrue(get_adapter("claude", allow_bash=True).allow_bash)
        self.assertFalse(get_adapter("claude").allow_bash)

    def test_opencode_is_registered(self):
        self.assertIn("opencode", list_adapters())

    def test_unknown_harness_raises_listing_valid_names(self):
        with self.assertRaises(UnknownHarness) as ctx:
            get_adapter("codex")  # a non-goal adapter; genuinely unregistered
        # The message lists the valid names, which now include opencode.
        self.assertIn("claude", str(ctx.exception))
        self.assertIn("opencode", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
