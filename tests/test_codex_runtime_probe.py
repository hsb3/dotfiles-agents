"""Tests for harness/codex_runtime_probe.py's `checkout-root` resolution.

Exercises `checkouts_dir()` and `activation_frontmatter()` against a real, uncommitted
git repo. Never invokes Codex; stdlib-only.
"""

import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from worktree_fixture import require_git  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "codex_runtime_probe_under_test", ROOT / "harness/codex_runtime_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CheckoutsDirTests(unittest.TestCase):
    def setUp(self):
        require_git()
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("ATELIER_ACTIVATION_FILE", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def write_activation(self, text):
        (self.repo / ".agents").mkdir(exist_ok=True)
        (self.repo / ".agents/atelier.local.md").write_text(text)

    def test_no_key_defaults_to_dotgit_checkouts(self):
        self.assertEqual(probe.checkouts_dir(self.root),
                          self.repo / ".git/atelier-codex/checkouts")

    def test_checkout_root_key_resolves_relative_to_repo(self):
        self.write_activation("---\ncheckout-root: .worktrees\n---\n")
        self.assertEqual(probe.checkouts_dir(self.root), self.repo / ".worktrees")

    def test_flag_frontmatter_feeds_the_same_resolution(self):
        # Exactly the content --checkout-root would write into the fixture's
        # activation config; proves the flag's write and (b)'s resolution agree.
        self.write_activation(probe.activation_frontmatter(".worktrees"))
        self.assertEqual(probe.checkouts_dir(self.root), self.repo / ".worktrees")


class ActivationFrontmatterRoundTripTests(unittest.TestCase):
    def test_newline_injection_raises(self):
        with self.assertRaises(ValueError):
            probe.activation_frontmatter("wt\nenforce: off")

    def test_trailing_comment_raises(self):
        with self.assertRaises(ValueError):
            probe.activation_frontmatter("wt # c")

    def test_empty_value_raises(self):
        with self.assertRaises(ValueError):
            probe.activation_frontmatter("")

    def test_plain_value_passes(self):
        self.assertIn("checkout-root: .worktrees\n", probe.activation_frontmatter(".worktrees"))


class Stop(Exception):
    """Sentinel raised by a fake `command` to stop before Codex output parsing."""


class NativeProbeUsesCheckoutsDirTests(unittest.TestCase):
    """Call-site coverage for native_probe(production=True): both the checkout
    dir it mkdir's and the --add-dir it passes must come from checkouts_dir()."""

    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / ".agents").mkdir()
        (self.repo / ".agents/atelier.local.md").write_text("---\ncheckout-root: .worktrees\n---\n")

    def test_workers_dir_and_add_dir_use_the_configured_checkout_root(self):
        calls = []

        def fake_command(name, argv, timeout=240):
            calls.append((name, argv))
            raise Stop

        with self.assertRaises(Stop):
            probe.native_probe(self.root, fake_command, "gpt-5.6-luna", production=True)
        expected = self.repo / ".worktrees"
        self.assertTrue(expected.is_dir())
        name, argv = calls[0]
        self.assertEqual(name, "native-isolation")
        self.assertIn(str(expected), argv)


class ProductionWorkflowUsesCheckoutsDirTests(unittest.TestCase):
    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / ".agents").mkdir()
        (self.repo / ".agents/atelier.local.md").write_text("---\ncheckout-root: .worktrees\n---\n")

    def test_add_dir_uses_the_configured_checkout_root(self):
        calls = []

        def fake_command(name, argv, timeout=240):
            calls.append((name, argv))
            raise Stop

        with self.assertRaises(Stop):
            probe.production_workflow(self.root, fake_command, "gpt-5.6-luna")
        expected = self.repo / ".worktrees"
        name, argv = calls[0]
        self.assertEqual(name, "production-workflow")
        self.assertIn(str(expected), argv)


class ActivateFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve() / "repo"
        self.repo.mkdir()

    def test_checkout_root_reaches_the_written_fixture(self):
        calls = []

        def fake_command(name, argv, timeout=240):
            calls.append(name)
            return ""

        probe.activate_fixture(fake_command, Path("/unused/package"), self.repo, ".worktrees")
        text = (self.repo / ".claude/atelier.local.md").read_text()
        self.assertIn("checkout-root: .worktrees\n", text)
        self.assertEqual(calls, ["activation-setup", "activation-refresh"])

    def test_run_forwards_checkout_root(self):
        # run() needs an authenticated Codex; pin its call to activate_fixture structurally.
        tree = ast.parse((ROOT / "harness/codex_runtime_probe.py").read_text())
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
        calls = [node for node in ast.walk(run) if isinstance(node, ast.Call)
                 and getattr(node.func, "id", None) == "activate_fixture"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(ast.unparse(calls[0].args[3]), "checkout_root")


if __name__ == "__main__":
    unittest.main()
