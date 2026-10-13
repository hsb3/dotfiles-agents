---
id: decision-1
title: Own glob matcher for the page list instead of Bun.Glob
date: '2026-10-13 03:13'
status: accepted
---
## Context

SPEC.md fixes a small glob language for `pages` and `exclude`: `*` within one segment, `**` across segments, wildcards never match a name that starts with `.`, an explicit dot name does (`.github/CONTRIBUTING.md`), and a symlinked file matches like any other. `exclude` uses the same syntax but matches the selected page paths, not the disk. `Bun.Glob` supports a larger language (`?`, `[...]`, `{a,b}`, negation), has its own dot and symlink options whose interplay with explicit dot segments differs between `scan` and `match`, and would walk the whole checkout (including `.git` and `node_modules`) for a pattern such as `docs/**/*.md`.

## Decision

`src/pages.ts` implements the two wildcards itself: a segment matcher (`*` → `[^/]*`, no leading-dot match unless the pattern segment starts with `.`), a path matcher for `exclude`, and a walk that descends only where the pattern needs it. Only `*` and `**` are special; every other character is literal. `**` does not descend into symlinked folders (no cycles); symlinked files, and symlinked folders named by a literal or `*` segment, are followed. Only regular `.md` files are selected.

## Consequences

The page list follows the spec's rules exactly and the walk never enters `.git` or other dot folders. Patterns using `?`, braces or classes are not supported; they match literally, and an entry that then matches nothing is reported as a config error, so the limitation is visible.
