"""Candidate classification — vendor-neutral.

Deciding whether a candidate dir is a skill / plugin / agent is the same
question for every harness; the per-vendor *injection mechanics* for each kind
live in the adapter (e.g. ``adapters/claude.py``).
"""

from __future__ import annotations

import os


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
