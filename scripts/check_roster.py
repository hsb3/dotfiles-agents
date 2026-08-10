#!/usr/bin/env python3
"""Roster <-> disk drift guard (issue #5).

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

TYPES = {"skill", "agent", "command", "mcp", "hook"}
# The runtime enum (ADR 0017): claude-code installs the symlink assemblies natively;
# opencode is generated at install time by gen_opencode.py (task-4).
TARGETS = {"claude-code", "opencode"}
ORIGINS = {"authored", "sourced", "vendored"}
DISPOSITIONS = {"qualified", "grandfathered-pending-use", "demoted", "untriaged", "orphaned"}
CAPABILITIES = {"hooks", "local-mcp", "hosted-mcp"}
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

    n = len(entries)
    counts = {}
    for e in entries:
        counts[e.get("type")] = counts.get(e.get("type"), 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))

    if problems:
        print(f"✗ roster<->disk drift: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ roster<->disk clean — {n} primitives ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
