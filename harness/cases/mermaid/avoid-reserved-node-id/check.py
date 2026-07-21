#!/usr/bin/env python3
"""Deterministic checks for avoid-reserved-node-id — runs IN the trial workspace.

Verifies PIPELINE.md gained a fenced ```mermaid``` flowchart, and that the
diagram does NOT use the bare reserved word `end` as a node identifier
(primitives-core/skills/mermaid/SKILL.md Pitfalls table, L146: "Reserved
word as bare node id (`end`, `class`)" -> "Rename the id (`fin`, `cls`)").
The fixture's pipeline.py defines a stage function literally named `end`,
and the prompt asks for node identifiers to match function names verbatim
-- the exact trap the skill warns about. A baseline model without the
skill plausibly follows the instruction literally and emits `end` as a
bare node id, which breaks the mermaid parser ("Syntax error in text").
Stdlib only.
"""

import json
import os
import re

checks = []

ARROW = r"(?:-->|---|-\.->|==>)"
DIAGRAM_TYPE_RE = re.compile(r"^\s*(flowchart|graph)\s+(TD|TB|LR|RL|BT)\b", re.MULTILINE)
OTHER_DIAGRAM_KEYWORDS = ("stateDiagram", "sequenceDiagram")

pipeline_md_path = "PIPELINE.md"
text = ""
if os.path.isfile(pipeline_md_path):
    with open(pipeline_md_path, encoding="utf-8", errors="ignore") as fh:
        text = fh.read()

fence_re = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
blocks = fence_re.findall(text)
has_fence = bool(blocks)
checks.append(
    {
        "id": "c1-mermaid-fence-in-pipeline-md",
        "passed": has_fence,
        "evidence": (
            f"found {len(blocks)} ```mermaid fenced block(s) in PIPELINE.md"
            if has_fence
            else "no ```mermaid fenced block found in PIPELINE.md"
        ),
    }
)

diagram_body = "\n".join(blocks)

has_diagram_type = bool(DIAGRAM_TYPE_RE.search(diagram_body)) or any(
    kw in diagram_body for kw in OTHER_DIAGRAM_KEYWORDS
)
checks.append(
    {
        "id": "c2-diagram-type-declared",
        "passed": has_diagram_type,
        "evidence": (
            "diagram body declares a recognized flowchart/state opening line"
            if has_diagram_type
            else f"no recognized diagram-type opening line in: {diagram_body[:200]!r}"
        ),
    }
)

# Pitfalls table (SKILL.md L146): bare `end` as a node id breaks the parser.
# Heuristic: flag `end` immediately adjacent to node-shape delimiters or
# arrow syntax (identifier position) -- NOT `end` appearing as ordinary
# label text (e.g. a label `[the end]` is fine; only the wiring id matters).
BARE_END_PATTERNS = [
    r"\bend\s*[\[({]",
    rf"{ARROW}\s*end\b(?!\w)",
    rf"\bend\s*{ARROW}",
    r"\bend:::",
]
violations = []
for pat in BARE_END_PATTERNS:
    for m in re.finditer(pat, diagram_body):
        violations.append(f"pattern {pat!r} matched {m.group(0)!r}")

checks.append(
    {
        "id": "c3-no-bare-reserved-end-node-id",
        "passed": has_fence and not violations,
        "evidence": (
            "no bare `end` node identifier found"
            if not violations
            else f"{len(violations)} reserved-word violation(s): " + "; ".join(violations[:5])
        ),
    }
)

# Sanity: a real 5-stage chain has at least 4 connecting arrows.
arrow_count = len(re.findall(ARROW, diagram_body))
checks.append(
    {
        "id": "c4-nontrivial-chain",
        "passed": has_fence and arrow_count >= 4,
        "evidence": f"found {arrow_count} arrow connection(s) in the diagram (want >= 4)",
    }
)

# The prompt says "do not modify pipeline.py" -- spot-check it is unchanged.
# Full-content equality (not startswith/prefix) so an append-only tamper at
# the end of the file is still caught.
sentinel_path = "pipeline.py"
sentinel_expected = (
    '"""Simple ETL pipeline stages, executed in order: '
    'start, extract, transform, load, end."""\n'
    "\n"
    "\n"
    "def start():\n"
    '    """Initializes the pipeline run and allocates a run id."""\n'
    "\n"
    "\n"
    "def extract():\n"
    '    """Pulls raw records from the source system."""\n'
    "\n"
    "\n"
    "def transform():\n"
    '    """Cleans and reshapes records for loading."""\n'
    "\n"
    "\n"
    "def load():\n"
    '    """Writes records into the warehouse."""\n'
    "\n"
    "\n"
    "def end():\n"
    '    """Finalizes the pipeline run and emits metrics."""\n'
)
sentinel_ok = False
sentinel_actual = ""
if os.path.isfile(sentinel_path):
    with open(sentinel_path, encoding="utf-8", errors="ignore") as fh:
        sentinel_actual = fh.read()
    sentinel_ok = sentinel_actual == sentinel_expected

checks.append(
    {
        "id": "c5-pipeline-source-untouched",
        "passed": sentinel_ok,
        "evidence": (
            f"{sentinel_path} unchanged"
            if sentinel_ok
            else f"{sentinel_path} missing or modified (got {sentinel_actual[:80]!r})"
        ),
    }
)

print(json.dumps(checks))
