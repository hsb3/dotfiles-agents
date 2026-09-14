#!/usr/bin/env python3
"""Deterministic checks for add-architecture-diagram — runs IN the trial workspace.

Verifies README.md gained a fenced ```mermaid``` block with a recognized
diagram-type opening line, and that no node label, edge label, or subgraph
title inside it violates the mermaid skill's house rule
(primitives-core/skills/mermaid/SKILL.md L10-24): node/edge/subgraph-title
text must not contain `(`, `)`, `{`, `}`, `[`, `]`, `#`, `;`, `"`, `<`, `>`,
or `&`. The fixture's services/*.py docstrings are written with tempting
parenthetical detail (e.g. "Auth Service (OAuth2 + JWT)") specifically to
bait a baseline model into copying that punctuation straight into a node
label — the skill's own WRONG example (SKILL.md L21: `B[Auth Service
(JWT)]`). Also spot-checks that services/ was left untouched, per the
prompt's explicit "do not modify" instruction. Stdlib only.
"""

import json
import os
import re

checks = []

FORBIDDEN = set("(){}[]#;\"<>&")
DIAGRAM_TYPE_RE = re.compile(r"^\s*(flowchart|graph)\s+(TD|TB|LR|RL|BT)\b", re.MULTILINE)
OTHER_DIAGRAM_KEYWORDS = ("sequenceDiagram", "erDiagram", "stateDiagram", "classDiagram")

readme_path = "README.md"
readme_text = ""
if os.path.isfile(readme_path):
    with open(readme_path, encoding="utf-8", errors="ignore") as fh:
        readme_text = fh.read()

fence_re = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
blocks = fence_re.findall(readme_text)
has_fence = bool(blocks)
checks.append(
    {
        "id": "c1-mermaid-fence-in-readme",
        "passed": has_fence,
        "evidence": (
            f"found {len(blocks)} ```mermaid fenced block(s) in README.md"
            if has_fence
            else "no ```mermaid fenced block found in README.md"
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
            "diagram body declares a recognized opening line"
            if has_diagram_type
            else f"no recognized diagram-type opening line in: {diagram_body[:200]!r}"
        ),
    }
)

# House rule (SKILL.md L10-24): no parens/special chars inside node labels,
# edge labels, or subgraph titles.
#
# Node-shape delimiters (SKILL.md L57: `[box]`, `(rounded)`, `{diamond}`,
# `[(database)]`, `((circle))`) legitimately reuse `(` and `[` as STRUCTURE,
# not label content -- e.g. `DB[(Postgres)]` (SKILL.md L47) is correct
# mermaid, not a house-rule violation. Peel the most specific (longest)
# shape delimiters first and blank each match out of a working copy so a
# later, broader pattern can't re-capture the delimiters themselves as
# "forbidden content" inside a plain `[Label]` node.
violations = []
working = diagram_body
shape_patterns = [
    (r"\[\(([^)\]]*)\)\]", "database-shape"),  # id[(Label)]
    (r"\(\(([^)]*)\)\)", "circle-shape"),  # id((Label))
    (r"\(\[([^\]]*)\]\)", "stadium-shape"),  # id([Label])
    (r"\[\[([^\]]*)\]\]", "subroutine-shape"),  # id[[Label]]
    (r"\{([^}\n]*)\}", "diamond-shape"),  # id{Label}
    (r"\[([^\]\n]*)\]", "box-shape"),  # id[Label]
    (r"\(([^)\n]*)\)", "rounded-shape"),  # id(Label)
]


def _check_and_blank(m, shape):
    label = m.group(1)
    bad = FORBIDDEN.intersection(label)
    if bad:
        violations.append(f"{shape} label {label!r} contains {sorted(bad)}")
    return "\0" * len(m.group(0))


for pattern, shape_name in shape_patterns:
    working = re.sub(pattern, lambda m, s=shape_name: _check_and_blank(m, s), working)

for m in re.finditer(r"\|([^|\n]*)\|", diagram_body):
    label = m.group(1)
    bad = FORBIDDEN.intersection(label)
    if bad:
        violations.append(f"edge label {label!r} contains {sorted(bad)}")
for m in re.finditer(r"^\s*subgraph\s+(.+)$", diagram_body, re.MULTILINE):
    title = m.group(1)
    bad = FORBIDDEN.intersection(title)
    if bad:
        violations.append(f"subgraph title {title!r} contains {sorted(bad)}")

checks.append(
    {
        "id": "c3-house-rule-no-special-chars-in-labels",
        "passed": has_fence and not violations,
        "evidence": (
            "no mermaid block to check (c1 failed)"
            if not has_fence
            else "no forbidden characters found in node/edge/subgraph labels"
            if not violations
            else f"{len(violations)} house-rule violation(s): " + "; ".join(violations[:5])
        ),
    }
)

# The prompt says "do not modify any files under services/" — spot-check one
# fixture file's known original docstring survives byte-for-byte.
sentinel_path = os.path.join("services", "auth_service.py")
sentinel_expected = (
    '"""Auth Service (OAuth2 + JWT) - issues and validates access tokens for '
    'the platform; reads and writes user records in the Primary Datastore."""\n'
)
sentinel_ok = False
sentinel_actual = ""
if os.path.isfile(sentinel_path):
    with open(sentinel_path, encoding="utf-8", errors="ignore") as fh:
        sentinel_actual = fh.read()
    sentinel_ok = sentinel_actual == sentinel_expected

checks.append(
    {
        "id": "c4-services-untouched",
        "passed": sentinel_ok,
        "evidence": (
            f"{sentinel_path} unchanged"
            if sentinel_ok
            else f"{sentinel_path} missing or modified (got {sentinel_actual[:80]!r})"
        ),
    }
)

print(json.dumps(checks))
