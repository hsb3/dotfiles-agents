"""Tests for the github-project-board skill's board scripts.

Unit level only — the pure helpers the PR-43 review flagged as untested edge cases:
`fv_scalar` (key-presence extraction: "" and 0 are real values), `values_equal`
(idempotency compare incl. the NUMBER 3.0 == "3" case), `resolve_field` (token
matching), and board-export's `field_value` (typename-based normalization). The
network half (gh/GraphQL) is deliberately out of scope here.

The scripts are hyphen-named standalone files, so they load via importlib rather
than a package import. Stdlib-only (unittest), same as the rest of the suite.
"""

import importlib.util
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(
    REPO, "primitives-core", "skills", "github-project-board", "scripts"
)


def load(name: str):
    path = os.path.join(SCRIPTS, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


APPLY = load("board-apply")
EXPORT = load("board-export")


class TestFvScalar(unittest.TestCase):
    """Key-presence extraction — the `or`-chain bug: "" and 0 must survive."""

    def test_empty_string_text_is_preserved(self):
        self.assertEqual(APPLY.fv_scalar({"text": "", "field": {"name": "Notes"}}), "")

    def test_zero_number_is_preserved(self):
        self.assertEqual(APPLY.fv_scalar({"number": 0}), 0)

    def test_none_values_fall_through(self):
        self.assertIsNone(APPLY.fv_scalar({"text": None}))
        self.assertIsNone(APPLY.fv_scalar({}))

    def test_precedence_first_present_key_wins(self):
        self.assertEqual(APPLY.fv_scalar({"name": "P1", "text": "x"}), "P1")

    def test_plain_values(self):
        self.assertEqual(APPLY.fv_scalar({"date": "2026-06-18"}), "2026-06-18")
        self.assertEqual(APPLY.fv_scalar({"title": "Sprint 2"}), "Sprint 2")
        self.assertEqual(APPLY.fv_scalar({"number": 3.0}), 3.0)


class TestValuesEqual(unittest.TestCase):
    """Idempotency compare — the NUMBER str(3.0) != "3" bug."""

    def test_number_float_vs_changeset_int_string(self):
        self.assertTrue(APPLY.values_equal(3.0, "3"))

    def test_number_float_vs_changeset_float_string(self):
        self.assertTrue(APPLY.values_equal(3.5, "3.5"))

    def test_text_case_insensitive(self):
        self.assertTrue(APPLY.values_equal("P1", "p1"))

    def test_none_never_equal(self):
        self.assertFalse(APPLY.values_equal(None, "3"))

    def test_differing_text(self):
        self.assertFalse(APPLY.values_equal("High", "Low"))

    def test_non_numeric_mismatch_does_not_raise(self):
        self.assertFalse(APPLY.values_equal("abc", "3"))

    def test_numeric_inequality(self):
        self.assertFalse(APPLY.values_equal(3.0, "4"))


class TestResolveField(unittest.TestCase):
    FIELDS = {"Status": {}, "Up Next Gate": {}, "Workstream": {}}

    def test_case_insensitive(self):
        self.assertEqual(APPLY.resolve_field("status", self.FIELDS), "Status")

    def test_underscore_and_space_insensitive(self):
        self.assertEqual(
            APPLY.resolve_field("up_next_gate", self.FIELDS), "Up Next Gate"
        )

    def test_no_match_returns_none(self):
        self.assertIsNone(APPLY.resolve_field("priority", self.FIELDS))


class TestExportFieldValue(unittest.TestCase):
    """board-export's typename-based normalization keeps "" and 0 too."""

    def test_each_typename(self):
        cases = [
            ({"__typename": "ProjectV2ItemFieldSingleSelectValue", "name": "P0"}, "P0"),
            ({"__typename": "ProjectV2ItemFieldTextValue", "text": ""}, ""),
            ({"__typename": "ProjectV2ItemFieldNumberValue", "number": 0}, 0),
            (
                {"__typename": "ProjectV2ItemFieldDateValue", "date": "2026-01-01"},
                "2026-01-01",
            ),
            (
                {"__typename": "ProjectV2ItemFieldIterationValue", "title": "It 1"},
                "It 1",
            ),
            ({"__typename": "ProjectV2ItemFieldRepositoryValue"}, None),
        ]
        for node, want in cases:
            self.assertEqual(EXPORT.field_value(node), want, node["__typename"])


if __name__ == "__main__":
    unittest.main()
