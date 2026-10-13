#!/usr/bin/env python3
"""Deterministic checks for local-bookmark-vault — runs IN the trial workspace
after the run (fixture/ contents are flattened into the workspace root, so
Makefile, server.py, tests/, static/ sit alongside whatever the agent wrote).

Verifies:
  c1 — README.md exists.
  c2 — README.md references at least one command that is *actually real*
       against this fixture (a `make <target>` where <target> is a genuine
       Makefile target, or a literal `python3 ...` invocation known to work
       here) — not a fabricated/generic command. Ties directly to the case
       prompt's "back up your claims with real proof" instruction.
  c3 — README.md avoids the skill's named hype phrases (readme-value-and-proof
       SKILL.md L20-21: "Avoid 'production-ready', 'seamless', 'blazing-fast',
       'MISSION ACCOMPLISHED', and similar").
  c4 — if README.md embeds any local (non-http) markdown image reference, the
       referenced path resolves to a real file in the workspace (supports, but
       does not replace, the LLM-graded a4 assertion about the image's actual
       content — SKILL.md L87-89: "verify every ref resolves").

Stdlib only.
"""

import json
import os
import re

checks = []

readme_path = "README.md"
readme_exists = os.path.isfile(readme_path)
readme_text = ""
if readme_exists:
    with open(readme_path, encoding="utf-8", errors="ignore") as fh:
        readme_text = fh.read()

checks.append(
    {
        "id": "c1-readme-exists",
        "passed": readme_exists,
        "evidence": f"{readme_path} {'present' if readme_exists else 'missing'} in workspace",
    }
)

# --- c2: a runnable command in README that is genuinely real for this fixture ---

makefile_targets = []
if os.path.isfile("Makefile"):
    with open("Makefile", encoding="utf-8", errors="ignore") as fh:
        makefile_text = fh.read()
    makefile_targets = re.findall(r"^([A-Za-z][\w-]*):", makefile_text, re.MULTILINE)
    makefile_targets = [t for t in makefile_targets if t != "PHONY"]

real_commands = [f"make {t}" for t in makefile_targets]
if os.path.isfile("server.py"):
    real_commands.append("python3 server.py")
if os.path.isdir("tests"):
    real_commands.append("python3 -m unittest discover -s tests")

matched = [cmd for cmd in real_commands if readme_exists and cmd in readme_text]
checks.append(
    {
        "id": "c2-references-real-runnable-command",
        "passed": bool(matched),
        "evidence": (
            f"README.md contains real command(s): {matched}"
            if matched
            else f"README.md contains none of the fixture's real commands {real_commands}"
        ),
    }
)

# --- c3: no banned hype phrases (SKILL.md L20-21) ---

BANNED_PATTERNS = {
    "production-ready": r"production[- ]ready",
    "seamless": r"seamless",
    "blazing-fast": r"blazing[- ]fast",
    "MISSION ACCOMPLISHED": r"mission\s+accomplished",
}
found_hype = []
for label, pattern in BANNED_PATTERNS.items():
    if re.search(pattern, readme_text, re.IGNORECASE):
        found_hype.append(label)

checks.append(
    {
        "id": "c3-no-banned-hype-phrases",
        "passed": readme_exists and not found_hype,
        "evidence": (
            f"found banned phrase(s): {found_hype}"
            if found_hype
            else "none of the skill's named hype phrases found in README.md"
        ),
    }
)

# --- c4: any local image ref in README resolves to a real file ---

image_refs = re.findall(r"!\[[^\]]*\]\(([^)\s]+)", readme_text)
local_refs = [r for r in image_refs if not re.match(r"^[a-zA-Z]+://", r)]
if local_refs:
    unresolved = [r for r in local_refs if not os.path.isfile(r)]
    checks.append(
        {
            "id": "c4-local-image-refs-resolve",
            "passed": not unresolved,
            "evidence": (
                f"all {len(local_refs)} local image ref(s) resolve: {local_refs}"
                if not unresolved
                else f"unresolved image ref(s): {unresolved}"
            ),
        }
    )
else:
    checks.append(
        {
            "id": "c4-local-image-refs-resolve",
            "passed": False,
            "evidence": "no local (non-URL) markdown image reference found in README.md",
        }
    )

print(json.dumps(checks))
