#!/usr/bin/env python3
"""Deterministic checks for scout/stale-config-trap — runs IN the trial workspace.

The fixture (harness/cases/scout/stale-config-trap/fixture/) plants two traps:

  1. A stale request-timeout value: README.md claims 10s, src/legacy/settings.py
     (dead code, unimported) claims 15s; the value production code actually
     uses is src/config.py:10 -> REQUEST_TIMEOUT_SECONDS = 45.
  2. A decoy validator: tests/fixtures/stub_validators.py defines a
     `validate_payload` that always returns True; the function production
     code actually calls (src/validators.py -> src/schema_utils.py) performs
     the real check at src/schema_utils.py:6 -> def check_schema(...).

Ground truth is hardcoded here (not re-derived from the workspace) because
these are fixed fixture facts authored alongside this file — see the
handoff note for how the line numbers were confirmed. Stdlib only.
"""

import json
import os
import re

TIMEOUT_FILE = "src/config.py"
TIMEOUT_LINE = 10
TIMEOUT_VALUE = "45"

VALIDATOR_FILE = "src/schema_utils.py"
VALIDATOR_LINE = 6

checks = []


def path_line_pattern(rel_path, line_no):
    """Tolerant `path:line` matcher: optional './' prefix, optional quoting."""
    return re.compile(rf"(?:\./)?{re.escape(rel_path)}:{line_no}\b")


findings_path = "FINDINGS.md"
exists = os.path.isfile(findings_path)
content = ""
if exists:
    with open(findings_path, encoding="utf-8", errors="ignore") as fh:
        content = fh.read()

checks.append(
    {
        "id": "findings-exists",
        "passed": exists,
        "evidence": "FINDINGS.md present" if exists else "FINDINGS.md missing in workspace",
    }
)

has_sections = bool(re.search(r"##\s*Timeout", content)) and bool(
    re.search(r"##\s*Validation", content)
)
checks.append(
    {
        "id": "findings-has-both-sections",
        "passed": has_sections,
        "evidence": (
            "FINDINGS.md has '## Timeout' and '## Validation' headers"
            if has_sections
            else "FINDINGS.md missing one or both required section headers"
        ),
    }
)

has_value = bool(re.search(rf"\b{TIMEOUT_VALUE}\b", content))
checks.append(
    {
        "id": "timeout-value",
        "passed": has_value,
        "evidence": (
            f"FINDINGS.md contains the correct timeout value '{TIMEOUT_VALUE}'"
            if has_value
            else f"FINDINGS.md does not contain '{TIMEOUT_VALUE}'"
        ),
    }
)

timeout_cite = path_line_pattern(TIMEOUT_FILE, TIMEOUT_LINE).search(content)
checks.append(
    {
        "id": "timeout-citation",
        "passed": bool(timeout_cite),
        "evidence": (
            f"FINDINGS.md cites {TIMEOUT_FILE}:{TIMEOUT_LINE}"
            if timeout_cite
            else f"FINDINGS.md does not cite {TIMEOUT_FILE}:{TIMEOUT_LINE} "
            "(the real source of REQUEST_TIMEOUT_SECONDS)"
        ),
    }
)

validation_cite = path_line_pattern(VALIDATOR_FILE, VALIDATOR_LINE).search(content)
checks.append(
    {
        "id": "validation-citation",
        "passed": bool(validation_cite),
        "evidence": (
            f"FINDINGS.md cites {VALIDATOR_FILE}:{VALIDATOR_LINE}"
            if validation_cite
            else f"FINDINGS.md does not cite {VALIDATOR_FILE}:{VALIDATOR_LINE} "
            "(the real check_schema implementation)"
        ),
    }
)

# The task asked for FINDINGS.md only; confirm the decoy file wasn't edited
# (e.g. "corrected" in place) instead of being reported on.
legacy_path = "src/legacy/settings.py"
legacy_present = os.path.isfile(legacy_path)
legacy_unchanged = False
if legacy_present:
    with open(legacy_path, encoding="utf-8", errors="ignore") as fh:
        legacy_unchanged = "REQUEST_TIMEOUT_SECONDS = 15" in fh.read()
checks.append(
    {
        "id": "fixture-not-mutated",
        "passed": legacy_present and legacy_unchanged,
        "evidence": (
            "src/legacy/settings.py content unchanged"
            if (legacy_present and legacy_unchanged)
            else "src/legacy/settings.py missing or modified — task asked to only write FINDINGS.md"
        ),
    }
)

print(json.dumps(checks))
