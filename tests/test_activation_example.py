"""Guards the shipped activation example
(primitives-core/skills/activation/examples/atelier.local.md) against find/replace
damage: a word fused onto a dotfile path (`.claudethe`) or a doubled word ("the the").
Reuses tests/test_activation.py's loader and helpers rather than a second YAML parser.
"""

import os
import re
import unittest

from tests import test_activation as ta

EXAMPLE_PATH = ta.EXAMPLE_PATH

DOUBLED_WORD = re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE)

# A real `.claude`/`.agents` path continues with `/`, `-` or whitespace, never a letter.
FUSED_PATH_WORD = re.compile(r"\.(claude|agents)[A-Za-z]")


def _read_example():
    with open(EXAMPLE_PATH, encoding="utf-8") as fh:
        return fh.read()


class ProseTests(unittest.TestCase):
    def test_no_doubled_word(self):
        text = _read_example()
        matches = [m.group(0) for m in DOUBLED_WORD.finditer(text)]
        self.assertEqual(matches, [],
                         "doubled word(s) in {0}: {1}".format(EXAMPLE_PATH, matches))

    def test_no_word_fused_onto_a_dotfile_path(self):
        text = _read_example()
        matches = [m.group(0) for m in FUSED_PATH_WORD.finditer(text)]
        self.assertEqual(matches, [],
                         "word fused onto a path in {0}: {1}".format(EXAMPLE_PATH, matches))


class HandoffStampTests(ta._Base):
    """Drives the real activation.py checker against the example's external
    handoff block, uncommented in a temp project copy, and asserts the stamp
    resolves to `.claude/handoff.stamp` rather than to a garbled value."""

    def test_external_handoff_stamp_resolves(self):
        armed = ta._uncomment_mapping_handoff(_read_example())
        self.assertIn("\nhandoff:\n", armed)  # the transform actually fired
        self.assertIn("\n  mode: external\n", armed)
        self.write(armed)

        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "handoff")
        self.assertIn("armed", row, output)
        expected_stamp = os.path.join(self.project, ".claude", "handoff.stamp")
        self.assertIn(expected_stamp, row, output)


if __name__ == "__main__":
    unittest.main()
