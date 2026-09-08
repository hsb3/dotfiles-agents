"""check_version_bump.py — the published-bytes/version-bump gate.

Fixture repos are built under a tempdir (never under primitives-core/ or plugins/, per the
roster guard's orphan rule). The LOCAL side is always a real on-disk assembly (regular
files plus symlinks into a fixture primitives-core/) so the dereferencing walk is exercised
for real; the PUBLISHED side is injected as a plain {path: bytes} map, so the comparison
tests need no git binary and no network.

Two narrower groups sit alongside those:
  * `PublishedRefResolution` drives GitPublishedTree with a FAKE command runner, pinning
    what the gate does when `origin/main` cannot be fetched (the network contract: a
    RECENT cached ref still measures and warns, one older than MAX_CACHED_REF_AGE_DAYS is
    red, and no usable ref at all is red).
  * `GitPublishedTreeIntegration` runs the real git plumbing against a throwaway clone of a
    throwaway origin (file transport, no network). It SKIPS when git is absent, so the rest
    of the suite still passes on a bare machine.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_version_bump as V  # noqa: E402


def published_index(files):
    """Build the published {pid: {relpath: blobhash}} index from a {path: bytes} map."""
    index = {}
    for path, data in files.items():
        parts = path.split("/")
        assert parts[0] == "plugins" and len(parts) > 2, path
        index.setdefault(parts[1], {})[("/".join(parts[2:]))] = V.blob_hash(data)
    return index


def published_json(files):
    """A published-plugin.json getter over a {path: bytes} map."""
    return lambda pid: files.get(f"plugins/{pid}/.claude-plugin/plugin.json")


def plugin_json_bytes(pid, version, description="A fixture plugin for the version-bump gate."):
    return json.dumps(
        {"name": pid, "description": description, "version": version}, indent=2
    ).encode("utf-8") + b"\n"


class ComparisonBase(unittest.TestCase):
    """A two-plugin fixture: `alpha` and `beta` both ship the shared `shared` skill body.

    On disk that is a symlink assembly (plugins/<id>/skills/shared ->
    primitives-core/skills/shared), which is what makes the dual-homed case real rather
    than simulated.
    """

    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-version-bump-")
        self.addCleanup(shutil.rmtree, self.fix, True)
        self.plugins = os.path.join(self.fix, "plugins")

        self.shared_body = b"---\nname: shared\ndescription: shared body\n---\n\nOriginal.\n"
        core = os.path.join(self.fix, "primitives-core", "skills", "shared")
        os.makedirs(core)
        self.shared_path = os.path.join(core, "SKILL.md")
        with open(self.shared_path, "wb") as fh:
            fh.write(self.shared_body)

        self.versions = {"alpha": "0.1.0", "beta": "2.3.4"}
        self.published_files = {}
        for pid, version in self.versions.items():
            pdir = os.path.join(self.plugins, pid)
            os.makedirs(os.path.join(pdir, ".claude-plugin"))
            os.makedirs(os.path.join(pdir, "skills"))
            os.symlink(
                os.path.join("..", "..", "..", "primitives-core", "skills", "shared"),
                os.path.join(pdir, "skills", "shared"),
            )
            manifest = plugin_json_bytes(pid, version)
            with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "wb") as fh:
                fh.write(manifest)
            readme = f"# {pid}\n".encode("utf-8")
            with open(os.path.join(pdir, "README.md"), "wb") as fh:
                fh.write(readme)
            # The published tree is what `cp -RL plugins` produced: dereferenced bytes.
            self.published_files[f"plugins/{pid}/.claude-plugin/plugin.json"] = manifest
            self.published_files[f"plugins/{pid}/README.md"] = readme
            self.published_files[f"plugins/{pid}/skills/shared/SKILL.md"] = self.shared_body

    # --- helpers -----------------------------------------------------------------
    def local_json(self, pid):
        path = os.path.join(self.plugins, pid, ".claude-plugin", "plugin.json")
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def problems(self):
        return V.compare(
            V.local_index(self.plugins),
            published_index(self.published_files),
            self.local_json,
            published_json(self.published_files),
        )

    def write_local(self, relpath, data):
        full = os.path.join(self.fix, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)

    def bump(self, pid, version):
        self.write_local(
            os.path.join("plugins", pid, ".claude-plugin", "plugin.json"),
            plugin_json_bytes(pid, version),
        )
        self.published_files.setdefault(f"plugins/{pid}/.claude-plugin/plugin.json", b"")


class Comparison(ComparisonBase):
    def test_unchanged_assembly_is_clean(self):
        self.assertEqual(self.problems(), [])

    def test_changed_bytes_without_a_bump_is_red(self):
        """The gate's whole reason to exist: changed published bytes, unmoved version."""
        self.write_local("plugins/alpha/README.md", b"# alpha\n\nNow with a second line.\n")
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/alpha", problems[0])
        self.assertIn("0.1.0", problems[0])
        self.assertIn("README.md", problems[0])
        self.assertNotIn("plugins/beta", problems[0])

    def test_changed_bytes_with_a_bump_is_clean(self):
        self.write_local("plugins/alpha/README.md", b"# alpha\n\nNow with a second line.\n")
        self.bump("alpha", "0.1.1")
        self.assertEqual(self.problems(), [])

    def test_dual_homed_edit_is_caught_for_every_plugin_that_ships_it(self):
        """One primitives-core skill body, two assemblies: BOTH plugins must go red."""
        with open(self.shared_path, "wb") as fh:
            fh.write(self.shared_body.replace(b"Original.", b"Edited once, shipped twice.\n"))
        problems = self.problems()
        self.assertEqual(len(problems), 2, problems)
        joined = "\n".join(problems)
        self.assertIn("plugins/alpha", joined)
        self.assertIn("plugins/beta", joined)
        for p in problems:
            self.assertIn("skills/shared/SKILL.md", p)

    def test_dual_homed_edit_with_only_one_bump_still_names_the_other(self):
        with open(self.shared_path, "wb") as fh:
            fh.write(self.shared_body.replace(b"Original.", b"Edited once, shipped twice.\n"))
        self.bump("alpha", "0.2.0")
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/beta", problems[0])

    def test_added_file_is_caught(self):
        """Direction one: local has a file the published tree does not."""
        self.write_local("plugins/alpha/hooks.json", b'{"hooks": {}}\n')
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/alpha", problems[0])
        self.assertIn("added", problems[0])
        self.assertIn("hooks.json", problems[0])

    def test_removed_file_is_caught(self):
        """Direction two: the published tree has a file local no longer ships."""
        os.remove(os.path.join(self.plugins, "alpha", "README.md"))
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/alpha", problems[0])
        self.assertIn("removed", problems[0])
        self.assertIn("README.md", problems[0])

    def test_new_plugin_absent_from_published_is_clean(self):
        pdir = os.path.join(self.plugins, "gamma", ".claude-plugin")
        os.makedirs(pdir)
        with open(os.path.join(pdir, "plugin.json"), "wb") as fh:
            fh.write(plugin_json_bytes("gamma", "0.1.0"))
        with open(os.path.join(self.plugins, "gamma", "README.md"), "wb") as fh:
            fh.write(b"# gamma\n")
        self.assertEqual(self.problems(), [])

    def test_plugin_removed_locally_is_not_reported(self):
        shutil.rmtree(os.path.join(self.plugins, "beta"))
        self.assertEqual(self.problems(), [])

    def test_pycache_dir_is_excluded(self):
        self.write_local("plugins/alpha/hooks/gate/__pycache__/hook.cpython-313.pyc", b"\x00fake")
        self.assertEqual(V.local_index(self.plugins)["alpha"].keys() & {
            "hooks/gate/__pycache__/hook.cpython-313.pyc"
        }, set())
        self.assertEqual(self.problems(), [])

    def test_loose_pyc_beside_a_source_file_is_excluded(self):
        self.write_local("plugins/alpha/skills/shared/helper.pyc", b"\x00fake")
        self.assertEqual(self.problems(), [])

    def test_pycache_under_a_symlinked_body_is_excluded(self):
        """The dereferenced walk reaches primitives-core/, where hooks leave bytecode."""
        self.write_local("primitives-core/skills/shared/__pycache__/x.cpython-313.pyc", b"\x00")
        self.assertEqual(self.problems(), [])

    def test_os_noise_files_are_excluded(self):
        self.write_local("plugins/alpha/.DS_Store", b"\x00\x00noise")
        self.assertEqual(self.problems(), [])

    def test_missing_local_plugin_json_is_red(self):
        os.remove(os.path.join(self.plugins, "alpha", ".claude-plugin", "plugin.json"))
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/alpha/.claude-plugin/plugin.json", problems[0])

    def test_local_plugin_json_without_a_version_is_red(self):
        self.write_local(
            "plugins/alpha/.claude-plugin/plugin.json",
            json.dumps({"name": "alpha", "description": "x"}).encode("utf-8"),
        )
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("version", problems[0])

    def test_unparseable_published_plugin_json_is_red(self):
        self.write_local("plugins/alpha/README.md", b"# alpha\n\nchanged\n")
        self.published_files["plugins/alpha/.claude-plugin/plugin.json"] = b"{not json"
        problems = self.problems()
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("alpha", problems[0])

    def test_problems_are_sorted_by_plugin_id(self):
        with open(self.shared_path, "wb") as fh:
            fh.write(b"changed\n")
        problems = self.problems()
        self.assertEqual([p.split(":")[0] for p in problems], ["plugins/alpha", "plugins/beta"])


