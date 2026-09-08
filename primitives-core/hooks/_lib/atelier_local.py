"""atelier_local — read one top-level key out of `.claude/atelier.local.md`.

The activation file's frontmatter, parsed narrowly: one named key, either its
scalar value or one level of indented sub-keys beneath it. Everything else is
ignored, and anything unreadable answers None, so a malformed file behaves
exactly as an absent one (`docs/override-convention.md`, fail-open).

`context-watermark` is the only reader today. The five older hooks each carry
their own copy of this parser (ADR 0017: a hook directory is symlinked on its
own, so one of them importing another's module would break the moment it is
installed alone) — importing from `_lib/` is safe because `_lib/` is a member
of every hooks assembly, but converting those five is a separate change.

Stdlib-only, Python 3.9 compatible.
"""

import os

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
ACTIVATION_MAX_BYTES = 256 * 1024


def activation_path(project_dir):
    """The activation file to read. `ATELIER_ACTIVATION_FILE` wins outright."""
    return os.environ.get("ATELIER_ACTIVATION_FILE") or os.path.join(
        project_dir, ACTIVATION_RELPATH)


def unquote(value):
    """Strip surrounding quotes, else a trailing ` #` comment."""
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        close = value.find(quote, 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at].rstrip()
    return value


def _frontmatter(text):
    """(lines, start, end) of the frontmatter block, or None."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip("﻿").strip()
        if not stripped:
            continue
        if stripped == "---":
            start = index + 1
        break  # the first non-blank line must be the opening fence
    if start is None:
        return None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return lines, start, index
    return None


def parse_key(text, key):
    """The named key's value: a str (scalar form), a dict (mapping form), or None.

    A key written twice takes the last value, matching every other atelier
    parser. A sequence under the key is unreadable here and yields None.
    """
    block = _frontmatter(text)
    if block is None:
        return None
    lines, index, end = block
    key = key.lower()
    value = None
    while index < end:
        line = lines[index]
        index += 1
        if not line.strip() or line[:1].isspace() or line.strip().startswith("#"):
            continue
        item = line.strip()
        colon = item.find(":")
        if colon == -1 or item[:colon].strip().lower() != key:
            continue
        rest = item[colon + 1:].strip()
        # A comment where the value would be reads as no value at all, so
        # `watermark:  # note` opens the mapping form.
        scalar = "" if rest.startswith("#") else unquote(rest)
        if scalar:
            value = scalar
            continue
        children = {}
        while index < end:
            child = lines[index]
            if not child.strip():
                index += 1
                continue
            if not child[:1].isspace():
                break  # back at the top level: the mapping is over
            index += 1
            sub = child.strip()
            if sub.startswith("#"):
                continue
            if sub.startswith("-"):
                children = None  # a sequence where a mapping belongs
                break
            sub_colon = sub.find(":")
            if sub_colon == -1:
                continue
            children[sub[:sub_colon].strip().lower()] = unquote(sub[sub_colon + 1:])
        value = children or None
    return value


def read_key(project_dir, key):
    """`parse_key` against the project's activation file. Any trouble -> None."""
    try:
        path = activation_path(project_dir)
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
        return parse_key(text, key)
    except Exception:
        return None
