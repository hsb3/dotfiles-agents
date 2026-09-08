"""Every bundled Python CLI answers `--help` without touching the world.

A skill's scripts are invoked by a model that has only the SKILL.md prose to go on.
`--help` is the one call it can make to check its own understanding, so a script whose
`--help` shells out to `gh`, exits 1 on an "unknown arg", or prints nothing is worse
than one with no help at all: the model reads the failure as "wrong script" and
abandons a working tool.

The file list is DERIVED, never hand-maintained -- every `.py` under a skill's
`scripts/` that carries a `__main__` guard is an entry point and is covered. Adding a
script opts it in automatically; a library module (no guard) is skipped, since importing
one is not a user-facing contract. Vendored `base/` trees are outside the pattern on
purpose: they are third-party and not ours to fix.

Each script runs from a scratch cwd (so nothing resolves a real repo) with HOME and
XDG_DATA_HOME redirected and every GH_/GITHUB_ variable removed, so a pass means
the help text came out of the script itself and not out of the host's credentials.
"""

import glob
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERN = os.path.join(ROOT, "primitives-core", "skills", "*", "scripts", "**", "*.py")

# A script that blocks on stdin or the network is a failure, not a reason to hang CI.
TIMEOUT_SECONDS = 60


def entry_points() -> list[str]:
    """Every bundled script with a `__main__` guard, sorted, repo-relative."""
    found = []
    for path in glob.glob(PATTERN, recursive=True):
        if "__pycache__" in path:
            continue
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        if '__name__ == "__main__"' in source or "__name__ == '__main__'" in source:
            found.append(os.path.relpath(path, ROOT))
    return sorted(found)


def scrubbed_env(home: str, data_home: str) -> dict:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GH_", "GITHUB_"))
    }
    env["HOME"] = home
    env["XDG_DATA_HOME"] = data_home
    return env


def run_help(rel_path: str, flag: str = "--help") -> subprocess.CompletedProcess:
    """Run one script's help from a world with nothing in it."""
    with tempfile.TemporaryDirectory() as sandbox:
        cwd = os.path.join(sandbox, "cwd")
        home = os.path.join(sandbox, "home")
        data_home = os.path.join(sandbox, "data")
        for path in (cwd, home, data_home):
            os.mkdir(path)
        return subprocess.run(
            [sys.executable, os.path.join(ROOT, rel_path), flag],
            cwd=cwd,
            env=scrubbed_env(home, data_home),
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )


class BundledScriptHelp(unittest.TestCase):
    def test_the_pattern_finds_scripts_at_all(self):
        """A broken glob would make every other assertion below vacuously true."""
        found = entry_points()
        self.assertGreater(len(found), 10, f"suspiciously few entry points: {found}")

    def test_every_entry_point_answers_help(self):
        failures = []
        for rel_path in entry_points():
            try:
                result = run_help(rel_path)
            except subprocess.TimeoutExpired:
                failures.append(f"{rel_path}: timed out after {TIMEOUT_SECONDS}s")
                continue
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip().splitlines()
                failures.append(
                    f"{rel_path}: exit {result.returncode}"
                    f" -- {detail[-1] if detail else '(no output)'}"
                )
            elif not result.stdout.strip():
                failures.append(f"{rel_path}: exit 0 but printed no usage on stdout")
        self.assertEqual(
            [], failures, "scripts whose --help does not work:\n  " + "\n  ".join(failures)
        )


if __name__ == "__main__":
    unittest.main()
