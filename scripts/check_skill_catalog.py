#!/usr/bin/env python3
"""Standalone skill-catalog eligibility + drift guard (issue #115).

Verifies that skill-catalog.yaml — the set of skills cleared to ship *standalone* (installed
one at a time, without a whole plugin bundle) — stays honest against the roster
(primitives-core.yaml) and the skill folders on disk. It is a projection over the roster, so
this guard catches both drift (a catalog id that no longer resolves, or whose provenance no
longer matches) and eligibility regressions (a skill that gained an `agents/` folder, an MCP
requirement, or a sibling dependency after it was catalogued).

Eligibility — a catalogued skill must satisfy ALL of:
  1. resolves to a roster entry with type: skill and origin: authored.
  2. roster `requires` (if any) contains none of local-mcp / hosted-mcp / hooks — a
     standalone install carries only the skill body; it cannot provision an MCP server or a
     hook. cli:/env: deps are advisory (surfaced by the installer), not disqualifying (#79).
  3. the skill folder contains no `agents/` subdir (a bundled companion agent means the skill
     is not self-contained — e.g. nanobanana ships agents/openai.yaml → out).
  4. no sibling-skill coupling: `depends_on_skills` is declared empty AND a heuristic finds no
     path/wikilink reference to ANOTHER roster skill id inside the folder (a bare topic
     mention does not trip it — only `skills/<id>`, `.../<id>/…`, or `[[<id>]]`).
  5. every relative markdown link inside the folder resolves to a file INSIDE the folder — no
     `../` escape, no dangling target. Proves the body is self-contained.
  6. every entry in `clients` is one of the roster entry's targets[] (per-client compat).

Drift / invariants:
  - catalog `provenance` equals the roster `origin` for the id.
  - `standalone` is true; `depends_on_skills` is empty (rule 4 restated as a hard field check).
  - namespacing: the standalone plugin name is the skill id (plugin name == id); it must not
    clash with any bundle id in plugins.yaml (a `/plugin install <id>@dotfiles-agents` would
    otherwise be ambiguous between the standalone plugin and a bundle).

Stdlib-only (a tailored line parser for the controlled catalog format, and it reuses
check_roster.parse_roster), so it runs in CI with zero install. Exit 0 = clean; exit 1 =
problems (one line each).

Usage: python3 scripts/check_skill_catalog.py   (run from the repo root)
"""

import os
import re
import sys

from check_roster import _list, parse_roster

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(REPO, "primitives-core.yaml")
CATALOG = os.path.join(REPO, "skill-catalog.yaml")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")

# Capability words that make a skill non-standalone: it would need to provision a runtime
# surface the bare skill body cannot carry. cli:/env: deps are intentionally NOT here.
DISQUALIFYING_REQUIRES = {"local-mcp", "hosted-mcp", "hooks"}
REQUIRED_FIELDS = ("id", "standalone", "clients", "depends_on_skills", "provenance")
KNOWN_CLIENTS = {"claude-code", "opencode"}
MD_LINK = re.compile(r"\]\(([^)]+)\)")


