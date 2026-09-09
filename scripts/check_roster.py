#!/usr/bin/env python3
"""Roster <-> disk drift guard (issue #5) + the translation-matrix completeness gate.

Verifies that primitives-core.yaml (the roster, slimmed to a provenance manifest per
ADR 0017) and primitives-core/ on disk agree:
  - every roster entry's `source` exists on disk
  - every primitive on disk (skill dir, agent .md, command .md, hook handler .sh, mcp .json)
    has a roster entry
  - basic schema: required fields present, type ∈ {skill,agent,command,mcp,hook},
    origin ∈ {authored,sourced,vendored}, disposition ∈ {qualified,grandfathered-pending-use,demoted,untriaged,orphaned}
  - `requires` (optional) is a list of {hooks,local-mcp,hosted-mcp} capability words plus
    dependency declarations `cli:<kebab>` (a binary/app that must be installed) and
    `env:<kebab>` (machine state, e.g. env:dotfiles) — issue #79
  - provenance: every `origin: sourced` or `origin: vendored` entry carries non-null
    `upstream` and `ref`

It also owns translation.yaml's parser and the matrix-completeness gate (decision-009): every
frontmatter key, tool and model alias used by an agent must be declared in translation.yaml,
so nothing reaches gen_opencode.py as a silent drop. The parser lives here rather than in the
generator because the gate must run without importing it (gen_opencode imports from this file).

Stdlib-only (a tailored line parser for the roster's controlled format — no pyyaml), so it runs
in CI with zero install. Exit 0 = clean; exit 1 = drift (prints every problem).

Usage: python3 scripts/check_roster.py   (run from the repo root)
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(REPO, "primitives-core.yaml")
PC = os.path.join(REPO, "primitives-core")
TRANSLATION = os.path.join(REPO, "translation.yaml")
AGENTS = os.path.join(PC, "agents")

TYPES = {"skill", "agent", "command", "mcp", "hook"}
# The runtime enum (ADR 0017): claude-code installs the symlink assemblies natively;
# opencode is generated at install time by gen_opencode.py (task-4).
TARGETS = {"claude-code", "opencode", "codex"}
ORIGINS = {"authored", "sourced", "vendored"}
DISPOSITIONS = {"qualified", "grandfathered-pending-use", "demoted", "untriaged", "orphaned"}
CAPABILITIES = {"hooks", "local-mcp", "hosted-mcp"}
# translation.yaml's two closed vocabularies (decision-009): the neutral capability words
# tool_capabilities rows map onto, and the treatments a frontmatter field may carry.
TOOL_CAPABILITIES = {"read", "search", "edit", "execute", "delegate"}
FIELD_TREATMENTS = {"map", "drop-with-notice", "unsupported"}
TRANSLATION_SECTIONS = ("matrix", "model_aliases", "tool_capabilities", "field_treatments",
                        "exclusions")
# Dependency declarations (issue #79): cli:<kebab> = a binary/app the primitive invokes;
# env:<kebab> = machine state it assumes (e.g. env:dotfiles). Deploy tooling reads these.
REQUIRES_DEP = re.compile(r"^(cli|env):[a-z0-9][a-z0-9_-]*$")
REQUIRED = (
    "id",
    "type",
    "source",
    "origin",
    "disposition",
    "targets",
)


def _list(v):
    """Parse a `[a, b]`-style inline list value into a Python list (mirrors translate._list)."""
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip() for x in inner.split(",")] if inner else []
    return [v] if v else []


def parse_roster(path):
    """Parse the roster's `primitives:` list into dicts. Tailored to our emitter's format:
    each entry starts with `  - id: <v>` and continues with `    <key>: <v>` lines.
    Duplicate keys within one entry: last wins (documented, not guarded)."""
    entries, cur = [], None
    in_list = False
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for raw in text.splitlines(True):
        line = raw.rstrip("\n")
        if re.match(r"^primitives:\s*(\[\s*\])?\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        m = re.match(r"^  - (\w+):\s*(.*)$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {}
            cur[m.group(1)] = m.group(2).strip()
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    if cur is not None:
        entries.append(cur)
    return entries


def parse_translation(path):
    """Tailored line parser for translation.yaml's controlled format (its entry lists)."""
    section, entry = None, None
    out = {name: [] for name in TRANSLATION_SECTIONS}
    header = re.compile(r"^(%s):\s*$" % "|".join(TRANSLATION_SECTIONS))
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = header.match(line)
            if m:
                section = m.group(1)
                entry = None
                continue
            m = re.match(r"^  - ([a-z_]+):\s*(.*)$", line)
            if m and section:
                entry = {m.group(1): m.group(2).strip().strip('"')}
                out[section].append(entry)
                continue
            m = re.match(r"^    ([a-z_]+):\s*(.*)$", line)
            if m and entry is not None:
                entry[m.group(1)] = m.group(2).strip().strip('"')
    return out


