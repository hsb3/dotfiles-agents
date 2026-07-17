"""Tests for scripts/check_hook_layout.py -- ratified hook-dir layout (D6 floor check 4).

Proves the check is red-able on each wrong-layout shape (shell handler, legacy hooks-handlers/,
a hook dir missing hook.py, a stray root file) and green on the ratified <name>/hook.py layout.
No hooks ship yet, so the real tree is vacuously green. Stdlib-only; fixtures are tempdirs.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_hook_layout as H  # noqa: E402


def _root(spec):
    """Build a hook root from {relpath: content|None(dir marker)} and return its check problems."""
    d = tempfile.mkdtemp()
    for rel, content in spec.items():
        full = os.path.join(d, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if content is None:
            os.makedirs(full, exist_ok=True)
        else:
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)
    return H.check_root(d, d)


class RedAble(unittest.TestCase):
    def test_shell_handler_flagged(self):
        probs = _root({"context-watermark/hooks-handlers/pw.Stop.warn.sh": "echo hi"})
        self.assertTrue(any(".sh" in p or "shell" in p for p in probs))

    def test_legacy_hooks_handlers_dir_flagged(self):
        probs = _root({"context-watermark/hooks-handlers/hook.py": "print(1)"})
        self.assertTrue(any("hooks-handlers" in p for p in probs))

    def test_hook_dir_missing_hook_py_flagged(self):
        probs = _root({"context-watermark/config.json": "{}"})
        self.assertTrue(any("missing hook.py" in p for p in probs))

    def test_stray_root_file_flagged(self):
        probs = _root({"hook.py": "print(1)"})
        self.assertTrue(any("root" in p for p in probs))


class Green(unittest.TestCase):
    def test_ratified_layout_clean(self):
        probs = _root({
            "context-watermark/hook.py": "print(1)",
            "context-watermark/config.json": "{}",
        })
        self.assertEqual(probs, [])

    def test_gitkeep_only_clean(self):
        self.assertEqual(_root({".gitkeep": ""}), [])


class RealTree(unittest.TestCase):
    def test_shipped_tree_hook_layout_clean(self):
        self.assertEqual(H.main(), 0)


if __name__ == "__main__":
    unittest.main()
