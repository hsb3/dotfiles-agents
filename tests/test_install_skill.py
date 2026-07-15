"""Tests over the opencode standalone installer, scripts/install-skill (issue #115).

Every install/uninstall runs against a tmpdir via --dir — NEVER ~/.agents or ~/.claude. The
installer has no .py extension, so it is imported from its file path. Stdlib-only.

Covers the happy path (byte-identical copy, idempotent --force update, uninstall), --list, and
every rejection path (unknown / ineligible / incompatible) with its distinct exit + message.
"""

import filecmp
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from importlib.machinery import SourceFileLoader

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS)
import check_skill_catalog as C  # noqa: E402

# scripts/install-skill has no .py extension (it is an executable CLI) — load it by path.
_loader = SourceFileLoader("install_skill", os.path.join(SCRIPTS, "install-skill"))
_spec = importlib.util.spec_from_loader(_loader.name, _loader)
install_skill = importlib.util.module_from_spec(_spec)
_loader.exec_module(install_skill)

REPO = install_skill.REPO


def _run(argv):
    """Run the installer's main() with argv, capturing (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = install_skill.main(argv)
    return code, out.getvalue(), err.getvalue()


def _identical(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(
        _identical(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs
    )


class HappyPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True)
        )

    def test_install_is_byte_identical_to_source(self):
        code, _o, _e = _run(["carbon-builder", "--dir", self.tmp])
        self.assertEqual(code, 0)
        dest = os.path.join(self.tmp, "carbon-builder")
        src = os.path.join(REPO, "primitives-core", "skills", "carbon-builder")
        self.assertTrue(os.path.isdir(dest))
        self.assertTrue(
            _identical(src, dest), "installed skill must be byte-identical to source"
        )

    def test_reinstall_needs_force(self):
        _run(["carbon-builder", "--dir", self.tmp])
        code, _o, err = _run(["carbon-builder", "--dir", self.tmp])
        self.assertEqual(code, 1)
        self.assertIn("--force", err)

    def test_force_updates_in_place(self):
        _run(["carbon-builder", "--dir", self.tmp])
        code, out, _e = _run(["carbon-builder", "--dir", self.tmp, "--force"])
        self.assertEqual(code, 0)
        self.assertIn("installed", out)

    def test_uninstall_removes_only_that_folder(self):
        _run(["carbon-builder", "--dir", self.tmp])
        _run(["notion-api", "--dir", self.tmp])
        code, out, _e = _run(["carbon-builder", "--dir", self.tmp, "--uninstall"])
        self.assertEqual(code, 0)
        self.assertIn("uninstalled", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "carbon-builder")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "notion-api")))

    def test_uninstall_missing_is_noop(self):
        code, out, _e = _run(["carbon-builder", "--dir", self.tmp, "--uninstall"])
        self.assertEqual(code, 0)
        self.assertIn("nothing to remove", out)

    def test_uninstall_rejects_path_traversal_name(self):
        # An unvalidated `--uninstall` name must NOT reach shutil.rmtree. Put a sentinel dir
        # OUTSIDE the --dir base, then aim a `../`-bearing name at it: dest would resolve to
        # the sentinel, so an ungated rmtree would delete it. The guard must exit non-zero and
        # leave the sentinel untouched (non-vacuous: the sentinel exists before and after).
        base = os.path.join(self.tmp, "base")
        os.makedirs(base)
        sentinel = os.path.join(self.tmp, "victim")
        os.makedirs(sentinel)
        with open(os.path.join(sentinel, "keep.txt"), "w") as fh:
            fh.write("do not delete")
        # os.path.join(abspath(base), "../victim") resolves to self.tmp/victim (the sentinel).
        code, _o, err = _run(["../victim", "--dir", base, "--uninstall"])
        self.assertEqual(code, 1)
        self.assertIn("unknown skill", err)
        self.assertTrue(
            os.path.isfile(os.path.join(sentinel, "keep.txt")),
            "path-traversal uninstall must delete nothing outside the base dir",
        )

    def test_project_flag_uses_opencode_skills_path(self):
        code, _o, _e = _run(["notion-api", "--project", self.tmp])
        self.assertEqual(code, 0)
        self.assertTrue(
            os.path.isdir(os.path.join(self.tmp, ".opencode", "skills", "notion-api"))
        )


class ListAndErrors(unittest.TestCase):
    def test_list_shows_the_six(self):
        code, out, _e = _run(["--list"])
        self.assertEqual(code, 0)
        for name in (
            "carbon-builder",
            "notion-api",
            "opencode-expertise",
            "dlt-pipelines",
            "subagent-creator",
            "private-fork",
        ):
            self.assertIn(name, out)

    def test_rejects_unknown_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _o, err = _run(["nope-skill", "--dir", tmp])
            self.assertEqual(code, 1)
            self.assertIn("unknown skill", err)

    def test_no_name_and_no_list_errors(self):
        code, _o, err = _run([])
        self.assertEqual(code, 2)
        self.assertIn("required", err)


class EligibilityErrorFunction(unittest.TestCase):
    """Drive eligibility_error directly with synthetic catalogs to exercise the ineligible and
    incompatible branches (no real ineligible skill is in the committed catalog, by design)."""

    def _roster(self):
        from check_roster import parse_roster

        return {e["id"]: e for e in parse_roster(C.ROSTER)}

    def test_ineligible_skill_is_named(self):
        roster = self._roster()
        # comms carries requires: [local-mcp] — catalogue it and the gate must refuse it.
        catalog = {
            "comms": {
                "id": "comms",
                "standalone": "true",
                "clients": ["claude-code", "opencode"],
                "depends_on_skills": [],
                "prerequisites": [],
                "provenance": "authored",
            }
        }
        err = install_skill.eligibility_error("comms", catalog, roster)
        self.assertIsNotNone(err)
        self.assertIn("not standalone-eligible", err)

    def test_incompatible_client_is_named(self):
        roster = self._roster()
        # carbon-builder is eligible but here catalogued without opencode among its clients.
        catalog = {
            "carbon-builder": {
                "id": "carbon-builder",
                "standalone": "true",
                "clients": ["claude-code"],
                "depends_on_skills": [],
                "prerequisites": [],
                "provenance": "authored",
            }
        }
        err = install_skill.eligibility_error("carbon-builder", catalog, roster)
        self.assertIsNotNone(err)
        self.assertIn("opencode-compatible", err)


if __name__ == "__main__":
    unittest.main()
