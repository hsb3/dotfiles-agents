#!/usr/bin/env python3
"""Provenance / externals conformance — D6 machine-floor check 3 (entry-gate spec).

Enforces the composition + provenance invariants of the rebuild (ADR 0015 / desk 0005·0007):

  1. `primitives-core` is self-authored ONLY. Every roster entry whose `source` lives under
     `primitives-core/` must be `origin: authored`. An `origin: sourced` body under
     `primitives-core/` is a third-party copy — the exact "wholesale passthrough" the
     composition principle forbids; sourced material is referenced in `externals.yaml`, never
     vendored into the source tree.
  2. Externals are by reference with recorded intent: every `externals.yaml` entry carries a
     non-null `upstream` + `ref`.

The `origin: sourced ⇒ non-null upstream+ref` roster rule is already enforced by
`check_roster.py`; this check owns the *placement* invariant (1) and the externals intent (2).

Externals-entry intent enforcement (2) was gated behind `ENFORCE_EXTERNALS_INTENT` while
D5/DEV-34 was pending Henry's J5 ruling (so `externals.yaml` didn't exist and couldn't carry
recorded intent yet). J5 ruled 2026-07-17 (decision 0019: keep 5, drop 26) and D5 populated
`externals.yaml` with those 5 entries, each with non-null `upstream` + `ref` — the flag is now
`True` and (2) blocks CI like (1) always has. Invariant (1) always blocks.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violation.
Usage: python3 scripts/check_provenance.py   (run from the repo root)
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import parse_roster  # noqa: E402

ROSTER = os.path.join(REPO, "primitives-core.yaml")
EXTERNALS = os.path.join(REPO, "externals.yaml")
PRIMITIVES_CORE_PREFIX = "primitives-core/"

# Activated at D5 (J5-ruled, decision 0019): externals.yaml now carries recorded intent for
# its 5 kept entries. The check blocks CI on missing/null upstream+ref like it always has for
# invariant (1).
ENFORCE_EXTERNALS_INTENT = True


def authored_placement_violations(roster):
    """(1) No `origin: sourced` body under primitives-core/ — self-authored only (ADR 0015)."""
    problems = []
    for e in roster:
        src = (e.get("source") or "").strip()
        if src.startswith(PRIMITIVES_CORE_PREFIX) and e.get("origin") == "sourced":
            problems.append(
                f"[{e.get('id', '<no-id>')}] origin: sourced but source is under "
                f"primitives-core/ ({src}) — third-party copy in the self-authored tree; "
                f"reference it in externals.yaml instead (ADR 0015 / composition principle)"
            )
    return problems


def parse_externals(path):
    """Parse externals.yaml's top-level list into dicts. Tolerant line parser (no pyyaml),
    mirroring the roster parser: entries begin `  - <key>: <v>`, continue `    <key>: <v>`."""
    if not os.path.isfile(path):
        return []
    entries, cur, in_list = [], None, False
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if re.match(r"^externals:\s*(\[\s*\])?\s*$", line):
                in_list = True
                continue
            if not in_list:
                continue
            m = re.match(r"^  - (\w[\w-]*):\s*(.*)$", line)
            if m:
                if cur is not None:
                    entries.append(cur)
                cur = {m.group(1): m.group(2).strip()}
                continue
            m = re.match(r"^    (\w[\w-]*):\s*(.*)$", line)
            if m and cur is not None:
                cur[m.group(1)] = m.group(2).strip()
    if cur is not None:
        entries.append(cur)
    return entries


def externals_intent_violations(entries):
    """(2) Every externals entry has non-null `upstream` + `ref` (recorded intent)."""
    problems = []
    for e in entries:
        eid = e.get("id", "<no-id>")
        for key in ("upstream", "ref"):
            v = (e.get(key) or "").strip()
            if not v or v in ("null", "~", "None"):
                problems.append(f"[external:{eid}] missing/null `{key}` (record intent or drop)")
    return problems


def main():
    roster = parse_roster(ROSTER)
    problems = authored_placement_violations(roster)

    externals = parse_externals(EXTERNALS)
    intent_problems = externals_intent_violations(externals)
    if ENFORCE_EXTERNALS_INTENT:
        problems.extend(intent_problems)
    elif externals:
        # Report-only while gated on D5/J5 — visible, not blocking.
        print(
            f"· externals conformance (report-only, gated on D5/J5): "
            f"{len(externals)} entries, {len(intent_problems)} with null intent"
        )

    if problems:
        print(f"✗ provenance/externals: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    n_pc = sum(1 for e in roster if (e.get("source") or "").startswith(PRIMITIVES_CORE_PREFIX))
    ext_state = f"{len(externals)} externals (intent enforcement {'ON' if ENFORCE_EXTERNALS_INTENT else 'gated on D5'})"
    print(f"✓ provenance clean — {n_pc} primitives-core bodies all authored; {ext_state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