def split_frontmatter(text):
    """Split a `---`-delimited frontmatter block into (dict, body); raises on a file without.

    A YAML block sequence (`tools:` then `  - Read` lines) folds into the same comma-joined
    string an inline `tools: Read, Bash` produces, so callers see one shape. Read as an empty
    scalar instead, it would hand the permission inversion a WRONG answer, not a missing one.
    """
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("agent file has no frontmatter block")
    fm, seq_key = {}, None
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            key, value = km.group(1), km.group(2).strip()
            fm[key] = value
            seq_key = None if value else key
            continue
        im = re.match(r"^\s+- (.*)$", line)
        if im and seq_key:
            item = im.group(1).strip()
            fm[seq_key] = f"{fm[seq_key]}, {item}" if fm[seq_key] else item
    return fm, m.group(2)


def tool_row(translation, name):
    """The tool_capabilities row covering `name`: exact `tool:` first, then a `prefix:` blanket."""
    for row in translation["tool_capabilities"]:
        if row.get("tool") == name:
            return row
    for row in translation["tool_capabilities"]:
        prefix = row.get("prefix")
        if prefix and name.startswith(prefix):
            return row
    return None


def check_matrix_completeness(agents_dir=None, translation_path=None):
    """Every agent frontmatter key, tool and model alias must be named by translation.yaml.

    decision-009 chose a completeness check over a version stamp as the drift catcher: a key
    or tool the matrix does not name would otherwise reach gen_opencode.py as a silent drop.
    """
    agents_dir = agents_dir or AGENTS
    translation_path = translation_path or TRANSLATION
    problems = []
    if not os.path.isfile(translation_path):
        return [f"translation matrix not on disk: {translation_path}"]
    tr = parse_translation(translation_path)

    for row in tr["tool_capabilities"]:
        name = row.get("tool") or row.get("prefix") or "<unnamed>"
        if row.get("capability") not in TOOL_CAPABILITIES:
            problems.append(
                f"translation.yaml: tool_capabilities row {name!r} has capability "
                f"{row.get('capability')!r} (must be one of {sorted(TOOL_CAPABILITIES)})")
    for row in tr["field_treatments"]:
        if row.get("treatment") == "map" and not row.get("opencode"):
            problems.append(
                f"translation.yaml: field_treatments row {row.get('field')!r} is "
                "`treatment: map` with no `opencode:` target key")
        if row.get("treatment") not in FIELD_TREATMENTS:
            problems.append(
                f"translation.yaml: field_treatments row {row.get('field')!r} has treatment "
                f"{row.get('treatment')!r} (must be one of {sorted(FIELD_TREATMENTS)})")

    treatments = {r["field"] for r in tr["field_treatments"] if "field" in r}
    aliases = {r["alias"] for r in tr["model_aliases"] if "alias" in r}
    if not os.path.isdir(agents_dir):
        return problems
    for fn in sorted(os.listdir(agents_dir)):
        if not fn.endswith(".md") or fn.lower() == "readme.md":
            continue
        with open(os.path.join(agents_dir, fn), encoding="utf-8") as fh:
            text = fh.read()
        try:
            fm, _ = split_frontmatter(text)
        except ValueError as exc:
            problems.append(f"[agents/{fn}] {exc}")
            continue
        for key in fm:
            if key not in treatments:
                problems.append(
                    f"[agents/{fn}] frontmatter key `{key}` has no translation.yaml "
                    "field_treatments row")
        for tool in (t.strip() for t in fm.get("tools", "").split(",")):
            if tool and tool_row(tr, tool) is None:
                problems.append(
                    f"[agents/{fn}] tool `{tool}` has no translation.yaml tool_capabilities "
                    "row (exact `tool:` or a declared `prefix:`)")
        model = fm.get("model", "").strip()
        if model and "/" not in model and model not in aliases:
            problems.append(
                f"[agents/{fn}] model `{model}` is neither provider-prefixed nor a "
                "translation.yaml model_aliases row")
    return problems


