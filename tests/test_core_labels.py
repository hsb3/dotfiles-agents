"""The core label vocabulary shipped with board-triage, and its one cross-gate invariant.

`core-labels.txt` is what `board_health.py --vocabulary` reads, so its contents decide
whether the fossil check runs at all. Two things can rot silently: the file drifting away
from the closed GitHub vocabulary `scripts/check_labels.py` enforces (a card and its mirror
would stop reading alike), and an `area:` name creeping in — the area family is
project-defined, so a fixed `area:` name here would be a fossil on every board that spells
its areas differently, and the fossil check would be permanently red for a reason no edit
to open work could clear.

Parsed with board_health's own `load_vocabulary()` rather than a second parser: a test that
reads the file its own way pins the file, not the behaviour that consumes it.

Stdlib-only, no fixtures needed — the subject is a tracked file.
"""

import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "board-triage")
CORE_LABELS = os.path.join(SKILL, "scripts", "core-labels.txt")

# Both loaded by path so this file's module names cannot collide with the other suites'
# loads of the same two scripts.
_bh_spec = importlib.util.spec_from_file_location(
    "board_health_for_core_labels", os.path.join(SKILL, "scripts", "board_health.py")
)
bh = importlib.util.module_from_spec(_bh_spec)
_bh_spec.loader.exec_module(bh)

_cl_spec = importlib.util.spec_from_file_location(
    "check_labels_for_core_labels", os.path.join(ROOT, "scripts", "check_labels.py")
)
cl = importlib.util.module_from_spec(_cl_spec)
_cl_spec.loader.exec_module(cl)


def declared():
    return bh.load_vocabulary(CORE_LABELS)


class GithubVocabularyIsASubset(unittest.TestCase):
    """The closed GitHub set is a subset of the core, so a card and its mirror read alike."""

    def test_every_github_label_is_a_core_label(self):
        missing = sorted(set(cl.VOCABULARY) - set(declared()))
        self.assertEqual(missing, [], f"core-labels.txt is missing {missing}")


class AreaIsProjectDefined(unittest.TestCase):
    """`area:<x>` is a family with no fixed name — declaring one makes a permanent fossil."""

    def test_no_area_name_is_declared(self):
        areas = sorted(n for n in declared() if n.lower().startswith("area:"))
        self.assertEqual(areas, [], f"area names are project-defined, found {areas}")


class DocsIsTheOneRecognisedAreaName(unittest.TestCase):
    """(owner ruling 2026-09-08) `area:docs` is core, and recorded as prose on purpose.

    The ruling makes `area:docs` the target of `doc`/`docs`/`documentation`, so a board may
    use it without adding it to its own area list. It still cannot be a CHECKED line: a
    declared name no open item carries is a vocabulary fossil, so every board with no
    documentation work would report a finding it can never clear. The comment carries the
    recognition; the checked lines stay area-free.
    """

    def test_the_file_names_area_docs_in_its_comments(self):
        text = open(CORE_LABELS, encoding="utf-8").read()
        commented = [
            line for line in text.splitlines() if line.lstrip().startswith("#")
        ]
        self.assertTrue(
            any("area:docs" in line for line in commented),
            "core-labels.txt must record that area:docs is the one recognised area name",
        )

    def test_area_docs_is_not_a_checked_line(self):
        self.assertNotIn("area:docs", declared())


class NamesAreWellFormed(unittest.TestCase):
    """A label is matched case-insensitively but compared as a string — no surprises in it."""

    def test_every_name_is_lowercase(self):
        bad = sorted(n for n in declared() if n != n.lower())
        self.assertEqual(bad, [], f"not lowercase: {bad}")

    def test_no_name_carries_whitespace(self):
        bad = sorted(n for n in declared() if any(c.isspace() for c in n))
        self.assertEqual(bad, [], f"contains whitespace: {bad}")


if __name__ == "__main__":
    unittest.main()
