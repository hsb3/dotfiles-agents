"""Pure bookmark-management logic for Local Bookmark Vault.

No I/O, no framework — kept separate from server.py so it is trivially
unit-testable with stdlib `unittest` (see tests/test_lib.py).
"""

from __future__ import annotations


def validate_bookmark(data: dict) -> str | None:
    """Return an error message if `data` is not a valid bookmark, else None."""
    if not isinstance(data, dict):
        return "bookmark must be an object"
    url = data.get("url", "")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return "url must be a string starting with http:// or https://"
    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        return "title must be a non-empty string"
    tag = data.get("tag", "")
    if tag and not isinstance(tag, str):
        return "tag must be a string"
    return None


def next_id(bookmarks: list[dict]) -> int:
    """Return the next free integer id (1-based, gap-tolerant)."""
    if not bookmarks:
        return 1
    return max(b["id"] for b in bookmarks) + 1


def filter_by_tag(bookmarks: list[dict], tag: str | None) -> list[dict]:
    """Return bookmarks matching `tag`; return all bookmarks if `tag` is falsy."""
    if not tag:
        return list(bookmarks)
    return [b for b in bookmarks if b.get("tag") == tag]


def remove_by_id(bookmarks: list[dict], bookmark_id: int) -> tuple[list[dict], bool]:
    """Return (remaining_bookmarks, removed) with the given id removed."""
    remaining = [b for b in bookmarks if b["id"] != bookmark_id]
    return remaining, len(remaining) != len(bookmarks)
