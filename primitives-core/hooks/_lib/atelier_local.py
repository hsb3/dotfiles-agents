"""atelier_local — read one top-level key out of `.claude/atelier.local.md`.

The activation file's frontmatter, parsed narrowly: one named key as a scalar, a
mapping of sub-keys, or a sequence. Everything else is ignored, and anything
unreadable answers None, so a malformed file behaves exactly as an absent one
(`docs/override-convention.md`, fail-open).

Every hook that reads the activation file parses it here, and nothing else does
(ADR 0017: `_lib/` is a member of every hooks assembly, so importing it is safe
where importing another hook's module is not). Each hook keeps its OWN sourcing
— which bytes to parse, its size cap, its fail-open default — because those
rules differ per hook and are load-bearing; only the parsing is shared.

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


def _inline_list(raw):
    """`["a", "b"]` / `[a, b]` -> ["a", "b"]. Commas inside quotes are respected."""
    items = []
    buf = []
    quote = None
    for ch in raw.strip()[1:-1]:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch == ",":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return [item for item in items if item]


def _block(lines, index, end):
    """The lines under a bare `key:` -> (next index, mapping or None, sequence or None).

    A block is a sequence the moment it holds one `- ` item, a mapping when it holds
    only `sub: value` lines, and neither when it is empty. Only an unindented line
    carrying a colon ends it — the next top-level key — so a comment or a stray word
    at any indent is skipped rather than treated as the end.
    """
    children = {}
    items = []
    is_sequence = False
    while index < end:
        line = lines[index]
        item = line.strip()
        if not item or item.startswith("#"):
            index += 1
            continue
        if item == "-" or item.startswith("- "):
            index += 1
            is_sequence = True
            entry = unquote(item[2:])
            if entry:
                items.append(entry)
            continue
        if not line[:1].isspace():
            if ":" in item:
                break
            index += 1
            continue
        index += 1
        colon = item.find(":")
        if colon != -1:
            children[item[:colon].strip().lower()] = unquote(item[colon + 1:])
    return index, (children or None), (items if is_sequence else None)


def parse_key(text, key):
    """The named key's value: a str (scalar), a dict (mapping), a list (sequence),
    or None when the key is absent, blank or unreadable.

    A key written twice resolves to its last written FORM, except that repeated
    sequence forms merge — naming a list twice must never silently shrink the list
    a guard enforces. Mixing forms is the case that clause does NOT cover:
    `protected: [main]` then `protected: junk` resolves to the scalar, every
    sequence consumer coerces a scalar to no items, and the guard stays armed
    over nothing. That is the fail-open rule of `docs/override-convention.md`
    applied to a malformed file rather than a bug — and it is why
    `activation.py check` exists, which reports such a key as inert.
    """
    block = _frontmatter(text)
    if block is None:
        return None
    lines, index, end = block
    key = key.lower()
    value = None
    items = []
    sequence = False
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
        if rest.startswith("[") and rest.endswith("]"):
            items.extend(_inline_list(rest))
            sequence = True
            continue
        # A comment where the value would be reads as no value at all, so
        # `watermark:  # note` opens the block form rather than yielding "# note".
        scalar = "" if rest.startswith("#") else unquote(rest)
        if scalar:
            value, sequence = scalar, False
            continue
        index, children, entries = _block(lines, index, end)
        if entries is None:
            value, sequence = children, False
        else:
            items.extend(entries)
            sequence = True
    return items if sequence else value


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
