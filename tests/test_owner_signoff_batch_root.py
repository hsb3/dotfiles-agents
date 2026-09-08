"""Tests for owner-signoff's batch-root override
(`resolve_batch_root` in primitives-core/skills/owner-signoff/scripts/build_signoff.py).

The batch root is the one thing a session must not guess: a wrong root writes the
sign-off where nobody looks for it. It defaults to `_meta/signoff` and is overridden by
a `signoff:` key in `.claude/owner-signoff.local.md` -- the project-local frontmatter-key
convention documented in docs/override-convention.md.

Fail-open is the invariant under test as much as the happy path: a key that is absent,
blank, or points outside the project root leaves the default in force, because an
override must never be a way to turn the skill off or to write outside the project.

Stdlib-only. Every fixture is a throwaway project root in a tempdir -- never under
primitives-core/, where the roster guard flags orphans. Assertions are on resolved
paths, not on stdout wording; the one subprocess case exists to prove the CLI mode and
the function agree, and parses its output as a path for that reason.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(
    REPO, "primitives-core", "skills", "owner-signoff", "scripts", "build_signoff.py"
)
sys.path.insert(0, os.path.dirname(SCRIPT))

import build_signoff as bs  # noqa: E402


class BatchRoot(unittest.TestCase):
    def project(self, local: str | None) -> pathlib.Path:
        """A throwaway project root, with `.claude/owner-signoff.local.md` iff *local*."""
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp)).resolve()
        claude = root / ".claude"
        claude.mkdir()
        if local is not None:
            (claude / "owner-signoff.local.md").write_text(local, encoding="utf-8")
        return root

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = holder.name

    def test_no_local_file_uses_shipped_default(self):
        root = self.project(None)
        self.assertEqual(bs.resolve_batch_root(root), root / "_meta" / "signoff")

    def test_key_overrides_the_default(self):
        root = self.project("---\nsignoff: docs/signoff\n---\n")
        self.assertEqual(bs.resolve_batch_root(root), root / "docs" / "signoff")

    def test_value_outside_the_project_root_is_ignored(self):
        root = self.project("---\nsignoff: ../elsewhere\n---\n")
        self.assertEqual(bs.resolve_batch_root(root), root / "_meta" / "signoff")

    def test_quoted_value_with_trailing_comment(self):
        root = self.project('---\nname: whatever\nsignoff: "team/decisions"   # comment\n---\n')
        self.assertEqual(bs.resolve_batch_root(root), root / "team" / "decisions")

    def test_local_file_without_the_key_uses_the_default(self):
        root = self.project("---\ntheme: slate\n---\n\nprose below\n")
        self.assertEqual(bs.resolve_batch_root(root), root / "_meta" / "signoff")

    def test_blank_value_uses_the_default(self):
        root = self.project("---\nsignoff:\n---\n")
        self.assertEqual(bs.resolve_batch_root(root), root / "_meta" / "signoff")

    def test_key_below_the_frontmatter_block_is_not_read(self):
        """Prose that happens to say `signoff: …` is documentation, not configuration."""
        root = self.project("---\ntheme: slate\n---\n\nsignoff: docs/signoff\n")
        self.assertEqual(bs.resolve_batch_root(root), root / "_meta" / "signoff")

    def test_cli_mode_agrees_with_the_function(self):
        root = self.project("---\nsignoff: docs/signoff\n---\n")
        done = subprocess.run(
            [sys.executable, SCRIPT, "--batch-root", str(root)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(pathlib.Path(done.stdout.strip()), bs.resolve_batch_root(root))


if __name__ == "__main__":
    unittest.main()
