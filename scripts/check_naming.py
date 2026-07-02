#!/usr/bin/env python3
"""Naming-taxonomy lint (grammar source of truth: manifests/naming.md).

Enforces, over every roster entry (primitives-core.yaml) and every plugins.yaml bundle id:
  - skill / agent / mcp / plugin ids: kebab-case  (^[a-z0-9]+(-[a-z0-9]+)*$)
  - hook ids: <plugin>.<Event>.<slug> — <plugin> kebab AND matching the entry's owning
    plugin (its `plugins:` member and its hooks/<plugin>/ path segment); <Event> an exact
    harness event; <slug> kebab; handler filename == <id>.sh; and the plugin's
    hooks/<plugin>/hooks/hooks.json config must exist
  - no client token in any id
  - no vendor in any id: a non-null `vendor:` string must not appear in the id
    (token-boundary match); `-henry` is the sole sanctioned fork marker

Deliberately NOT linted: externals.yaml ids (sourced items keep their upstream identity).
There is no suppression mechanism by design — a violation is fixed by a recorded rename or
a corrected roster entry, never an exception.

Stdlib-only (reuses check_roster.parse_roster), so it runs in CI with zero install.
Exit 0 = clean; exit 1 = violations (one line per problem, grammar: manifests/naming.md).

Usage: python3 scripts/check_naming.py   (run from the repo root)
"""

import os
import re
import sys

from check_roster import _list, parse_roster

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(REPO, "primitives-core.yaml")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")
HOOKS_DIR = os.path.join(REPO, "primitives-core", "hooks")

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Harness event list — pinned to manifests/naming.md (canonical). The workbench keeps its
# own copy (dotfiles-agents-workbench/scripts/promote_check.py EVENTS); tests guard drift.
EVENTS = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "UserPromptSubmit",
    "SubagentStop",
    "Notification",
    "PreCompact",
    "SessionEnd",
)

# Same token list as dotfiles-agents-workbench/scripts/promote_check.py CLIENT_TOKENS.
CLIENT_TOKENS = (
    "functionform",
    "ra-platform",
    "ra-labs",
    "raptorxai",
    "raptorgpt",
    "headcase",
)

HOOK_ID = re.compile(r"^(?P<plugin>[^.]+)\.(?P<event>[^.]+)\.(?P<slug>[^.]+)$")

# Per-kind pattern hints for messages (manifests/naming.md "Patterns" table).
PATTERNS = {
    "skill": "<domain>-<capability>",
    "agent": "<domain>-<role>[-<verb>]",
    "mcp": "<service>",
    "plugin": "<domain>-<function>",
    "hook": "<plugin>.<Event>.<slug>",
}


def _vendor_in_id(vendor, eid):
    """Token-boundary match of `vendor` inside `eid` (segments split on - and .).

    Boundary, not substring: vendor `go` must NOT flag `django-helper`.
    """
    return re.search(rf"(^|[-.]){re.escape(vendor)}([-.]|$)", eid) is not None


def check_common(eid, vendor, problems):
    """Client-token and vendor-in-name rules, common to every kind."""
    for tok in CLIENT_TOKENS:
        if tok in eid.lower():
            problems.append(
                f"[{eid}] id encodes client token `{tok}` — rename "
                f"(client names never appear in ids)"
            )
    vendor = (vendor or "").strip()
    if vendor and vendor != "null" and _vendor_in_id(vendor.lower(), eid.lower()):
        problems.append(
            f"[{eid}] id encodes its vendor `{vendor}` — vendor lives in the roster, "
            f"not the name (`-henry` is the sole sanctioned fork marker)"
        )