def _read(path):
    """Read a file as text, tolerating undecodable bytes (scans never need exact bytes)."""
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def parse_catalog(path):
    """Parse skill-catalog.yaml's `skills:` list into dicts (mirrors the roster parser's
    controlled format: `  - id: <v>` then `    <key>: <v>`; inline `[a, b]` lists via _list)."""
    entries, cur, in_list = [], None, False
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for raw in text.splitlines(True):
        line = raw.rstrip("\n")
        if re.match(r"^skills:\s*(\[\s*\])?\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        m = re.match(r"^  - (\w+):\s*(.*)$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {m.group(1): m.group(2).strip()}
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    if cur is not None:
        entries.append(cur)
    for e in entries:
        e["clients"] = _list(e.get("clients", ""))
        e["depends_on_skills"] = _list(e.get("depends_on_skills", ""))
        e["prerequisites"] = _list(e.get("prerequisites", ""))
    return entries


def _text_files(folder):
    """Every non-binary-ish file under a skill folder (walked for the reference scans)."""
    out = []
    for dp, _d, files in os.walk(folder):
        for f in files:
            if f == ".DS_Store":
                continue
            out.append(os.path.join(dp, f))
    return out


def sibling_reference(folder, this_id, other_ids):
    """Return the first (other-id, evidence) pair where the folder references ANOTHER skill id
    as a path or wikilink, else None. Path/wikilink form only — a bare topic mention of the
    word does not count (that is why opencode-expertise discussing 'MCP' or 'skills' is fine)."""
    for path in _text_files(folder):
        try:
            text = _read(path)
        except OSError:
            continue
        for oid in other_ids:
            if oid == this_id:
                continue
            for pat in (rf"skills/{re.escape(oid)}\b", rf"\[\[{re.escape(oid)}\]\]"):
                if re.search(pat, text):
                    return (oid, os.path.relpath(path, folder))
    return None


def unresolved_markdown_links(folder):
    """Return a list of (file, target) for every relative markdown link that escapes the
    folder or dangles. Links are resolved relative to the file that CONTAINS them (a link in
    references/a.md to `b.md` means references/b.md). External / anchor / absolute targets are
    skipped — only in-repo relative file references are load-bearing for self-containment."""
    problems = []
    root = os.path.realpath(folder)
    for path in _text_files(folder):
        if not path.endswith(".md"):
            continue
        try:
            text = _read(path)
        except OSError:
            continue
        for target in MD_LINK.findall(text):
            t = target.strip()
            if not t or t.startswith(("http://", "https://", "#", "mailto:", "/")):
                continue
            t = t.split("#", 1)[0].split("?", 1)[0]  # drop anchor / query
            if not t:
                continue
            resolved = os.path.realpath(os.path.join(os.path.dirname(path), t))
            rel = os.path.relpath(path, folder)
            if os.path.commonpath([root, resolved]) != root:
                problems.append((rel, target, "escapes the skill folder"))
            elif not os.path.exists(resolved):
                problems.append((rel, target, "target does not exist"))
    return problems


def parse_bundle_ids(path):
    """Bundle ids from plugins.yaml (reused shape from check_naming.parse_bundle_ids)."""
    ids = []
    if not os.path.isfile(path):
        return ids
    with open(path, encoding="utf-8") as fh:
        for raw in fh.read().splitlines(True):
            m = re.match(r"^  - id:\s*(\S+)\s*$", raw)
            if m:
                ids.append(m.group(1))
    return ids


def check_entry(entry, roster_by_id, all_skill_ids, bundle_ids, problems):
    """Full eligibility + drift + namespacing check for one catalog entry."""
    cid = entry.get("id", "<no-id>")
    for k in REQUIRED_FIELDS:
        if k not in entry:
            problems.append(f"[{cid}] missing required catalog field: {k}")
    if entry.get("standalone") != "true":
        problems.append(
            f"[{cid}] standalone must be `true` (got {entry.get('standalone')!r})"
        )
    if entry.get("depends_on_skills"):
        problems.append(
            f"[{cid}] depends_on_skills must be empty — sibling-skill coupling disqualifies "
            f"a standalone skill (got {entry['depends_on_skills']})"
        )
    for c in entry.get("clients", []):
        if c not in KNOWN_CLIENTS:
            problems.append(
                f"[{cid}] unknown client `{c}` (must be one of {sorted(KNOWN_CLIENTS)})"
            )

    r = roster_by_id.get(cid)
    if r is None:
        problems.append(
            f"[{cid}] catalog id has no roster entry (catalog<->roster drift)"
        )
        return
    # 1. type + origin
    if r.get("type") != "skill":
        problems.append(f"[{cid}] roster type is {r.get('type')!r}, not skill")
    if r.get("origin") != "authored":
        problems.append(
            f"[{cid}] not standalone-eligible: roster origin is {r.get('origin')!r}, not authored"
        )
    # provenance drift
    if entry.get("provenance") != r.get("origin"):
        problems.append(
            f"[{cid}] provenance {entry.get('provenance')!r} != roster origin {r.get('origin')!r} (drift)"
        )
    # 2. requires excludes MCP/hooks
    bad = DISQUALIFYING_REQUIRES & set(_list(r.get("requires", "")))
    if bad:
        problems.append(
            f"[{cid}] not standalone-eligible: roster `requires` includes {sorted(bad)} "
            f"(a standalone install cannot provision {sorted(bad)})"
        )
    # 6. clients subset of roster targets
    for c in entry.get("clients", []):
        if c not in r.get("targets", []):
            problems.append(
                f"[{cid}] client `{c}` not in roster targets {r.get('targets')}"
            )

    folder = os.path.join(REPO, r.get("source", ""))
    if not os.path.isdir(folder):
        problems.append(f"[{cid}] roster source folder missing: {r.get('source')}")
        return
    # 3. no bundled agent
    if os.path.isdir(os.path.join(folder, "agents")):
        problems.append(
            f"[{cid}] not standalone-eligible: folder ships an agents/ subdir (bundled companion agent)"
        )
    # 4. sibling-skill reference heuristic
    sib = sibling_reference(folder, cid, all_skill_ids)
    if sib:
        problems.append(
            f"[{cid}] references sibling skill `{sib[0]}` (in {sib[1]}) — sibling coupling disqualifies standalone"
        )
    # 5. markdown links resolve in-folder
    for rel, target, why in unresolved_markdown_links(folder):
        problems.append(f"[{cid}] markdown link `{target}` in {rel} {why}")
    # namespacing invariant
    if cid in bundle_ids:
        problems.append(
            f"[{cid}] standalone plugin name clashes with bundle id `{cid}` in plugins.yaml "
            f"(plugin name == skill id must be unambiguous)"
        )


def run_checks():
    """Return (problems, n_catalog) — the guard's result without printing (importable by tests)."""
    problems = []
    roster = parse_roster(ROSTER)
    roster_by_id = {e.get("id"): e for e in roster}
    all_skill_ids = {e.get("id") for e in roster if e.get("type") == "skill"}
    bundle_ids = set(parse_bundle_ids(PLUGINS_YAML))
    catalog = parse_catalog(CATALOG)
    if not catalog:
        problems.append("skill-catalog.yaml has 0 skills (or failed to parse)")
    seen = set()
    for entry in catalog:
        cid = entry.get("id", "<no-id>")
        if cid in seen:
            problems.append(f"[{cid}] duplicate catalog entry")
        seen.add(cid)
        check_entry(entry, roster_by_id, all_skill_ids, bundle_ids, problems)
    return problems, len(catalog)


def main():
    problems, n = run_checks()
    if problems:
        print(f"✗ skill-catalog: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"✓ skill-catalog clean — {n} standalone skills, eligibility + drift + namespacing OK"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
