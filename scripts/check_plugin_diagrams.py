#!/usr/bin/env python3
"""Plugin-README diagram guard — every plugin ships a visual, and it cannot go stale silently.

Standard: docs/readme-diagram-standard.md. Each `plugins/<id>/README.md` is
hand-authored (bundle READMEs are regular files under ADR 0017, not symlinks) and carries at
least one Mermaid diagram drawing what the "What you get" table cannot — what makes each
piece fire, in what order, and what comes out.

A diagram is uniquely prone to rotting unnoticed. It is not prose anyone re-reads, and a
malformed one renders BLANK on GitHub with no error anywhere — the README looks fine in
source review and ships with a hole in it. MEASURED 2026-08-07 with mermaid-cli: a `(` in a
node label and a reserved word as a bare node id each produce NO output, and the CLI still
EXITS 0. Neither the renderer nor the exit code will tell you. Hence a static gate.

Six checks:

  1. Presence — every plugins/<id>/README.md carries at least one ```mermaid fence.
  2. House rule — no `( ) { } [ ] # ; " < > &` inside any node or edge label. This is the
     `mermaid` skill's standing rule. Not every character in the set breaks every renderer
     today (`&` currently renders), but the rule is deliberately broader than one renderer's
     present tolerance so that GitHub, IDE previews, and mermaid-cli all agree — the skill
     bans the characters outright rather than papering over them with HTML entities.
     Multi-character shapes (`[( )]`, `(( ))`, `[[ ]]`, `{{ }}`) are recognized first, so a
     legitimate cylinder or circle is not mistaken for a parenthesis in a label.
  3. Reserved word as a bare node id — `load --> end` is a hard parse failure. Detected by
     adjacency to an arrow, so a legitimate `end` closing a subgraph is untouched.
  4. Theme safety — no hardcoded `fill:` in a `style`/`classDef` line. GitHub renders with
     the viewer's theme; a hardcoded light fill goes invisible on dark.
  5. Node ceiling — at most MAX_NODES per fence. Past that the diagram has become a second
     table, which is the one thing the standard exists to prevent.
  6. No ghost primitives — every node label naming a KNOWN primitive names one that plugin
     actually ships. This is the check that earns the script's keep: a renamed or retired
     primitive leaves a stale node in a picture nobody re-read (the `foreman`->`atelier`
     class of bug), and no other gate reads diagram bodies. Membership is derived from the
     symlink assembly on disk, never from a recorded list.

Deliberately NOT covered: whether a diagram is any GOOD. "Draw the trigger and the flow,
never the inventory" is a human call at review time — a tidy diagram that is just the table
redrawn passes all five checks.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_plugin_diagrams.py   (run from anywhere)
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(REPO, "plugins")
PRIMITIVES_DIR = os.path.join(REPO, "primitives-core")

#: House rule (mermaid skill): these break rendering inside a label, silently or hard.
BANNED_LABEL_CHARS = "(){}[]#;\"<>&"

#: Ceiling, not a target. The standard asks for 15 or fewer; past 20 it is a second table.
MAX_NODES = 20

#: Longest opener first — `[(` must beat `[`, or a cylinder reads as a parenthesis in a label.
SHAPE_PAIRS = (
    ("[(", ")]"),
    ("((", "))"),
    ("[[", "]]"),
    ("{{", "}}"),
    ("([", "])"),
    ("[", "]"),
    ("(", ")"),
    ("{", "}"),
    (">", "]"),
)

#: Mermaid grammar and flowchart directions — never node ids, so they do not count as nodes.
RESERVED = frozenset(
    """flowchart graph subgraph end direction style classDef class click linkStyle
    TD TB BT LR RL sequenceDiagram participant erDiagram stateDiagram-v2 classDiagram
    """.split()
)

MERMAID_FENCE_RE = re.compile(r"^```mermaid[ \t]*\n(.*?)^```", re.MULTILINE | re.DOTALL)
COMMENT_RE = re.compile(r"^\s*%%.*$", re.MULTILINE)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
FILL_RE = re.compile(r"^\s*(?:style|classDef)\b.*\bfill\s*:", re.MULTILINE)

#: Every flowchart edge form: `-->`, `--->`, `-.->`, `==>`, and the plain `---` connector.
ARROW_RE = re.compile(r"[-=.]{2,}>|-{3}")
#: The inline-label edge forms — `-.text.->`, `--text-->`, `==text==>`. The middle excludes
#: `>` so a match can never span two arrows and mask the node between them.
EDGE_INLINE_LABEL_RE = re.compile(r"(--|-\.|==)([^\n>]*?)(\.-+>|-+>|=+>)")
LEADING_IDENT_RE = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_-]*)")
TRAILING_IDENT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)\s*$")


def _fences(text):
    """Return the body of every ```mermaid block, in document order."""
    return [m.group(1) for m in MERMAID_FENCE_RE.finditer(text)]


def _scan_shape_labels(body):
    """Return (label, offset) for every `id[label]`-style node label in a fence body.

    Hand-rolled rather than regex because the check must SEE a banned character that a
    tolerant regex would skip past: the scanner takes everything up to the closer, so
    `A[Auth Service (JWT)]` yields the label WITH its parentheses and check 2 fires.
    """
    labels = []
    i, n = 0, len(body)
    while i < n:
        m = IDENT_RE.match(body, i)
        if not m:
            i += 1
            continue
        j = m.end()
        for opener, closer in SHAPE_PAIRS:
            if body.startswith(opener, j):
                k = body.find(closer, j + len(opener))
                if k != -1:
                    labels.append((body[j + len(opener):k], j + len(opener)))
                    j = k + len(closer)
                break
        i = max(j, m.end())
    return labels


def _edge_labels(body):
    """Return every `|label|` edge label in a fence body."""
    return [seg for seg in re.findall(r"\|([^|\n]*)\|", body)]


def _mask_labels(body):
    """Blank every label — node shape, `|pipe|`, and inline edge — leaving ids and arrows.

    Arrow characters survive so a caller can still split on ARROW_RE. The inline forms
    (`-.text.->`, `--text-->`, `==text==>`) are as valid as the pipe form, and a label left
    unmasked reads as node ids; the mask never crosses a `>`, so a chained `A --> B --> C`
    cannot swallow B.
    """
    masked = list(body)
    for label, off in _scan_shape_labels(body):
        for p in range(off, off + len(label)):
            masked[p] = " "
    masked = re.sub(r"\|[^|\n]*\|", " ", "".join(masked))
    return EDGE_INLINE_LABEL_RE.sub(
        lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), masked)


def _node_ids(body):
    """Distinct node ids in a fence, for the ceiling check.

    Labels are blanked first so their prose never reads as an identifier; what remains is
    ids, arrows, and grammar, and RESERVED removes the grammar.
    """
    masked = _mask_labels(body)
    ids = set()
    for line in masked.splitlines():
        stripped = line.strip()
        # `subgraph Foo` names a container, not a node.
        if stripped.startswith("subgraph"):
            continue
        for tok in IDENT_RE.findall(line):
            if tok not in RESERVED:
                ids.add(tok)
    return ids


def _reserved_used_as_node_ids(body):
    """Reserved words sitting on either side of an arrow, i.e. used as node ids.

    Labels are blanked first so prose containing the word `end` or `class` is not mistaken
    for a node id.
    """
    masked = _mask_labels(body)
    hits = set()
    for line in masked.splitlines():
        parts = ARROW_RE.split(line)
        if len(parts) < 2:
            continue
        for i, part in enumerate(parts):
            # an identifier abutting an arrow on either side is being used as a node id
            candidates = []
            if i > 0:
                m = LEADING_IDENT_RE.match(part)
                if m:
                    candidates.append(m.group(1))
            if i < len(parts) - 1:
                m = TRAILING_IDENT_RE.search(part)
                if m:
                    candidates.append(m.group(1))
            hits |= {c for c in candidates if c in RESERVED}
    return hits


def _known_primitive_ids():
    """Every primitive id under primitives-core/, by directory (skills/hooks) or stem (agents)."""
    ids = set()
    for kind in ("skills", "hooks"):
        d = os.path.join(PRIMITIVES_DIR, kind)
        if os.path.isdir(d):
            ids |= {
                e for e in os.listdir(d)
                if not e.startswith(".") and os.path.isdir(os.path.join(d, e))
            }
    d = os.path.join(PRIMITIVES_DIR, "agents")
    if os.path.isdir(d):
        ids |= {e[:-3] for e in os.listdir(d) if e.endswith(".md")}
    return ids


def _assembly_members(pid):
    """What plugins/<pid>/ actually ships, derived live from the assembly.

    Same basis as check_catalog._assembly_counts and check_solo_skills._members: skills and
    hooks are directories, agents are .md files. Loose files (hooks.json) are not members.
    """
    base = os.path.join(PLUGINS_DIR, pid)
    members = set()
    for kind in ("skills", "hooks"):
        d = os.path.join(base, kind)
        if os.path.isdir(d):
            members |= {
                e for e in os.listdir(d)
                if not e.startswith(".") and os.path.isdir(os.path.join(d, e))
            }
    d = os.path.join(base, "agents")
    if os.path.isdir(d):
        members |= {e[:-3] for e in os.listdir(d) if e.endswith(".md")}
    return members


def _plugin_ids():
    if not os.path.isdir(PLUGINS_DIR):
        return []
    return sorted(
        e for e in os.listdir(PLUGINS_DIR)
        if not e.startswith(".") and os.path.isdir(os.path.join(PLUGINS_DIR, e))
    )


def _fence_problems(rel, idx, body, members, known):
    out = []
    where = f"{rel}: mermaid block {idx + 1}"
    body = COMMENT_RE.sub("", body)

    labels = [lab for lab, _ in _scan_shape_labels(body)] + _edge_labels(body)

    for lab in labels:
        hits = sorted({c for c in lab if c in BANNED_LABEL_CHARS})
        if hits:
            out.append(
                f"{where}: label {lab.strip()!r} contains {' '.join(hits)} — the mermaid "
                "house rule bans these in a label; they render blank on GitHub with no error"
            )

    for word in sorted(_reserved_used_as_node_ids(body)):
        out.append(
            f"{where}: {word!r} is a Mermaid reserved word used as a bare node id — this is a "
            f"hard parse failure that renders nothing; give the node its own id and keep "
            f"{word!r} as the label, e.g. fin[{word}]"
        )

    if FILL_RE.search(body):
        out.append(
            f"{where}: hardcoded fill: colour — GitHub renders with the viewer's theme, so a "
            "fixed light fill goes invisible on dark; drop the style or use theme neutral"
        )

    nodes = _node_ids(body)
    if len(nodes) > MAX_NODES:
        out.append(
            f"{where}: {len(nodes)} nodes exceeds the ceiling of {MAX_NODES} — this has "
            "become a second table; split it or raise its altitude"
        )

    for lab in labels:
        for tok in IDENT_RE.findall(lab):
            if tok in known and tok not in members:
                out.append(
                    f"{where}: label {lab.strip()!r} names the primitive {tok!r}, which this "
                    "plugin does not ship — a renamed or retired primitive left a ghost in "
                    "the diagram; check the assembly under plugins/"
                )
    return out


def problems():
    out = []
    known = _known_primitive_ids()
    for pid in _plugin_ids():
        rel = f"plugins/{pid}/README.md"
        path = os.path.join(PLUGINS_DIR, pid, "README.md")
        if not os.path.isfile(path):
            out.append(f"{rel}: missing — every plugin needs a README carrying its diagram")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        fences = _fences(text)
        if not fences:
            out.append(
                f"{rel}: no ```mermaid block — every plugin README carries at least one "
                "diagram (docs/readme-diagram-standard.md)"
            )
            continue
        members = _assembly_members(pid)
        for idx, body in enumerate(fences):
            out.extend(_fence_problems(rel, idx, body, members, known))
    return out


def main():
    found = problems()
    if found:
        print(f"plugin-README diagram guard: {len(found)} problem(s)")
        for p in found:
            print(f"  - {p}")
        return 1
    n = len(_plugin_ids())
    print(f"plugin-README diagram guard: OK ({n} plugin READMEs, each with a diagram)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
