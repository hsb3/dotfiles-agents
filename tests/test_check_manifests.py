"""check_manifests.py — the `claude plugin validate --strict` conformance gate.

The module shells out to a real binary, so the subprocess boundary is SUBSTITUTED rather
than exercised: `check_manifests.shutil.which` and `check_manifests.subprocess.run` are
patched for every test. Nothing here needs the `claude` CLI, git, or a network — the suite
passes on a bare machine, which is the repo's zero-install invariant.

Fixture repos are built under a tempdir (never under primitives-core/ or plugins/, per the
roster guard's orphan rule) and the module's REPO/PLUGINS_DIR/MARKETPLACE constants — all
computed at import time — are pointed at them for the duration of each test, so subjects()
derives from the fixture rather than the real repo.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_manifests as M  # noqa: E402


class FakeValidator:
    """Stands in for `subprocess.run(["claude", "plugin", "validate", ...])`.

    `results` maps a subject path to (returncode, stdout); anything unlisted passes clean.
    Every invocation is recorded so a test can assert what was NOT run.
    """

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        rc, out = self.results.get(argv[3], (0, ""))
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")

    @property
    def validated_paths(self):
        return [argv[3] for argv in self.calls]


class ManifestGateBase(unittest.TestCase):
    """A fixture repo: a marketplace.json plus two well-formed plugin assemblies."""

    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-manifests-")
        self.addCleanup(shutil.rmtree, self.fix, True)
        self.saved = {k: getattr(M, k) for k in ("REPO", "PLUGINS_DIR", "MARKETPLACE")}
        self.addCleanup(lambda: [setattr(M, k, v) for k, v in self.saved.items()])
        M.REPO = self.fix
        M.PLUGINS_DIR = os.path.join(self.fix, "plugins")
        M.MARKETPLACE = os.path.join(self.fix, ".claude-plugin", "marketplace.json")

        os.makedirs(os.path.join(self.fix, ".claude-plugin"))
        for pid in ("alpha", "beta"):
            self.make_plugin(pid)
        with open(M.MARKETPLACE, "w") as fh:
            json.dump(
                {"plugins": [{"name": p, "source": f"./plugins/{p}"} for p in ("alpha", "beta")]},
                fh,
            )

        # No test in this file may reach a real binary.
        self.which_saved = M.shutil.which
        self.run_saved = M.subprocess.run
        self.addCleanup(lambda: setattr(M.shutil, "which", self.which_saved))
        self.addCleanup(lambda: setattr(M.subprocess, "run", self.run_saved))
        M.shutil.which = lambda name: "/fake/bin/claude" if name == "claude" else None
        self.validator = FakeValidator()
        M.subprocess.run = self.validator

    # --- helpers -----------------------------------------------------------------
    def make_plugin(self, pid, manifest=True):
        pdir = os.path.join(M.PLUGINS_DIR, pid)
        os.makedirs(os.path.join(pdir, ".claude-plugin"), exist_ok=True)
        if manifest:
            with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "w") as fh:
                json.dump({"name": pid, "description": "fixture", "version": "0.1.0"}, fh)
        return pdir

    def fail(self, path, output):
        self.validator.results[path] = (1, output)

    def plugin_path(self, pid):
        return os.path.join(M.PLUGINS_DIR, pid)

    def run_main(self, argv=("check_manifests.py",)):
        """main() with stdout+stderr captured; returns (rc, combined text)."""
        out, err = io.StringIO(), io.StringIO()
        saved_argv = sys.argv
        sys.argv = list(argv)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = M.main()
        finally:
            sys.argv = saved_argv
        return rc, out.getvalue() + err.getvalue()


class CleanRepo(ManifestGateBase):
    def test_all_manifests_passing_exits_zero(self):
        rc, text = self.run_main()
        self.assertEqual(rc, 0, text)
        self.assertIn("✓", text)

    def test_marketplace_and_every_plugin_are_validated(self):
        self.run_main()
        self.assertEqual(
            self.validator.validated_paths,
            [self.fix, self.plugin_path("alpha"), self.plugin_path("beta")],
        )

    def test_the_validator_is_invoked_with_strict(self):
        self.run_main()
        argv = self.validator.calls[0]
        self.assertEqual(argv[:3], ["claude", "plugin", "validate"])
        self.assertIn("--strict", argv)

    def test_verbose_lists_each_passing_subject(self):
        rc, text = self.run_main(("check_manifests.py", "--verbose"))
        self.assertEqual(rc, 0, text)
        self.assertIn("plugins/alpha", text)
        self.assertIn("plugins/beta", text)


class FailingManifests(ManifestGateBase):
    def test_one_failing_manifest_is_red_and_names_only_that_subject(self):
        self.fail(
            self.plugin_path("beta"),
            "Warning: unrecognized field `changelog` in plugin.json",
        )
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/beta", text)
        self.assertIn("changelog", text)
        self.assertNotIn("plugins/alpha", text)

    def test_every_failing_subject_is_reported_not_just_the_first(self):
        """The docstring promises every violation prints; a bail-on-first would hide one."""
        self.fail(self.plugin_path("alpha"), "Warning: missing `author`")
        self.fail(self.plugin_path("beta"), "Warning: unrecognized field `changelog`")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/alpha", text)
        self.assertIn("plugins/beta", text)
        self.assertIn("2 problem(s)", text)

    def test_a_failing_marketplace_is_red(self):
        self.fail(self.fix, "Warning: marketplace entry has no `description`")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("description", text)

    def test_silent_nonzero_exit_still_reports_something(self):
        self.fail(self.plugin_path("alpha"), "")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("no output", text)


class MissingPrerequisites(ManifestGateBase):
    def test_missing_claude_binary_is_a_failure_not_a_skip(self):
        """The load-bearing case: an absent tool must go red, never quietly green."""
        M.shutil.which = lambda name: None
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("claude", text)
        self.assertIn("not a skip", text)
        self.assertEqual(self.validator.calls, [])

    def test_missing_marketplace_is_red(self):
        os.remove(M.MARKETPLACE)
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("marketplace.json", text)
        self.assertIn("missing", text)

    def test_plugin_dir_without_a_manifest_is_a_broken_assembly(self):
        self.make_plugin("gamma", manifest=False)
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/gamma", text)
        self.assertIn("broken assembly", text)
        # reported, not validated: the validator must not be asked about it
        self.assertNotIn(self.plugin_path("gamma"), self.validator.validated_paths)


class ValidatorFailureModes(ManifestGateBase):
    def test_a_hung_validator_is_red_not_a_hang(self):
        def timeout(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=M.TIMEOUT_SECONDS)

        M.subprocess.run = timeout
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("timed out", text)

    def test_a_binary_that_vanishes_mid_run_is_red_not_a_crash(self):
        def gone(argv, **kwargs):
            raise FileNotFoundError("claude")

        M.subprocess.run = gone
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("could not execute", text)


class SubjectDerivation(ManifestGateBase):
    """subjects() derives from disk — no inventory to edit when a plugin is added."""

    def test_marketplace_comes_first(self):
        self.assertEqual(M.subjects()[0], ("marketplace", self.fix))

    def test_a_new_plugin_dir_is_picked_up_with_no_list_edited(self):
        before = [label for label, _ in M.subjects()]
        self.make_plugin("gamma")
        after = [label for label, _ in M.subjects()]
        self.assertNotIn("gamma", before)
        self.assertIn("gamma", after)

    def test_dotfiles_and_non_directories_are_skipped(self):
        os.makedirs(os.path.join(M.PLUGINS_DIR, ".hidden"))
        with open(os.path.join(M.PLUGINS_DIR, "README.md"), "w") as fh:
            fh.write("not a plugin\n")
        labels = [label for label, _ in M.subjects()]
        self.assertEqual(labels, ["marketplace", "alpha", "beta"])

    def test_subjects_are_sorted_for_stable_output(self):
        for pid in ("zeta", "delta"):
            self.make_plugin(pid)
        labels = [label for label, _ in M.subjects()][1:]
        self.assertEqual(labels, sorted(labels))

    def test_no_plugins_dir_leaves_the_marketplace_as_the_only_subject(self):
        shutil.rmtree(M.PLUGINS_DIR)
        self.assertEqual(M.subjects(), [("marketplace", self.fix)])


if __name__ == "__main__":
    unittest.main()