class MainEntryPoint(ComparisonBase):
    """main() end to end, with the published tree injected — no git, no network."""

    class FakeTree:
        def __init__(self, files, reason=None, note=""):
            self.files = files
            self.reason = reason
            self.note = note

        def prepare(self):
            return self.reason

        def index(self):
            return published_index(self.files)

        def plugin_json(self, pid):
            return self.files.get(f"plugins/{pid}/.claude-plugin/plugin.json")

    def run_main(self, tree):
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=tree, out=lines.append)
        return rc, "\n".join(lines)

    def test_clean_tree_exits_zero(self):
        rc, text = self.run_main(self.FakeTree(self.published_files))
        self.assertEqual(rc, 0, text)
        self.assertIn("✓", text)

    def test_violation_exits_one_and_names_the_plugin(self):
        self.write_local("plugins/beta/README.md", b"# beta\n\nchanged\n")
        rc, text = self.run_main(self.FakeTree(self.published_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("✗", text)
        self.assertIn("plugins/beta", text)
        self.assertIn("2.3.4", text)

    def test_unreachable_published_ref_is_red(self):
        """A gate that cannot measure is red, never green (decision-016 point 4).

        The message has to acquit the version: nothing was compared, so a reader must not
        read this as a missing bump.
        """
        self.write_local("plugins/beta/README.md", b"# beta\n\nchanged\n")
        tree = self.FakeTree(self.published_files, reason="could not reach origin/main (offline)")
        rc, text = self.run_main(tree)
        self.assertEqual(rc, 1, text)
        self.assertIn("✗", text)
        self.assertIn("offline", text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertNotIn("plugins/beta", text)

    def test_stale_ref_note_is_surfaced(self):
        tree = self.FakeTree(self.published_files, note="fetch failed; using a cached origin/main")
        rc, text = self.run_main(tree)
        self.assertEqual(rc, 0, text)
        self.assertIn("cached origin/main", text)


class LsTreeParsing(unittest.TestCase):
    def _entry(self, sha, path):
        return f"100644 blob {sha}\t{path}".encode("utf-8") + b"\x00"

    def test_parses_nul_separated_entries(self):
        out = (
            self._entry("a" * 40, "plugins/alpha/README.md")
            + self._entry("b" * 40, "plugins/alpha/skills/shared/SKILL.md")
            + self._entry("c" * 40, "plugins/beta/README.md")
        )
        index = V.parse_ls_tree(out)
        self.assertEqual(sorted(index), ["alpha", "beta"])
        self.assertEqual(
            index["alpha"],
            {"README.md": "a" * 40, "skills/shared/SKILL.md": "b" * 40},
        )

    def test_non_ascii_paths_survive(self):
        """A tracked path with non-ASCII bytes must not be mangled (cf. check_flow.py)."""
        out = self._entry("d" * 40, "plugins/alpha/skills/shared/café.md")
        index = V.parse_ls_tree(out)
        self.assertEqual(list(index["alpha"]), ["skills/shared/café.md"])

    def test_pruned_paths_are_dropped_from_the_published_side_too(self):
        out = (
            self._entry("e" * 40, "plugins/alpha/README.md")
            + self._entry("f" * 40, "plugins/alpha/hooks/g/__pycache__/h.pyc")
        )
        self.assertEqual(list(V.parse_ls_tree(out)["alpha"]), ["README.md"])

    def test_empty_output_is_an_empty_index(self):
        self.assertEqual(V.parse_ls_tree(b""), {})


class PublishedRefResolution(unittest.TestCase):
    """GitPublishedTree.prepare() against a fake command runner."""

    def tree(self, responses, calls=None):
        def run(args):
            calls_seen = calls if calls is not None else []
            calls_seen.append(args)
            for prefix, result in responses:
                if args[: len(prefix)] == prefix:
                    return result
            raise AssertionError(f"unexpected git call: {args}")

        return V.GitPublishedTree(run=run)

    def test_fetch_then_resolve_is_available(self):
        calls = []
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (0, b"", "")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            ],
            calls,
        )
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.note, "")
        self.assertTrue(any(c[0] == "fetch" for c in calls))

    def test_shallow_repo_fetches_shallow(self):
        calls = []
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"true\n", "")),
                (["fetch"], (0, b"", "")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            ],
            calls,
        )
        self.assertIsNone(tree.prepare())
        fetch = next(c for c in calls if c[0] == "fetch")
        self.assertIn("--depth=1", fetch)

    def test_full_repo_fetch_stays_full(self):
        """Never shallow-mark a complete local clone as a side effect of a gate."""
        calls = []
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (0, b"", "")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            ],
            calls,
        )
        tree.prepare()
        fetch = next(c for c in calls if c[0] == "fetch")
        self.assertNotIn("--depth=1", fetch)

    def _committed_days_ago(self, days):
        """A `git log -1 --format=%ct` stdout for a commit `days` days in the past."""
        return str(int(time.time() - days * 86400)).encode("ascii") + b"\n"

    def test_failed_fetch_falls_back_to_a_recent_cached_ref(self):
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: unable to access ... Could not resolve host")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, self._committed_days_ago(2), "")),
            ]
        )
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        self.assertIn("Could not resolve host", tree.note)

    def test_the_recent_cached_ref_warning_states_the_measured_age(self):
        """The warning has to say HOW stale, or a reader cannot judge what it is worth."""
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, self._committed_days_ago(3), "")),
            ]
        )
        self.assertIsNone(tree.prepare())
        # two decimals, so a reader can tell 6.99 days from 7.04 — one decimal prints
        # "7.0 days old" for both, on opposite sides of the verdict
        self.assertIn("3.00 days old", tree.note)
        self.assertIn(str(V.MAX_CACHED_REF_AGE_DAYS), tree.note)

    def test_failed_fetch_with_a_stale_cached_ref_is_unavailable(self):
        """A ref too old to stand in for a refreshed one has not measured `main`."""
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, self._committed_days_ago(30), "")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("30.00 days old", reason)
        self.assertIn(str(V.MAX_CACHED_REF_AGE_DAYS), reason)
        self.assertIn("Could not resolve host", reason)

    def test_the_limit_itself_measures_and_a_second_past_it_is_red(self):
        """The cutoff is exact and one-sided: MORE than the limit is red, the limit is not.

        The clock is pinned, because with a real one an integer `%ct` exactly the limit
        away lands microseconds over and the boundary is untestable.
        """
        now = 1_800_000_000.0
        limit = V.MAX_CACHED_REF_AGE_DAYS * V.SECONDS_PER_DAY
        for seconds_old, expect_red in ((limit, False), (limit + 1, True)):
            tree = self.tree(
                [
                    (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                    (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                    (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                    (["log", "-1"], (0, str(int(now - seconds_old)).encode("ascii"), "")),
                ]
            )
            with mock.patch.object(V.time, "time", lambda: now):
                reason = tree.prepare()
            self.assertEqual(reason is not None, expect_red, f"{seconds_old}s: {reason}")

    def test_a_future_dated_cached_ref_is_unavailable(self):
        """A ref dated ahead of now is a clock disagreeing, not a fresh ref.

        A local clock behind the publisher's turns a genuinely old cache negative-aged, so
        reading that as "within the limit" is the staleness loophole reopened.
        """
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, self._committed_days_ago(-3650), "")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("age could not be read", reason)

    def test_an_absurdly_large_commit_date_is_unavailable(self):
        """Same branch by construction: a garbage `%ct` is a huge negative age."""
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, b"9" * 18 + b"\n", "")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("age could not be read", reason)

    def test_a_later_successful_fetch_clears_the_stale_warning(self):
        """`note` is per-prepare() state: a warning must not outlive the failure it named."""
        fetches = [(128, b"", "fatal: Could not resolve host: github.com"), (0, b"", "")]

        def run(args):
            if args[0] == "fetch":
                return fetches.pop(0)
            if args[0] == "log":
                return (0, str(int(time.time())).encode("ascii"), "")
            if args[:2] == ["rev-parse", "--is-shallow-repository"]:
                return (0, b"false\n", "")
            return (0, b"c" * 40 + b"\n", "")

        tree = V.GitPublishedTree(run=run)
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.note, "")

    def test_an_unreadable_cached_ref_date_is_unavailable(self):
        """Age unmeasured is freshness unproven, which is red (decision-016 point 4)."""
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (128, b"", "fatal: bad object")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("age could not be read", reason)

    def test_an_unparseable_cached_ref_date_is_unavailable(self):
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
                (["log", "-1"], (0, b"not-a-timestamp\n", "")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("age could not be read", reason)

    def test_a_successful_fetch_never_asks_for_the_cached_ref_age(self):
        """A refreshed ref is fresh by definition — measuring it would be dead weight."""
        calls = []
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (0, b"", "")),
                (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            ],
            calls,
        )
        self.assertIsNone(tree.prepare())
        self.assertEqual([c for c in calls if c[0] == "log"], [])

    def test_failed_fetch_with_no_cached_ref_is_unavailable(self):
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["rev-parse", "--verify"], (1, b"", "")),
            ]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("origin/main", reason)
        self.assertIn("Could not resolve host", reason)

    def test_multiline_git_stderr_is_collapsed_to_one_line(self):
        """git's fetch stderr runs several lines; a CI notice must stay one."""
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: could not read\n\nPlease make sure\nthe repo exists.")),
                (["rev-parse", "--verify"], (1, b"", "")),
            ]
        )
        reason = tree.prepare()
        self.assertNotIn("\n", reason)
        self.assertIn("Please make sure the repo exists.", reason)

    def test_a_very_long_git_error_is_bounded(self):
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "x " * 5000)),
                (["rev-parse", "--verify"], (1, b"", "")),
            ]
        )
        self.assertLess(len(tree.prepare()), V.MAX_GIT_ERROR_CHARS + 120)

    def test_missing_git_binary_is_unavailable_not_a_crash(self):
        def run(args):
            raise FileNotFoundError("git")

        reason = V.GitPublishedTree(run=run).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("git", reason)

    def test_timeout_is_unavailable_not_a_crash(self):
        def run(args):
            raise subprocess.TimeoutExpired(cmd="git", timeout=1)

        reason = V.GitPublishedTree(run=run).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("timed out", reason)

    def test_unavailable_tree_makes_main_red(self):
        """Even with nothing to compare, an unreadable published tree cannot report green."""
        def run(args):
            raise FileNotFoundError("git")

        fix = tempfile.mkdtemp(prefix="check-version-bump-empty-")
        self.addCleanup(shutil.rmtree, fix, True)
        os.makedirs(os.path.join(fix, "plugins"))
        lines = []
        rc = V.main(
            plugins_dir=os.path.join(fix, "plugins"),
            tree=V.GitPublishedTree(run=run),
            out=lines.append,
        )
        self.assertEqual(rc, 1)
        self.assertIn("NOT evidence of a missing version bump", "\n".join(lines))


