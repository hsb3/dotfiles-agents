"""Tests for harness/codex_runtime_probe.py's `checkout-root` resolution.

Exercises `checkouts_dir()` and `activation_frontmatter()` against a real, uncommitted
git repo. Never invokes Codex; stdlib-only.
"""

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


if __name__ == "__main__":
    unittest.main()