def disk_primitives():
    """Return the set of (type, source-relpath) present on disk."""
    found = set()
    sk = os.path.join(PC, "skills")
    if os.path.isdir(sk):
        for d in os.listdir(sk):
            if os.path.isdir(os.path.join(sk, d)) and not d.startswith("."):
                found.add(("skill", f"primitives-core/skills/{d}"))
    ag = os.path.join(PC, "agents")
    if os.path.isdir(ag):
        for f in os.listdir(ag):
            # agents/README.md documents the family (per-item README convention),
            # not a primitive — same exemption check_identity.py applies.
            if f.endswith(".md") and f.lower() != "readme.md":
                found.add(("agent", f"primitives-core/agents/{f}"))
    cm = os.path.join(PC, "commands")
    if os.path.isdir(cm):
        for f in os.listdir(cm):
            # commands are flat .md files like agents, so they share the family-README
            # convention and the same readme.md exemption (decision-010)
            if f.endswith(".md") and f.lower() != "readme.md":
                found.add(("command", f"primitives-core/commands/{f}"))
    # Ratified hook-dir layout: each hooks/<name>/ carrying a hook.py is one hook primitive
    # (source = the dir, like a skill). Must stay consistent with scripts/check_hook_layout.py,
    # which bans the old hooks-handlers/*.sh layout; a test guards the two against drifting.
    hk = os.path.join(PC, "hooks")
    if os.path.isdir(hk):
        for d in sorted(os.listdir(hk)):
            dp = os.path.join(hk, d)
            if (
                os.path.isdir(dp)
                and not d.startswith(".")
                and os.path.isfile(os.path.join(dp, "hook.py"))
            ):
                found.add(("hook", f"primitives-core/hooks/{d}"))
    mc = os.path.join(PC, "mcp")
    if os.path.isdir(mc):
        for f in os.listdir(mc):
            if f.endswith(
                ".json"
            ):  # neutral connection specs (README.md is not a primitive)
                found.add(("mcp", f"primitives-core/mcp/{f}"))
    return found


def check_entry_schema(e, problems):
    """Schema checks for one parsed roster entry (required fields, enums, provenance rule)."""
    eid = e.get("id", "<no-id>")
    for k in REQUIRED:
        if k not in e:
            problems.append(f"[{eid}] missing required field: {k}")
    t = e.get("type")
    if t not in TYPES:
        problems.append(f"[{eid}] bad type: {t!r}")
    if "origin" in e and e.get("origin") not in ORIGINS:
        problems.append(
            f"[{eid}] bad origin: {e.get('origin')!r} (must be one of {sorted(ORIGINS)})"
        )
    if "disposition" in e and e.get("disposition") not in DISPOSITIONS:
        problems.append(
            f"[{eid}] bad disposition: {e.get('disposition')!r} "
            f"(must be one of {sorted(DISPOSITIONS)})"
        )
    if "targets" in e:
        bad = [t2 for t2 in _list(e["targets"]) if t2 not in TARGETS]
        if bad:
            problems.append(
                f"[{eid}] unknown targets entry: {bad} (must be one of {sorted(TARGETS)})"
            )
    if "requires" in e:
        unknown = {
            r
            for r in _list(e["requires"])
            if r not in CAPABILITIES and not REQUIRES_DEP.match(r)
        }
        if unknown:
            problems.append(
                f"[{eid}] unknown requires entry: {sorted(unknown)} "
                f"(must be one of {sorted(CAPABILITIES)} or cli:<kebab> / env:<kebab>)"
            )
    if e.get("origin") in ("sourced", "vendored"):
        for k in ("upstream", "ref"):
            v = e.get(k, "").strip()
            if not v or v == "null":
                problems.append(
                    f"[{eid}] origin: {e.get('origin')} requires non-null `{k}`"
                )


def main():
    problems = []
    entries = parse_roster(ROSTER)
    if not entries:
        problems.append("roster has 0 primitives (or failed to parse)")

    rostered = set()
    for e in entries:
        eid = e.get("id", "<no-id>")
        check_entry_schema(e, problems)
        t = e.get("type")
        src = e.get("source", "")
        if src:
            if not os.path.exists(os.path.join(REPO, src)):
                problems.append(f"[{eid}] source not on disk: {src}")
            rostered.add((t, src))

    # disk -> roster (orphans on disk)
    on_disk = disk_primitives()
    for t, src in sorted(on_disk - rostered):
        problems.append(f"on disk but NOT in roster: ({t}) {src}")

    # roster -> disk for the file-backed types (orphans in roster)
    for t, src in sorted(
        {
            (e.get("type"), e.get("source"))
            for e in entries
            if e.get("type") in {"skill", "agent", "command", "hook", "mcp"}
        }
        - on_disk
    ):
        if src and os.path.exists(os.path.join(REPO, src)):
            continue  # exists but maybe normalized differently; existence already checked above
        problems.append(f"in roster but NOT on disk: ({t}) {src}")

    problems.extend(check_matrix_completeness())

    n = len(entries)
    counts = {}
    for e in entries:
        counts[e.get("type")] = counts.get(e.get("type"), 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))

    if problems:
        print(f"✗ roster<->disk / translation-matrix drift: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ roster<->disk clean, translation matrix complete — {n} primitives ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
