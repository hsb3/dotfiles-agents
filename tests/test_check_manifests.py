"""check_manifests.py — the `claude plugin validate --strict` conformance gate.

The module shells out to a real binary, so the subprocess boundary is SUBSTITUTED rather
than exercised: `check_manifests.shutil.which` and `check_manifests.subprocess.run` are
patched for every test. Nothing here needs the `claude` CLI, git, or a network — the suite
passes on a bare machine, which is the repo's zero-install invariant.

Fixture repos are built under a tempdir (never under primitives-core/ or plugins/, per the
roster guard's orphan rule) and the module's REPO/PLUGINS_DIR/MARKETPLACE constants — all
computed at import time — are pointed at them for the duration of each test, so subjects()
derives from the fixture rather than the real repo.

Validation happens on a DEREFERENCED COPY in a second tempdir, so the path handed to the
validator is NOT the path reported in messages. The fake validator therefore keys its
canned results by subject LABEL (recovered from the path's shape) rather than by path:
tests say "beta fails" without caring which tree beta was validated in, which is the only
thing that keeps them honest about the copy/report split.
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


def label_for(path):
    """Recover a subject label from a validated path, in either tree.

    `<anywhere>/plugins/beta` is beta; anything else is the marketplace root (the repo
    itself in place, or the dereferenced copy's root).
    """
    parent, base = os.path.split(path.rstrip(os.sep))
    return base if os.path.basename(parent) == "plugins" else "marketplace"


class FakeValidator:
    """Stands in for `subprocess.run(["claude", "plugin", "validate", ...])`.

    `results` maps a subject LABEL to (returncode, stdout); anything unlisted passes clean.
    Every invocation is recorded so a test can assert what was NOT run, and what tree the
    path pointed into. With `snapshot` on it also records the bytes actually visible at the
    validated path, which is how the symlink-following behaviour is pinned.
    """

    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []
        self.snapshot = False
        self.snapshots = {}

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        path = argv[3]
        label = label_for(path)
        if self.snapshot:
            self.snapshots[label] = self._walk(path)
        rc, out = self.results.get(label, (0, ""))
        return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")

    @staticmethod
    def _walk(path):
        """{relpath: (is_symlink, text)} for every file reachable at `path`.

        os.walk does not follow directory symlinks, so a component that is still a link
        simply does not appear here — exactly the blindness the real validator has.
        """
        seen = {}
        for root, _dirs, files in os.walk(path):
            for name in files:
                full = os.path.join(root, name)
                with open(full, encoding="utf-8", errors="replace") as fh:
                    seen[os.path.relpath(full, path)] = (os.path.islink(full), fh.read())
        return seen

    @property
    def validated_paths(self):
        return [argv[3] for argv in self.calls]

    @property
    def validated_labels(self):
        return [label_for(argv[3]) for argv in self.calls]


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

    def symlink_component(self, pid, body="---\nname: alpha\ndescription: real body\n---\n"):
        """Give `pid` a skills/ entry that is a real symlink into a fixture primitives-core.

        This is the shape that turned CI red: the validator does not follow it, so the copy
        has to resolve it. Returns the link path.
        """
        src = os.path.join(self.fix, "primitives-core", "skills", pid)
        os.makedirs(src, exist_ok=True)
        with open(os.path.join(src, "SKILL.md"), "w") as fh:
            fh.write(body)
        skills = os.path.join(self.plugin_path(pid), "skills")
        os.makedirs(skills, exist_ok=True)
        link = os.path.join(skills, pid)
        os.symlink(os.path.relpath(src, skills), link)
        return link

    def fail(self, label, output):
        self.validator.results[label] = (1, output)

    def plugin_path(self, pid):
        return os.path.join(M.PLUGINS_DIR, pid)

    @property
    def deref_root(self):
        """The dereferenced copy's root, recovered from the marketplace invocation."""
        return self.validator.calls[0][3]

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
        self.assertEqual(self.validator.validated_labels, ["marketplace", "alpha", "beta"])

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


class DereferencedCopy(ManifestGateBase):
    """The fix for the red CI: validate what ships, not the symlink assembly in place."""

    def test_the_validated_target_is_the_copy_not_the_tree_in_place(self):
        self.run_main()
        paths = self.validator.validated_paths
        for path in paths:
            self.assertFalse(
                path == self.fix or path.startswith(self.fix + os.sep),
                f"validated the real tree in place: {path}",
            )
        self.assertEqual(
            paths[1:],
            [os.path.join(self.deref_root, "plugins", pid) for pid in ("alpha", "beta")],
        )

    def test_a_symlinked_component_is_followed_into_the_copy(self):
        """The exact bug: a link the validator will not read must be resolved first."""
        self.symlink_component("alpha")
        self.validator.snapshot = True
        rc, text = self.run_main()
        self.assertEqual(rc, 0, text)
        seen = self.validator.snapshots["alpha"]
        self.assertIn("skills/alpha/SKILL.md", seen, "the symlinked body never reached the copy")
        is_link, content = seen["skills/alpha/SKILL.md"]
        self.assertFalse(is_link, "the copy still holds a symlink, so the validator skips it")
        self.assertIn("real body", content)

    def test_the_copy_carries_the_marketplace_manifest(self):
        with M.dereferenced() as deref:
            self.assertTrue(
                os.path.isfile(os.path.join(deref, ".claude-plugin", "marketplace.json"))
            )

    def test_the_tempdir_is_cleaned_up_afterwards(self):
        self.run_main()
        self.assertNotEqual(self.deref_root, self.fix)
        self.assertFalse(os.path.exists(self.deref_root), "the dereferenced copy leaked")

    def test_reported_paths_stay_repo_relative_not_tempdir_paths(self):
        """A failure message naming a vanished tempdir would be useless to a human."""
        self.fail("beta", "Warning: unrecognized field `changelog`")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/beta", text)
        self.assertNotIn(self.deref_root, text)
        self.assertNotIn("manifest-gate-", text)

    def test_no_plugins_dir_yields_no_copy(self):
        shutil.rmtree(M.PLUGINS_DIR)
        with M.dereferenced() as deref:
            self.assertIsNone(deref)

    def test_run_validates_in_place_when_there_is_no_copy(self):
        problems, checked = M._run(M.subjects(), None, False)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 3)
        self.assertEqual(
            self.validator.validated_paths,
            [self.fix, self.plugin_path("alpha"), self.plugin_path("beta")],
        )

    def test_a_subject_missing_from_the_copy_falls_back_to_its_real_path(self):
        """A copy that somehow lacks a counterpart must not validate a nonexistent path."""
        empty = tempfile.mkdtemp(prefix="empty-deref-")
        self.addCleanup(shutil.rmtree, empty, True)
        M._run([("alpha", self.plugin_path("alpha"))], empty, False)
        self.assertEqual(self.validator.validated_paths, [self.plugin_path("alpha")])


class FailingManifests(ManifestGateBase):
    def test_one_failing_manifest_is_red_and_names_only_that_subject(self):
        self.fail("beta", "Warning: unrecognized field `changelog` in plugin.json")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/beta", text)
        self.assertIn("changelog", text)
        self.assertNotIn("plugins/alpha", text)

    def test_every_failing_subject_is_reported_not_just_the_first(self):
        """The docstring promises every violation prints; a bail-on-first would hide one."""
        self.fail("alpha", "Warning: missing `author`")
        self.fail("beta", "Warning: unrecognized field `changelog`")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/alpha", text)
        self.assertIn("plugins/beta", text)
        self.assertIn("2 problem(s)", text)

    def test_a_failing_marketplace_is_red(self):
        self.fail("marketplace", "Warning: marketplace entry has no `description`")
        rc, text = self.run_main()
        self.assertEqual(rc, 1, text)
        self.assertIn("description", text)

    def test_silent_nonzero_exit_still_reports_something(self):
        self.fail("alpha", "")
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
        self.assertNotIn("gamma", self.validator.validated_labels)


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
