#!/usr/bin/env python3
"""Primitive CONTENT validation (issue #22, deliverable B).

The drift guards prove consistency (roster matches disk, committed targets match a rebuild) but
never look INSIDE a primitive. This guard does: it validates that each source primitive is
well-formed before the build ever renders it, plus the roster cross-checks check_roster.py omits.

What it checks:
  - skill : SKILL.md at the source root with frontmatter `name` + `description`
  - agent : the .md has frontmatter with `name` + `description`
  - mcp   : the spec JSON has `name` and `transport` in {stdio, http}; stdio => `command`,
            http => `url`; any secret-named env/header value is a ${VAR} placeholder, not a literal
  - roster: `origin` in {authored, sourced}, `targets` subset of the real targets, `summary` set
  - externals mcp specs (externals.yaml kind: mcp) get the same mcp-spec checks

Stdlib-only (reuses translate.py's parsers), so `make ci` stays zero-install. Exit 0 = clean;
exit 1 = problems (prints every one). `--json` emits the findings as JSON.

Usage: python3 scripts/validate_primitives.py [--json]   (run from the repo root)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate as T  # reuse the roster/externals parsers + REPO root

VALID_TARGETS = {"claude-code", "opencode", "claude-agents"}
VALID_ORIGIN = {"authored", "sourced"}
VALID_TRANSPORT = {"stdio", "http"}
SECRET_HINT = re.compile(r"(token|secret|key|password|passwd|pat|credential)", re.I)
PLACEHOLDER = re.compile(r"^\$\{[^}]+\}$")


def frontmatter_keys(text):
    """Return the set of top-level frontmatter keys in a `---` block (best-effort, stdlib)."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return set()
    return {
        km.group(1)
        for ln in m.group(1).split("\n")
        if (km := re.match(r"^([\w-]+):", ln))
    }


def check_secret_values(mapping, label, problems):
    """Any secret-named env/header value must be a ${VAR} placeholder, never a literal."""
    for k, v in (mapping or {}).items():
        if (
            SECRET_HINT.search(k)
            and isinstance(v, str)
            and v
            and not PLACEHOLDER.match(v)
        ):
            problems.append(
                f"[{label}] secret-looking value for {k!r} is a literal, not a ${{VAR}} placeholder"
            )


def validate_mcp_spec(spec_path, label, problems):
    full = os.path.join(T.REPO, spec_path)
    if not os.path.isfile(full):
        problems.append(f"[{label}] mcp spec not found: {spec_path}")
        return
    try:
        spec = json.load(open(full, encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        problems.append(f"[{label}] mcp spec is not valid JSON: {e}")
        return
    if not spec.get("name"):
        problems.append(f"[{label}] mcp spec missing `name`")
    transport = spec.get("transport")
    if transport not in VALID_TRANSPORT:
        problems.append(
            f"[{label}] mcp spec `transport` must be one of {sorted(VALID_TRANSPORT)}, got {transport!r}"
        )
    if transport == "stdio" and not spec.get("command"):
        problems.append(f"[{label}] stdio mcp spec missing `command`")
    if transport == "http" and not spec.get("url"):
        problems.append(f"[{label}] http mcp spec missing `url`")
    check_secret_values(spec.get("env"), label, problems)
    check_secret_values(spec.get("headers"), label, problems)


def validate_entry(e, problems):
    eid, t, src = e.get("id", "<no-id>"), e.get("type"), e.get("source", "")
    # roster cross-checks check_roster.py does not do
    if e.get("origin") not in VALID_ORIGIN:
        problems.append(
            f"[{eid}] `origin` must be one of {sorted(VALID_ORIGIN)}, got {e.get('origin')!r}"
        )
    bad_targets = set(e.get("targets", [])) - VALID_TARGETS
    if bad_targets:
        problems.append(f"[{eid}] unknown target(s): {sorted(bad_targets)}")
    if not e.get("summary", "").strip():
        problems.append(f"[{eid}] empty `summary`")
    # per-type content checks
    full = os.path.join(T.REPO, src)
    if t == "skill":
        skill_md = os.path.join(full, "SKILL.md")
        if not os.path.isfile(skill_md):
            problems.append(f"[{eid}] skill missing SKILL.md at root")
        else:
            keys = frontmatter_keys(open(skill_md, encoding="utf-8").read())
            for need in ("name", "description"):
                if need not in keys:
                    problems.append(f"[{eid}] SKILL.md frontmatter missing `{need}`")
    elif t == "agent":
        if os.path.isfile(full):
            keys = frontmatter_keys(open(full, encoding="utf-8").read())
            for need in ("name", "description"):
                if need not in keys:
                    problems.append(f"[{eid}] agent frontmatter missing `{need}`")
    elif t == "mcp":
        validate_mcp_spec(src, eid, problems)


def main():
    as_json = "--json" in sys.argv
    problems = []
    roster = T.parse_roster(T.ROSTER)
    for e in roster:
        validate_entry(e, problems)
    # externals kind: mcp specs
    for ext in T.parse_externals(T.EXTERNALS):
        if ext.get("kind") == "mcp":
            validate_mcp_spec(
                ext.get("spec", ""), f"external:{ext.get('id')}", problems
            )

    if as_json:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
        return 1 if problems else 0
    if problems:
        print(f"✗ primitive validation: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    n_mcp = sum(1 for e in roster if e.get("type") == "mcp")
    print(
        f"✓ primitives valid — {len(roster)} entries content-checked ({n_mcp} mcp specs + externals)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
