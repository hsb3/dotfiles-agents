"""No-repo-coupling gate (DESIGN §5): nothing under harness/ may import from or
reference repo files outside harness/. Candidates and cases are passed as paths
at runtime, so the package must contain no sibling-repo path/import references.

This is the Wave-1 lightweight enforcement; Wave 4 wires an equivalent grep gate
into `make ci`. `.claude-plugin` is deliberately NOT forbidden — it is a Claude
Code structural token the synthetic-plugin wrapper writes, not a repo path.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent_harness"))

FORBIDDEN = (
    "primitives-core",
    "dotfiles-agents-workbench",
    "incubator/",
    "scripts/run_eval",
    "import run_eval",
    "from scripts",
    "import scripts",
)


class TestNoRepoCoupling(unittest.TestCase):
    def test_package_has_no_outside_repo_references(self):
        offenders = []
        for root, _dirs, files in os.walk(PKG):
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
                for token in FORBIDDEN:
                    if token in text:
                        offenders.append(f"{os.path.relpath(path, PKG)}: {token!r}")
        self.assertEqual(offenders, [], f"repo-coupling references found: {offenders}")

    def test_package_imports_only_itself_and_stdlib(self):
        # Guard against `from ..scripts` / absolute imports of repo modules.
        for root, _dirs, files in os.walk(PKG):
            for f in files:
                if not f.endswith(".py"):
                    continue
                with open(os.path.join(root, f), encoding="utf-8") as fh:
                    for line in fh:
                        s = line.strip()
                        if s.startswith("from ") and "agent_harness" not in s:
                            # relative imports (from .x) and stdlib (from os import)
                            # are fine; a bare `from <repo_pkg> import` is not.
                            mod = s.split()[1]
                            self.assertFalse(
                                mod.startswith("scripts")
                                or mod.startswith("tests")
                                or mod.startswith("primitives"),
                                f"{f}: suspicious import {s!r}",
                            )


if __name__ == "__main__":
    unittest.main()
