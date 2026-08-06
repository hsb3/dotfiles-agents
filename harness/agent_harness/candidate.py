"""Candidate classification and resolution — vendor-neutral.

Deciding whether a candidate dir is a skill / plugin / agent is the same
question for every harness; the per-vendor *injection mechanics* for each kind
live in the adapter (e.g. ``adapters/claude.py``).

A "candidate" on disk is either a directory (skill/plugin/agent-with-multiple-
files) or, for the single-file agent case, a lone ``.md`` file. Both adapters
build agent definitions by listing ``*.md`` files in a directory — the
directory's *name* is irrelevant to them, only the frontmatter ``name:``
inside each file matters — so ``resolved_candidate_dir`` stages a flat
``.md`` file into a throwaway directory and yields that, giving every caller
a directory to work with either way.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile


def detect_kind(path):
    """Classify a candidate dir: 'skill' | 'plugin' | 'agent' | None."""
    if os.path.isfile(os.path.join(path, "SKILL.md")):
        return "skill"
    if os.path.isfile(os.path.join(path, ".claude-plugin", "plugin.json")):
        return "plugin"
    mds = [
        f for f in os.listdir(path) if f.endswith(".md") and f.lower() != "readme.md"
    ]
    return "agent" if mds else None


@contextlib.contextmanager
def resolved_candidate_dir(path):
    """Yield a directory to classify/inject for ``path``.

    ``path`` may be either a candidate directory — yielded unchanged, no copy
    and no cleanup of it — or a single flat agent ``.md`` file, which is
    copied into a fresh temporary directory that is yielded instead and
    removed on every exit path (normal return or exception).

    Raises FileNotFoundError if ``path`` does not exist, and ValueError if it
    exists but is neither a directory nor a ``.md`` file.
    """
    if os.path.isdir(path):
        yield path
        return
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if not path.endswith(".md"):
        raise ValueError(f"{path}: not a directory or a flat agent .md file")
    staged = tempfile.mkdtemp(prefix="agent-harness-candidate-")
    try:
        shutil.copy2(path, os.path.join(staged, os.path.basename(path)))
        yield staged
    finally:
        shutil.rmtree(staged, ignore_errors=True)
