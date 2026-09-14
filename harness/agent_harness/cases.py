"""Case loader — cases are data, not code.

Layout (DESIGN §3, flattened from the workbench's ``<candidate>/cases/``):

    <cases_dir>/<candidate>/<case-id>/{case.json, fixture/, check.py}

``case.json`` = ``{prompt, assertions: [{id, text}]}``. Minimal validation only;
authoring guidance lives in ``cases/_template``.
"""

from __future__ import annotations

import json
import os
import sys


def load_cases(candidate, cases_dir, only=None):
    """Load ``<cases_dir>/<candidate>/*/case.json``; validate minimally.

    Returns a list of case dicts (each with injected ``id`` and ``dir``), ordered
    by case-id. Exits with a clear message on a malformed or empty dataset.
    """
    base = os.path.join(cases_dir, candidate)
    if not os.path.isdir(base):
        sys.exit(f"no eval cases at {base} — copy cases/_template to author some")
    cases = []
    for cid in sorted(os.listdir(base)):
        case_dir = os.path.join(base, cid)
        if not os.path.isdir(case_dir):
            continue
        cj = os.path.join(case_dir, "case.json")
        if not os.path.isfile(cj):
            continue
        if only and cid != only:
            continue
        with open(cj, encoding="utf-8") as fh:
            case = json.load(fh)
        if not case.get("prompt"):
            sys.exit(f"{cj}: missing required field 'prompt'")
        for a in case.get("assertions", []):
            if not a.get("id") or not a.get("text"):
                sys.exit(f"{cj}: every assertion needs 'id' and 'text'")
        case["id"] = cid
        case["dir"] = case_dir
        cases.append(case)
    if not cases:
        sys.exit(
            f"no case.json found under {base}" + (f" for --case {only}" if only else "")
        )
    return cases
