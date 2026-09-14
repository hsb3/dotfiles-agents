#!/usr/bin/env python3
"""Deterministic checks for this case — runs IN the trial workspace after the run.

Prints a JSON list of {"id", "passed", "evidence"} to stdout. Stdlib only.
Delete this file if the case has no deterministic checks. Pattern examples:
file-structure presence, required-idiom greps, `py_compile` syntax checks.
"""

import json
import os

checks = []

# Example: a required file exists in the final workspace state.
target = "README.md"  # REPLACE
checks.append(
    {
        "id": "c1-file-exists",
        "passed": os.path.isfile(target),
        "evidence": f"{target} {'present' if os.path.isfile(target) else 'missing'} in workspace",
    }
)

print(json.dumps(checks))
