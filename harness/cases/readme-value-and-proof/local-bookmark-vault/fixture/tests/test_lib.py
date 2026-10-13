"""Unit tests for lib.py — run with `make test` or
`python3 -m unittest discover -s tests`.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import filter_by_tag, next_id, remove_by_id, validate_bookmark  # noqa: E402


class ValidateBookmarkTests(unittest.TestCase):
    def test_valid_bookmark_passes(self):
        self.assertIsNone(
            validate_bookmark({"url": "https://example.com", "title": "Example"})
        )

    def test_rejects_missing_scheme(self):
        self.assertIsNotNone(
            validate_bookmark({"url": "example.com", "title": "Example"})
        )

    def test_rejects_empty_title(self):
        self.assertIsNotNone(
            validate_bookmark({"url": "https://example.com", "title": "  "})
        )


class NextIdTests(unittest.TestCase):
    def test_empty_list_starts_at_one(self):
        self.assertEqual(next_id([]), 1)

    def test_increments_past_max(self):
        self.assertEqual(next_id([{"id": 1}, {"id": 5}]), 6)


class FilterByTagTests(unittest.TestCase):
    def test_no_tag_returns_all(self):
        bookmarks = [{"id": 1, "tag": "docs"}, {"id": 2, "tag": "tools"}]
        self.assertEqual(filter_by_tag(bookmarks, None), bookmarks)

    def test_filters_matching_tag(self):
        bookmarks = [{"id": 1, "tag": "docs"}, {"id": 2, "tag": "tools"}]
        self.assertEqual(
            filter_by_tag(bookmarks, "tools"), [{"id": 2, "tag": "tools"}]
        )


class RemoveByIdTests(unittest.TestCase):
    def test_removes_matching_id(self):
        bookmarks = [{"id": 1}, {"id": 2}]
        remaining, removed = remove_by_id(bookmarks, 1)
        self.assertTrue(removed)
        self.assertEqual(remaining, [{"id": 2}])

    def test_missing_id_is_noop(self):
        bookmarks = [{"id": 1}]
        remaining, removed = remove_by_id(bookmarks, 99)
        self.assertFalse(removed)
        self.assertEqual(remaining, bookmarks)


if __name__ == "__main__":
    unittest.main()
