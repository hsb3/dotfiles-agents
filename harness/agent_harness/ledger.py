"""Results ledger — append-only JSONL, resumable.

One row per trial, ``json.dumps(sort_keys=True)``. The resume key is
**campaign|harness|model|candidate|case|config|trial**: ``harness``/``model`` were
added over the workbench (DESIGN §3); ``campaign`` is prepended (#171) so a re-run
after a harness fix stays distinct from the pre-fix rows in the same ledger. Rows
written before the campaign field read as ``""`` (backward compatible).
"""

from __future__ import annotations

import json
import os


def row_key(row):
    """Resume key: campaign|harness|model|candidate|case|config|trial.

    ``campaign`` defaults to ``""`` for rows predating the field, so old rows keep
    their key shape (empty first segment) and never collide with a labeled re-run.
    """
    return (
        f"{row.get('campaign', '')}|{row['harness']}|{row['model']}|{row['candidate']}"
        f"|{row['case']}|{row['config']}|{row['trial']}"
    )


def load_done(path):
    """Set of resume keys already present in the ledger (corrupt lines skipped)."""
    if not os.path.isfile(path):
        return set()
    done = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                done.add(row_key(json.loads(line)))
            except (ValueError, KeyError):
                continue
    return done


def append_row(path, row):
    """Append one row as a sorted-key JSON line."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def read_rows(path, candidate):
    """All rows for `candidate` (corrupt lines skipped)."""
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("candidate") == candidate:
                rows.append(row)
    return rows
