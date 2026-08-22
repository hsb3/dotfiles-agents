#!/usr/bin/env python3
"""Manifest conformance gate — the first-party validator, run over every manifest we ship.

`claude plugin validate <path> --strict` is Claude Code's own manifest checker. `--strict`
turns its warnings into a non-zero exit, catching what the runtime tolerates silently:
unrecognized fields, missing attribution metadata, and shape problems that load fine and
then behave surprisingly. It knows the real schema, which is exactly the knowledge this
repo should not be re-deriving in Python — a hand-rolled copy drifts the moment the CLI
learns a field.

MEASURED 2026-08-22, and the reason this gate is worth having:
  - `changelog` is NOT a recognized field. The validator warns "Claude Code ignores
    unrecognized fields at load time, so it's safe to keep" — safe, and inert. Without
    --strict that warning is invisible and a manifest can carry a field nobody reads.
  - A manifest with no `author` warns rather than fails.
  - All eight plugins and the marketplace exit 0 today, so this gate lands green and stays
    that way only while the manifests stay clean.

The subject list is DERIVED from `plugins/*/` on disk, never from a recorded inventory —
same rule as every other guard here. A plugin dir with no `.claude-plugin/plugin.json` is
reported rather than skipped, since that is a broken assembly, not a non-subject.

NOT in `make ci`. `make ci` is offline and zero-install by design, and this needs the
`claude` binary. It rides the `drift guards` CI job for the same reason
`check_version_bump.py` and `check_vendored_drift.py` do — dev's branch protection pins
required checks by job NAME, so a new gate joins an existing job rather than adding one.

A MISSING `claude` BINARY IS A FAILURE, NOT A SKIP. A gate that quietly does nothing when
its tool is absent reports green forever and teaches everyone the check is running. If the
binary is genuinely unavailable somewhere, turn this gate off explicitly there.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_manifests.py [--verbose]   (run from anywhere)
"""

import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(REPO, "plugins")
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")

# Per-invocation ceiling. The validator is a local process on a small JSON file; anything
# near this means it is hung or waiting on input, and a hung gate is worse than a red one.
TIMEOUT_SECONDS = 60


def subjects():
    """Return [(label, path)] to validate — the marketplace, then every plugin assembly.

    Derived from disk, never from a list. Sorted so output is stable across machines.
    """
    out = [("marketplace", REPO)]
    if not os.path.isdir(PLUGINS_DIR):
        return out
    for name in sorted(os.listdir(PLUGINS_DIR)):
        path = os.path.join(PLUGINS_DIR, name)
        if name.startswith(".") or not os.path.isdir(path):
            continue
        out.append((name, path))
    return out


def validate(path):
    """Run the validator on one path. Return (ok, combined_output)."""
    try:
        proc = subprocess.run(
            ["claude", "plugin", "validate", path, "--strict"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=REPO,
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {TIMEOUT_SECONDS}s"
    except OSError as exc:  # binary vanished between the check and the call
        return False, f"could not execute the validator: {exc}"
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def main():
    verbose = "--verbose" in sys.argv

    if shutil.which("claude") is None:
        print(
            "✗ manifest gate cannot run — the `claude` binary is not on PATH.\n"
            "  This is a failure, not a skip: a gate that silently does nothing when its\n"
            "  tool is missing reports green forever. Install the Claude Code CLI, or turn\n"
            "  this gate off explicitly where it cannot run.",
            file=sys.stderr,
        )
        return 1

    if not os.path.isfile(MARKETPLACE):
        print(f"✗ {os.path.relpath(MARKETPLACE, REPO)}: missing — nothing to validate", file=sys.stderr)
        return 1

    problems = []
    checked = 0
    for label, path in subjects():
        rel = os.path.relpath(path, REPO) or "."
        if label != "marketplace":
            manifest = os.path.join(path, ".claude-plugin", "plugin.json")
            if not os.path.isfile(manifest):
                problems.append(f"{rel}: no .claude-plugin/plugin.json — broken assembly")
                continue
        ok, output = validate(path)
        checked += 1
        if not ok:
            detail = output or "validator exited non-zero with no output"
            problems.append(f"{rel}: --strict failed\n    " + detail.replace("\n", "\n    "))
        elif verbose:
            print(f"  ✓ {rel}")

    if problems:
        print(f"✗ manifest gate: {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        f"✓ manifests clean — {checked} manifest(s) pass `claude plugin validate --strict` "
        "(marketplace + every plugin assembly, derived from disk)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