GIT = shutil.which("git")


@unittest.skipUnless(GIT, "git is not installed")
class GitPublishedTreeIntegration(unittest.TestCase):
    """Real git plumbing, no network: a file-transport origin in a tempdir."""

    def git(self, repo, *args, date=None):
        env = dict(os.environ)
        env.update(
            HOME=self.home,
            GIT_CONFIG_GLOBAL=os.path.join(self.home, "gitconfig"),
            GIT_CONFIG_SYSTEM=os.path.join(self.home, "gitconfig"),
            GIT_AUTHOR_NAME="fixture",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="fixture",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
            GIT_TERMINAL_PROMPT="0",
        )
        if date is not None:
            # The gate reads %ct, the COMMITTER date; `git commit --date` moves only the
            # author date, so backdating has to go through the environment.
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        proc = subprocess.run(
            [GIT, "-C", repo] + list(args), capture_output=True, env=env, timeout=60
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        return proc.stdout

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="check-version-bump-git-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        with open(os.path.join(self.home, "gitconfig"), "w") as fh:
            fh.write("")

        # origin: a repo whose `main` carries the DEREFERENCED published tree
        self.origin = os.path.join(self.root, "origin")
        os.makedirs(os.path.join(self.origin, "plugins", "alpha", ".claude-plugin"))
        os.makedirs(os.path.join(self.origin, "plugins", "alpha", "skills", "shared"))
        with open(os.path.join(self.origin, "plugins", "alpha", ".claude-plugin", "plugin.json"), "wb") as fh:
            fh.write(plugin_json_bytes("alpha", "0.1.0"))
        with open(os.path.join(self.origin, "plugins", "alpha", "skills", "shared", "SKILL.md"), "wb") as fh:
            fh.write(b"published body\n")
        self.git(self.origin, "init", "-q", "-b", "main")
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-qm", "publish: fixture")

        # work: a clone whose plugins/ is a SYMLINK assembly over primitives-core/
        self.work = os.path.join(self.root, "work")
        subprocess.run([GIT, "clone", "-q", self.origin, self.work], check=True, timeout=60)
        core = os.path.join(self.work, "primitives-core", "skills", "shared")
        os.makedirs(core, exist_ok=True)
        self.body = os.path.join(core, "SKILL.md")
        with open(self.body, "wb") as fh:
            fh.write(b"published body\n")
        shutil.rmtree(os.path.join(self.work, "plugins", "alpha", "skills", "shared"))
        os.symlink(
            os.path.join("..", "..", "..", "primitives-core", "skills", "shared"),
            os.path.join(self.work, "plugins", "alpha", "skills", "shared"),
        )
        self.plugins = os.path.join(self.work, "plugins")

    def tree(self):
        return V.GitPublishedTree(repo=self.work)

    def local_json(self, pid):
        with open(os.path.join(self.plugins, pid, ".claude-plugin", "plugin.json"), "rb") as fh:
            return fh.read()

    def test_dereferenced_assembly_matches_the_published_tree(self):
        tree = self.tree()
        self.assertIsNone(tree.prepare(), tree.note)
        self.assertEqual(
            V.compare(V.local_index(self.plugins), tree.index(), self.local_json, tree.plugin_json),
            [],
        )

    def test_real_edit_through_a_symlink_is_caught(self):
        with open(self.body, "wb") as fh:
            fh.write(b"edited body\n")
        tree = self.tree()
        self.assertIsNone(tree.prepare(), tree.note)
        problems = V.compare(
            V.local_index(self.plugins), tree.index(), self.local_json, tree.plugin_json
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("plugins/alpha", problems[0])
        self.assertIn("skills/shared/SKILL.md", problems[0])

    def test_main_against_the_real_clone_exits_one(self):
        with open(self.body, "wb") as fh:
            fh.write(b"edited body\n")
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        self.assertEqual(rc, 1, "\n".join(lines))
        self.assertIn("plugins/alpha", "\n".join(lines))

    def _break_origin(self):
        self.git(self.work, "remote", "set-url", "origin", os.path.join(self.root, "gone"))

    def test_unreachable_origin_falls_back_to_the_cached_ref(self):
        """Real fetch failure, cached ref present: still compares, and says the ref is stale."""
        self._break_origin()
        with open(self.body, "wb") as fh:
            fh.write(b"edited body\n")
        tree = self.tree()
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        problems = V.compare(
            V.local_index(self.plugins), tree.index(), self.local_json, tree.plugin_json
        )
        self.assertEqual(len(problems), 1, problems)

    def _republish(self, body, days_ago):
        """Publish `body` on origin/main dated `days_ago` back, cache it, return its %ct.

        Returns the committer date git actually recorded rather than the one requested —
        the gate reads that value, so the fixture asserts on it instead of assuming.
        """
        when = "@%d +0000" % int(time.time() - days_ago * 86400)
        published = os.path.join(self.origin, "plugins", "alpha", "skills", "shared", "SKILL.md")
        with open(published, "wb") as fh:
            fh.write(body)
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-qm", "publish: backdated fixture", date=when)
        self.git(self.work, "fetch", "-q", "origin", "+refs/heads/main:refs/remotes/origin/main")
        out = self.git(self.work, "log", "-1", "--format=%ct", "origin/main")
        return int(out.decode("ascii").strip())

    def test_unreachable_origin_with_a_stale_cached_ref_is_red(self):
        """Cached ref older than the limit: red, and it does not blame the version."""
        committed = self._republish(b"republished body\n", 30)
        self.assertLess(committed, time.time() - 29 * 86400)
        self._break_origin()
        # local still ships the OLD body, so a real divergence exists that must not be
        # reported as a missing bump
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertIn("30.00 days old", text)
        self.assertNotIn("plugins/alpha", text)

    def test_unreachable_origin_with_a_future_dated_cached_ref_is_red(self):
        """A skewed clock must not launder a stale cache into a green comparison."""
        self._republish(b"republished body\n", -3650)
        self._break_origin()
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertIn("age could not be read", text)
        self.assertNotIn("plugins/alpha", text)

    def test_unreachable_origin_with_a_recent_cached_ref_still_measures(self):
        """Cached ref younger than the limit: exit 0, with the warning kept."""
        committed = self._republish(b"republished body\n", 2)
        self.assertGreater(committed, time.time() - 3 * 86400)
        self._break_origin()
        with open(self.body, "wb") as fh:
            fh.write(b"republished body\n")
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 0, text)
        self.assertIn("⚠", text)
        self.assertIn("could not be refreshed", text)
        self.assertIn("2.00 days old", text)

    def test_unreachable_origin_with_no_cached_ref_is_red(self):
        """Real fetch failure, no cached ref: red, and it does not blame the version."""
        self._break_origin()
        self.git(self.work, "update-ref", "-d", "refs/remotes/origin/main")
        with open(self.body, "wb") as fh:
            fh.write(b"edited body\n")  # a real violation that must NOT be reported as one
        self.assertIsNotNone(self.tree().prepare())
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertNotIn("plugins/alpha", text)


if __name__ == "__main__":
    unittest.main()