def check_hook_id(e, problems):
    """The hook grammar: id <plugin>.<Event>.<slug>, path + plugins membership + filename."""
    eid = e.get("id", "<no-id>")
    m = HOOK_ID.match(eid)
    if not m:
        problems.append(
            f"[{eid}] hook id not `<plugin>.<Event>.<slug>` (pattern: {PATTERNS['hook']})"
        )
        return
    plugin, event, slug = m.group("plugin"), m.group("event"), m.group("slug")
    if not KEBAB.match(plugin):
        problems.append(
            f"[{eid}] hook plugin segment `{plugin}` not kebab-case "
            f"(pattern: {PATTERNS['hook']})"
        )
    if event not in EVENTS:
        problems.append(
            f"[{eid}] hook event `{event}` not a harness event "
            f"(exact PascalCase, one of: {', '.join(EVENTS)})"
        )
    if not KEBAB.match(slug):
        problems.append(
            f"[{eid}] hook slug `{slug}` not kebab-case (pattern: {PATTERNS['hook']})"
        )
    plugins = _list(e.get("plugins", "[]"))
    if plugin not in plugins:
        problems.append(
            f"[{eid}] hook plugin segment `{plugin}` not among the entry's "
            f"plugins {plugins}"
        )
    src = e.get("source", "")
    if src and f"primitives-core/hooks/{plugin}/" not in src:
        problems.append(
            f"[{eid}] hook plugin segment `{plugin}` does not match its "
            f"hooks/<plugin>/ path segment: {src}"
        )
    if src and os.path.basename(src) != f"{eid}.sh":
        problems.append(
            f"[{eid}] hook handler filename must be `{eid}.sh`, "
            f"got `{os.path.basename(src)}`"
        )


def check_entry_naming(e, problems):
    """Naming checks for one parsed roster entry."""
    eid = e.get("id", "<no-id>")
    kind = e.get("type", "")
    if kind == "hook":
        check_hook_id(e, problems)
    else:
        if not KEBAB.match(eid):
            problems.append(
                f"[{eid}] {kind or 'primitive'} id not kebab-case "
                f"(pattern: {PATTERNS.get(kind, '<kebab-case>')})"
            )
    check_common(eid, e.get("vendor"), problems)


def check_hooks_layout(hooks_dir, problems):
    """Every hook plugin dir on disk must carry its hooks/hooks.json config."""
    if not os.path.isdir(hooks_dir):
        return
    for d in sorted(os.listdir(hooks_dir)):
        if d.startswith(".") or not os.path.isdir(os.path.join(hooks_dir, d)):
            continue
        cfg = os.path.join(hooks_dir, d, "hooks", "hooks.json")
        if not os.path.isfile(cfg):
            problems.append(
                f"[{d}] hook plugin missing config: "
                f"primitives-core/hooks/{d}/hooks/hooks.json"
            )


def parse_bundle_ids(path):
    """Bundle ids from plugins.yaml (`  - id: <v>` lines)."""
    ids = []
    if not os.path.isfile(path):
        return ids
    for raw in open(path, encoding="utf-8"):
        m = re.match(r"^  - id:\s*(\S+)\s*$", raw)
        if m:
            ids.append(m.group(1))
    return ids


def check_bundle_id(pid, problems):
    """plugins.yaml bundle ids: kebab, no client token (vendor n/a on bundles)."""
    if not KEBAB.match(pid):
        problems.append(
            f"[{pid}] plugin id not kebab-case (pattern: {PATTERNS['plugin']})"
        )
    check_common(pid, None, problems)


def main():
    problems = []
    entries = parse_roster(ROSTER)
    if not entries:
        problems.append("roster has 0 primitives (or failed to parse)")
    for e in entries:
        check_entry_naming(e, problems)
    check_hooks_layout(HOOKS_DIR, problems)
    bundle_ids = parse_bundle_ids(PLUGINS_YAML)
    if not bundle_ids:
        problems.append("plugins.yaml has 0 bundle ids (or failed to parse)")
    for pid in bundle_ids:
        check_bundle_id(pid, problems)

    if problems:
        print(
            f"✗ naming-taxonomy violations: {len(problems)} problem(s) "
            f"— grammar: manifests/naming.md"
        )
        for p in problems:
            print(f"  - {p}")
        return 1
    counts = {}
    for e in entries:
        counts[e.get("type")] = counts.get(e.get("type"), 0) + 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(
        f"✓ naming clean — {len(entries)} roster ids ({summary}) "
        f"+ {len(bundle_ids)} plugin ids (grammar: manifests/naming.md)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
