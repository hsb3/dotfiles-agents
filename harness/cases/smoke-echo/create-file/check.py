#!/usr/bin/env python3
"""Deterministic check for the smoke-echo case — runs IN the trial workspace.

Verifies the agent created HELLO.txt containing 'harness-ok'. This case is the
harness's own end-to-end self-test (a trivial task any base model can do); a
trivial candidate is injected only to exercise the load path. Stdlib only.
"""

import json
import os

checks = []

exists = os.path.isfile("HELLO.txt")
content = ""
if exists:
    with open("HELLO.txt", encoding="utf-8", errors="ignore") as fh:
        content = fh.read().strip()

checks.append(
    {
        "id": "hello-file-exists",
        "passed": exists,
        "evidence": "HELLO.txt present" if exists else "HELLO.txt missing in workspace",
    }
)
checks.append(
    {
        "id": "hello-content",
        "passed": content == "harness-ok",
        "evidence": f"HELLO.txt content={content!r} (want 'harness-ok')",
    }
)

print(json.dumps(checks))
