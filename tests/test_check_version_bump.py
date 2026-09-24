"""check_version_bump.py — the published-bytes/version-bump gate.

Fixture repos are built under a tempdir (never under primitives-core/ or plugins/, per the
roster guard's orphan rule). The LOCAL side is always a real on-disk assembly (regular
files plus symlinks into a fixture primitives-core/) so the dereferencing walk is exercised
for real; the PUBLISHED side is injected as a plain {path: bytes} map, so the comparison
tests need no git binary and no network.

Two narrower groups sit alongside those:
  * `PublishedRefResolution` drives GitPublishedTree with a FAKE command runner, pinning
    what the gate does when `origin/main` cannot be fetched (the network contract: a cache
    synced within MAX_SYNC_AGE_DAYS still measures and warns, one last synced past that is
    red, and no sync record — or no usable ref — at all is red).
  * `GitPublishedTreeIntegration` runs the real git plumbing against a throwaway clone of a
    throwaway origin (file transport, no network). It SKIPS when git is absent, so the rest
    of the suite still passes on a bare machine. It is also where the two ambiguity cases
    live: a local branch or tag literally named `origin/main` must not become the tree the
    gate compares against.
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
    """GitPublishedTree.prepare() against a fake command runner.

    The sync stamp is a real file in a tempdir — injected rather than resolved through
    git, so the fake runner only ever sees the calls a test is pinning.
    """

    CANONICAL = "git@github.com:hsb3/dotfiles-agents.git"

    def setUp(self):
        self.gitdir = tempfile.mkdtemp(prefix="check-version-bump-stamp-")
        self.addCleanup(shutil.rmtree, self.gitdir, True)
        self.stamp = os.path.join(self.gitdir, V.SYNC_STAMP_NAME)

    def record_sync(self, days_ago=0, raw=None, url=CANONICAL):
        """Write the sync stamp a previous successful run would have left."""
        with open(self.stamp, "w") as fh:
            fh.write(
                raw
                if raw is not None
                else "%d\t%s\n" % (int(time.time() - days_ago * 86400), url)
            )

    def tree(self, responses, calls=None):
        def run(args):
            calls_seen = calls if calls is not None else []
            calls_seen.append(args)
            for prefix, result in responses:
                if args[: len(prefix)] == prefix:
                    return result
            raise AssertionError(f"unexpected git call: {args}")

        return V.GitPublishedTree(run=run, stamp_path=self.stamp)

    def test_fetch_then_resolve_is_available(self):
        calls = []
        tree = self.tree(self._online(), calls)
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.note, "")
        self.assertTrue(any(c[0] == "fetch" for c in calls))

    def test_shallow_repo_fetches_shallow(self):
        calls = []
        tree = self.tree(
            [(["rev-parse", "--is-shallow-repository"], (0, b"true\n", ""))] + self._online()[1:],
            calls,
        )
        self.assertIsNone(tree.prepare())
        fetch = next(c for c in calls if c[0] == "fetch")
        self.assertIn("--depth=1", fetch)

    def test_full_repo_fetch_stays_full(self):
        """Never shallow-mark a complete local clone as a side effect of a gate."""
        calls = []
        tree = self.tree(self._online(), calls)
        tree.prepare()
        fetch = next(c for c in calls if c[0] == "fetch")
        self.assertNotIn("--depth=1", fetch)

    def _remote(self, url=CANONICAL):
        return (["remote", "get-url"], (0, url.encode("utf-8") + b"\n", ""))

    def _offline(self, extra=()):
        """Responses for a failed fetch over a resolvable cached ref."""
        return [
            (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
            (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
            (["show-ref", "--verify"], (0, b"", "")),
            (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            self._remote(),
        ] + list(extra)

    def _online(self, extra=()):
        """Responses for a fetch that reached the remote."""
        return [
            (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
            (["fetch"], (0, b"", "")),
            (["show-ref", "--verify"], (0, b"", "")),
            (["rev-parse", "--verify"], (0, b"c" * 40 + b"\n", "")),
            self._remote(),
        ] + list(extra)

    def test_failed_fetch_falls_back_to_a_recently_synced_cached_ref(self):
        self.record_sync(days_ago=2)
        tree = self.tree(self._offline())
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        self.assertIn("Could not resolve host", tree.note)

    def test_the_fallback_warning_states_the_measured_sync_age(self):
        """The warning has to say HOW stale, or a reader cannot judge what it is worth."""
        self.record_sync(days_ago=3)
        tree = self.tree(self._offline())
        self.assertIsNone(tree.prepare())
        # two decimals, so a reader can tell 6.99 days from 7.04 — one decimal prints
        # "7.0 days ago" for both, on opposite sides of the verdict
        self.assertIn("3.00 days ago", tree.note)
        self.assertIn(str(V.MAX_SYNC_AGE_DAYS), tree.note)

    def test_the_tip_commit_date_is_not_the_metric(self):
        """A quiet `main` publishes nothing for weeks; that says nothing about the cache.

        The gate must never ask for the cached commit's date — the fake runner rejects
        any call a test does not name, so a `git log` here would raise.
        """
        self.record_sync(days_ago=1)
        calls = []
        tree = self.tree(self._offline(), calls)
        self.assertIsNone(tree.prepare())
        self.assertEqual([c for c in calls if c[0] == "log"], [])

    def test_failed_fetch_with_a_long_unsynced_cache_is_unavailable(self):
        """A cache last synced past the limit has not measured `main`."""
        self.record_sync(days_ago=30)
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("30.00 days ago", reason)
        self.assertIn(str(V.MAX_SYNC_AGE_DAYS), reason)
        self.assertIn("Could not resolve host", reason)

    def test_the_limit_itself_measures_and_a_second_past_it_is_red(self):
        """The cutoff is exact and one-sided: MORE than the limit is red, the limit is not.

        The clock is pinned, because with a real one a stamp written exactly the limit
        away lands microseconds over and the boundary is untestable.
        """
        now = 1_800_000_000.0
        limit = V.MAX_SYNC_AGE_DAYS * V.SECONDS_PER_DAY
        for seconds_old, expect_red in ((limit, False), (limit + 1, True)):
            self.record_sync(raw="%d\t%s" % (int(now - seconds_old), self.CANONICAL))
            tree = self.tree(self._offline())
            with mock.patch.object(V.time, "time", lambda: now):
                reason = tree.prepare()
            self.assertEqual(reason is not None, expect_red, f"{seconds_old}s: {reason}")

    def test_a_future_dated_sync_record_is_unavailable(self):
        """A record dated ahead of now is a clock disagreeing, not a fresh sync.

        A clock moved backwards turns a long-abandoned record negative-aged, so reading
        that as "within the limit" is the staleness loophole reopened.
        """
        self.record_sync(days_ago=-3650)
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("in the FUTURE", reason)

    def test_an_absurdly_large_sync_record_is_unavailable(self):
        """Same branch by construction: a garbage stamp is a huge negative age."""
        self.record_sync(raw="9" * 18 + "\t" + self.CANONICAL)
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("in the FUTURE", reason)

    def test_a_later_successful_fetch_clears_the_stale_warning(self):
        """`note` is per-prepare() state: a warning must not outlive the failure it named."""
        fetches = [(128, b"", "fatal: Could not resolve host: github.com"), (0, b"", "")]

        def run(args):
            if args[0] == "fetch":
                return fetches.pop(0)
            if args[0] == "remote":
                return (0, self.CANONICAL.encode("utf-8") + b"\n", "")
            if args[:2] == ["rev-parse", "--is-shallow-repository"]:
                return (0, b"false\n", "")
            return (0, b"c" * 40 + b"\n", "")

        self.record_sync()
        tree = V.GitPublishedTree(run=run, stamp_path=self.stamp)
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.note, "")

    def test_no_sync_record_at_all_is_unavailable(self):
        """Freshness unproven is freshness unmeasured, which is red (decision-016 point 4).

        This is the clone that has never fetched under this gate: measured on git 2.55.0,
        neither a reflog entry nor a FETCH_HEAD survives a clone to date its cache.
        """
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("no record of ever syncing it", reason)

    def test_an_unparseable_sync_record_is_unavailable(self):
        self.record_sync(raw="not-a-timestamp\t" + self.CANONICAL + "\n")
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("sync record is unreadable", reason)

    def test_a_bare_timestamp_sync_record_is_unavailable(self):
        """The format this gate wrote before the stamp named its remote.

        Not grandfathered: a record that cannot say which remote earned it is exactly the
        certificate `test_a_sync_from_another_remote_is_no_record` refuses, so honouring
        it would keep that hazard alive for a full limit's worth of days per clone.
        """
        self.record_sync(raw="%d\n" % int(time.time()))
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("sync record is unreadable", reason)

    def test_a_sync_from_another_remote_is_no_record(self):
        """The fetch that wrote the stamp wrote the cached ref too, so a stamp earned
        from a fork certifies a tree the current `origin` never published."""
        self.record_sync(url="https://example.invalid/someone/fork.git")
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertIn("earned from https://example.invalid/someone/fork.git", reason)
        self.assertIn(self.CANONICAL, reason)

    def test_an_unreadable_remote_url_is_unavailable(self):
        """No way to tell whether the record describes this remote is no proof either."""
        self.record_sync()
        tree = self.tree(
            self._offline()[:4] + [(["remote", "get-url"], (128, b"", "fatal: No such remote"))]
        )
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("could not be read", reason)

    def test_a_directory_at_the_stamp_path_is_not_reported_as_a_missing_record(self):
        """`IsADirectoryError` is an OSError; reporting it as "never synced" hands the
        reader a remedy that cannot work."""
        os.mkdir(self.stamp)
        reason = self.tree(self._offline()).prepare()
        self.assertIsNotNone(reason)
        self.assertNotIn("no record of ever syncing it", reason)
        self.assertIn("could not be read", reason)

    def test_an_unlocatable_git_dir_is_unavailable(self):
        """No stamp path resolvable means no freshness proof, so the fallback declines."""
        tree = self.tree(
            self._offline([(["rev-parse", "--git-common-dir"], (128, b"", "fatal: not a repo"))])
        )
        tree._stamp_path = None  # force resolution through the fake runner
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("git directory could not be located", reason)

    def test_a_successful_fetch_records_the_sync_and_never_reads_one(self):
        """A refreshed ref is fresh by definition — reading the record would be dead weight."""
        tree = self.tree(self._online())
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.note, "")
        with open(self.stamp) as fh:
            stamped_at, _, stamped_url = fh.read().strip().partition("\t")
        self.assertAlmostEqual(int(stamped_at), int(time.time()), delta=60)
        self.assertEqual(stamped_url, self.CANONICAL)

    def test_a_failed_fetch_records_nothing(self):
        """Only contact with the remote may write the record it is evidence of."""
        self.tree(self._offline()).prepare()
        self.assertFalse(os.path.exists(self.stamp))

    def test_a_sync_whose_remote_cannot_be_named_records_nothing(self):
        """A record that cannot say where it came from certifies nothing, so skip it."""
        tree = self.tree(
            self._online()[:4] + [(["remote", "get-url"], (128, b"", "fatal: No such remote"))]
        )
        self.assertIsNone(tree.prepare())
        self.assertFalse(os.path.exists(self.stamp))

    def test_an_unwritable_git_dir_does_not_crash_the_gate(self):
        """A read-only git dir costs the NEXT offline run its fallback, nothing more."""
        tree = self.tree(self._online())
        tree._stamp_path = os.path.join(self.gitdir, "no-such-dir", V.SYNC_STAMP_NAME)
        self.assertIsNone(tree.prepare())

    def test_failed_fetch_with_no_cached_ref_is_unavailable(self):
        tree = self.tree(
            [
                (["rev-parse", "--is-shallow-repository"], (0, b"false\n", "")),
                (["fetch"], (128, b"", "fatal: Could not resolve host: github.com")),
                (["show-ref", "--verify"], (1, b"", "")),
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
                (["show-ref", "--verify"], (1, b"", "")),
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
                (["show-ref", "--verify"], (1, b"", "")),
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
        """Go offline: the URL `origin` names is unchanged, the remote is unreachable.

        Repointing `origin` elsewhere would be a different remote, not a lost network —
        and the gate now tells those apart.
        """
        shutil.move(self.origin, self.origin + ".offline")

    def _sync_stamp(self):
        return V.GitPublishedTree(repo=self.work).stamp_path

    def _record_sync(self, days_ago=0):
        """Stand in for a successful gate run `days_ago` back, against this `origin`."""
        url = self.git(self.work, "remote", "get-url", "origin").decode("utf-8").strip()
        with open(self._sync_stamp(), "w") as fh:
            fh.write("%d\t%s\n" % (int(time.time() - days_ago * 86400), url))

    def test_unreachable_origin_falls_back_to_the_cached_ref(self):
        """Real fetch failure, recent sync on record: still compares, and says so."""
        self.assertIsNone(self.tree().prepare())  # an online run records the sync
        self._break_origin()
        with open(self.body, "wb") as fh:
            fh.write(b"edited body\n")
        tree = self.tree()
        self.assertIsNone(tree.prepare())
        self.assertIn("could not be refreshed", tree.note)
        self.assertIn("last synced", tree.note)
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

    def test_unreachable_origin_with_a_long_unsynced_cache_is_red(self):
        """Last successful sync past the limit: red, and it does not blame the version.

        An offline stretch this long is exactly the case the fallback must not survive:
        `main` may have been published to any number of times unseen.
        """
        self._republish(b"republished body\n", 0)
        self.assertIsNone(self.tree().prepare())  # synced once...
        self._record_sync(days_ago=30)  # ...and then 30 days of no contact
        self._break_origin()
        # local still ships the OLD body, so a real divergence exists that must not be
        # reported as a missing bump
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertIn("synced it 30.00 days ago", text)
        self.assertNotIn("plugins/alpha", text)

    def test_unreachable_origin_with_a_future_dated_sync_record_is_red(self):
        """A skewed clock must not launder a stale cache into a green comparison."""
        self._record_sync(days_ago=-3650)
        self._break_origin()
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertIn("in the FUTURE", text)
        self.assertNotIn("plugins/alpha", text)

    def test_unreachable_origin_in_a_clone_that_never_synced_is_red(self):
        """`git clone` leaves no record of when it populated the tracking ref.

        Measured on git 2.55.0: a clone writes neither a reflog entry for
        `refs/remotes/origin/main` nor a FETCH_HEAD, and a FAILED fetch truncates and
        re-dates FETCH_HEAD anyway — so a clone that has never run this gate online has
        nothing that dates its cache, and unproven freshness is red. One online run fixes
        it, which is what the message says.
        """
        self.assertFalse(os.path.exists(self._sync_stamp()))
        self._break_origin()
        with open(self.body, "wb") as fh:
            fh.write(b"republished body\n")
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("no record of ever syncing it", text)
        self.assertNotIn("plugins/alpha", text)

    def _fork_of_origin(self):
        """A second remote carrying the tree the working copy already ships."""
        fork = os.path.join(self.root, "fork")
        shutil.copytree(self.origin, fork)
        return fork

    def test_a_sync_earned_from_another_remote_does_not_certify_the_cache(self):
        """The stamp must say WHAT it certifies, not merely that contact happened.

        A fetch from a fork succeeds, so it mints a freshness record — and the cached ref
        it left behind is the fork's tree, which the canonical remote never wrote. Seven
        days of offline greens against that ref is the same "green when it cannot measure"
        the fallback exists to prevent.
        """
        fork = self._fork_of_origin()
        self._republish(b"republished body\n", 0)  # canonical moves; local still ships the old body

        self.git(self.work, "remote", "set-url", "origin", "file://" + fork)
        lines = []
        self.assertEqual(  # the disclosed wrong-remote hazard: online, this reads green
            V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append), 0,
            "\n".join(lines),
        )

        self.git(self.work, "remote", "set-url", "origin", "file://" + self.origin)
        self._break_origin()
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("earned from", text)
        self.assertIn("NOT evidence of a missing version bump", text)

    def test_a_sync_record_in_the_older_bare_timestamp_format_is_not_honoured(self):
        """A record that cannot name the remote it came from is exactly the certificate
        the fork case says must not be honoured, so the upgrade does not grandfather it."""
        with open(self._sync_stamp(), "w") as fh:
            fh.write("%d\n" % int(time.time()))
        self._break_origin()
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 1, text)
        self.assertIn("unreadable", text)

    def test_a_successful_fetch_records_the_sync(self):
        """The stamp is the gate's own, because git keeps no equivalent."""
        self.assertFalse(os.path.exists(self._sync_stamp()))
        self.assertIsNone(self.tree().prepare())
        with open(self._sync_stamp()) as fh:
            stamped_at, _, stamped_url = fh.read().strip().partition("\t")
        self.assertAlmostEqual(int(stamped_at), int(time.time()), delta=60)
        self.assertEqual(stamped_url, self.origin)  # what the clone set `origin` to

    def test_the_sync_stamp_lives_in_the_git_common_dir(self):
        """Linked worktrees share the tracking ref, so they must share its sync record."""
        self.assertEqual(
            self._sync_stamp(),
            os.path.join(self.work, ".git", V.SYNC_STAMP_NAME),
        )

    def _shadowed_divergence(self, kind):
        """Run the gate with a local `kind` named `origin/main` pinned pre-publish.

        `origin` publishes a body the working tree does not ship, under an unmoved
        version — a genuine violation, visible only through the remote-tracking ref.
        """
        shadowed = self.git(
            self.work, "rev-parse", "refs/remotes/origin/main"
        ).decode("ascii").strip()
        self._republish(b"republished body\n", 0)
        self.git(self.work, kind, "origin/main", shadowed)
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        return rc, "\n".join(lines)

    def test_a_local_branch_shadowing_origin_main_is_not_what_gets_compared(self):
        """`origin/main` is AMBIGUOUS: git resolves `refs/heads/<name>` BEFORE
        `refs/remotes/<name>`, and `--quiet` swallows the ambiguity warning.

        A local branch named `origin/main` (a mistyped `git fetch origin main:origin/main`,
        or `git switch -c origin/main`) therefore becomes the published tree this gate
        compares against, while the fetch it just ran correctly updated the tracking ref
        nobody read. Pinned pre-publish it makes a real divergence vanish.
        """
        rc, text = self._shadowed_divergence("branch")
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/alpha", text)

    def test_a_tag_shadowing_origin_main_is_not_what_gets_compared(self):
        """Same shadowing, one rung higher: `refs/tags/<name>` outranks `refs/heads/`."""
        rc, text = self._shadowed_divergence("tag")
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/alpha", text)

    def test_a_recently_synced_cache_under_a_quiet_main_is_not_red(self):
        """Freshness is contact with the remote, not the tip commit's date (card 3b2e).

        `main` published 30 days ago and has been quiet since; this clone synced it
        seconds ago and then lost the network. The cache is a perfectly accurate reading
        of what is published, and a gate that calls it stale is a false red.
        """
        self._republish(b"republished body\n", 30)
        with open(self.body, "wb") as fh:
            fh.write(b"republished body\n")  # local matches published exactly
        self.assertIsNone(self.tree().prepare())  # an online run: records the sync
        self._break_origin()  # ...and now the machine is offline
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.tree(), out=lines.append)
        text = "\n".join(lines)
        self.assertEqual(rc, 0, text)
        self.assertIn("could not be refreshed", text)
        self.assertIn("last synced", text)

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

    def test_a_local_branch_named_the_full_refname_is_not_the_published_tree(self):
        """A full refname is not self-verifying.

        `rev-parse --verify` applies all six resolution rules, so with the tracking ref
        absent a local branch literally named `refs/remotes/origin/main` resolves as
        `refs/heads/refs/remotes/origin/main` and becomes the tree this gate compares
        against. `show-ref --verify` matches the literal ref path and nothing else.
        """
        poisoned = self.git(
            self.work, "rev-parse", V.PUBLISHED_FULL_REF
        ).decode("ascii").strip()
        self.git(self.work, "branch", V.PUBLISHED_FULL_REF, poisoned)
        self.git(self.work, "remote", "remove", "origin")
        self.git(self.work, "update-ref", "-d", V.PUBLISHED_FULL_REF)

        tree = self.tree()
        reason = tree.prepare()
        self.assertIsNotNone(reason)
        self.assertIn("could not be resolved", reason)
        # ...and the shadow was never read as the published sha, which `index()` and
        # `plugin_json()` would otherwise still reach for.
        self.assertIsNone(tree._sha)


class VersionOrdering(unittest.TestCase):
    def test_numeric_not_lexical(self):
        self.assertGreater(V.version_key("1.10.0"), V.version_key("1.9.0"))

    def test_shorter_tuple_pads_with_zeros(self):
        self.assertEqual(V.version_key("2.4"), V.version_key("2.4.0"))
        self.assertGreater(V.version_key("1.0.1"), V.version_key("1.0"))

    def test_unorderable_versions_have_no_key(self):
        for raw in ("2.4.0-beta", "v1.0.0", "1..0", "", "1.-1.0"):
            self.assertIsNone(V.version_key(raw), raw)


class BaseStage(ComparisonBase):
    """The second stage: a bundle that differs from origin/dev must outrank dev's version.

    Scenario: main publishes beta 2.3.4; dev already carries another change to beta shipped
    as 2.4.0; this PR changes beta differently and claims some version.
    """

    FakeTree = MainEntryPoint.FakeTree

    def setUp(self):
        super().setUp()
        self.dev_files = dict(self.published_files)
        self.dev_files["plugins/beta/README.md"] = b"# beta\n\ndev change\n"
        self.dev_files["plugins/beta/.claude-plugin/plugin.json"] = plugin_json_bytes("beta", "2.4.0")
        self.write_local("plugins/beta/README.md", b"# beta\n\nthis PR's change\n")

    def run_main(self, base_tree):
        lines = []
        rc = V.main(
            plugins_dir=self.plugins,
            tree=self.FakeTree(self.published_files),
            base_tree=base_tree,
            out=lines.append,
        )
        return rc, "\n".join(lines)

    def test_same_version_as_dev_is_red(self):
        self.bump("beta", "2.4.0")
        rc, text = self.run_main(self.FakeTree(self.dev_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("plugins/beta", text)
        self.assertIn("origin/dev", text)
        self.assertIn("2.4.0", text)
        self.assertIn("already ships", text)

    def test_version_above_dev_is_green(self):
        self.bump("beta", "2.5.0")
        rc, text = self.run_main(self.FakeTree(self.dev_files))
        self.assertEqual(rc, 0, text)
        self.assertIn("origin/main", text)
        self.assertIn("origin/dev", text)

    def test_version_below_dev_but_above_main_is_red(self):
        self.bump("beta", "2.3.9")
        rc, text = self.run_main(self.FakeTree(self.dev_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("2.3.9", text)
        self.assertIn("2.4.0", text)

    def test_identical_to_dev_needs_nothing_from_this_stage(self):
        self.write_local("plugins/beta/README.md", b"# beta\n\ndev change\n")
        self.bump("beta", "2.4.0")
        rc, text = self.run_main(self.FakeTree(self.dev_files))
        self.assertEqual(rc, 0, text)

    def test_plugin_absent_on_dev_is_skipped(self):
        self.bump("beta", "2.4.0")
        dev = {k: v for k, v in self.dev_files.items() if not k.startswith("plugins/beta/")}
        rc, text = self.run_main(self.FakeTree(dev))
        self.assertEqual(rc, 0, text)

    def test_unorderable_version_is_red(self):
        self.bump("beta", "2.5.0-rc1")
        rc, text = self.run_main(self.FakeTree(self.dev_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("cannot be ordered", text)

    def test_unreachable_dev_is_red_and_names_it(self):
        self.bump("beta", "2.5.0")
        rc, text = self.run_main(self.FakeTree(self.dev_files, reason="origin/dev could not be resolved"))
        self.assertEqual(rc, 1, text)
        self.assertIn("the PR base origin/dev", text)
        self.assertIn("NOT evidence of a missing version bump", text)

    def test_dev_note_is_surfaced(self):
        self.bump("beta", "2.5.0")
        rc, text = self.run_main(self.FakeTree(self.dev_files, note="using a cached origin/dev"))
        self.assertEqual(rc, 0, text)
        self.assertIn("cached origin/dev", text)

    def test_unreadable_dev_tree_is_red_not_a_traceback(self):
        class Broken(self.FakeTree):
            def index(self):
                raise RuntimeError("git archive origin/dev failed: link escapes")

        self.bump("beta", "2.5.0")
        rc, text = self.run_main(Broken(self.dev_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("link escapes", text)
        self.assertIn("NOT evidence of a missing version bump", text)

    def test_unreadable_main_tree_is_red_not_a_traceback(self):
        class Broken(self.FakeTree):
            def index(self):
                raise RuntimeError("git ls-tree origin/main failed: bad object")

        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=Broken(self.published_files), out=lines.append)
        self.assertEqual(rc, 1, "\n".join(lines))
        self.assertIn("NOT evidence of a missing version bump", "\n".join(lines))

    def test_dev_moved_past_this_tree_adds_an_update_hint(self):
        class Moved(self.FakeTree):
            def is_ancestor_of_head(self):
                return False

        self.bump("beta", "2.4.0")
        rc, text = self.run_main(Moved(self.dev_files))
        self.assertEqual(rc, 1, text)
        self.assertIn("has moved past this tree", text)

    def test_no_update_hint_when_dev_is_contained_or_unknown(self):
        class Contained(self.FakeTree):
            def is_ancestor_of_head(self):
                return True

        self.bump("beta", "2.4.0")
        for tree in (Contained(self.dev_files), self.FakeTree(self.dev_files)):
            rc, text = self.run_main(tree)
            self.assertEqual(rc, 1, text)
            self.assertNotIn("moved past", text)

    def test_no_arg_entry_point_runs_the_dev_stage(self):
        """`__main__` calls main() bare; that path must build and run the origin/dev tree too."""
        built = []

        def factory(branch=V.PUBLISHED_BRANCH, **_):
            built.append(branch)
            return self.FakeTree(self.dev_files if branch == V.BASE_BRANCH else self.published_files)

        self.bump("beta", "2.4.0")
        lines = []
        with mock.patch.object(V, "GitPublishedTree", factory), \
                mock.patch.object(V, "PLUGINS_DIR", self.plugins):
            rc = V.main(out=lines.append)
        self.assertEqual(sorted(built), ["dev", "main"])
        self.assertEqual(rc, 1, "\n".join(lines))
        self.assertIn("origin/dev", "\n".join(lines))

    def test_without_a_base_tree_the_stage_does_not_run(self):
        self.bump("beta", "2.4.0")
        lines = []
        rc = V.main(plugins_dir=self.plugins, tree=self.FakeTree(self.published_files), out=lines.append)
        self.assertEqual(rc, 0, "\n".join(lines))


class BranchParameterisedTree(unittest.TestCase):
    """GitPublishedTree(branch="dev") reads and records origin/dev, never origin/main."""

    def test_dev_tree_fetches_and_resolves_dev(self):
        calls = []

        def run(args):
            calls.append(args)
            if args[0] == "rev-parse" and args[1] == "--verify":
                return 0, b"d" * 40 + b"\n", ""
            if args[:2] == ["remote", "get-url"]:
                return 0, b"file:///origin\n", ""
            return 0, b"false\n", ""

        gitdir = tempfile.mkdtemp(prefix="check-version-bump-dev-")
        self.addCleanup(shutil.rmtree, gitdir, True)
        tree = V.GitPublishedTree(branch="dev", run=run, stamp_path=os.path.join(gitdir, "s"))
        self.assertIsNone(tree.prepare())
        self.assertEqual(tree.ref, "origin/dev")
        fetch = next(c for c in calls if c[0] == "fetch")
        self.assertIn("+refs/heads/dev:refs/remotes/origin/dev", fetch)
        show = next(c for c in calls if c[0] == "show-ref")
        self.assertIn("refs/remotes/origin/dev", show)
        self.assertFalse(any("main" in " ".join(c) for c in calls), calls)

    def test_ancestry_is_unknown_in_a_shallow_clone(self):
        """Shallow history cuts HEAD's parents, so "not an ancestor" would be a false hint."""
        def run(args):
            if args[0] == "merge-base":
                return 1, b"", ""
            return 0, b"true\n", ""

        self.assertIsNone(V.GitPublishedTree(branch="dev", run=run).is_ancestor_of_head())

    def test_dev_stamp_is_distinct_from_mains(self):
        def run(args):
            return 0, b".git\n", ""

        main_tree = V.GitPublishedTree(repo="/r", run=run)
        dev_tree = V.GitPublishedTree(repo="/r", run=run, branch="dev")
        self.assertEqual(main_tree.stamp_path, os.path.join("/r", ".git", V.SYNC_STAMP_NAME))
        self.assertEqual(os.path.basename(main_tree.stamp_path), "version-bump-published-sync")
        self.assertNotEqual(main_tree.stamp_path, dev_tree.stamp_path)


@unittest.skipUnless(GIT, "git is not installed")
class BaseStageIntegration(unittest.TestCase):
    """Real git: a bare origin carrying `main` (dereferenced, published) and `dev` (symlinks).

    dev is the symlink assembly over primitives-core/, as the real one is, so its tree must be
    dereferenced before it can be compared with the local walk.
    """

    git = GitPublishedTreeIntegration.git

    def _write(self, root, rel, data):
        full = os.path.join(root, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(data)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="check-version-bump-base-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        os.makedirs(self.home)
        with open(os.path.join(self.home, "gitconfig"), "w") as fh:
            fh.write("")

        manifest = "plugins/alpha/.claude-plugin/plugin.json"
        seed = os.path.join(self.root, "seed")
        os.makedirs(seed)
        self.git(seed, "init", "-q", "-b", "main")
        self._write(seed, manifest, plugin_json_bytes("alpha", "0.1.0"))
        self._write(seed, "plugins/alpha/skills/shared/SKILL.md", b"published body\n")
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "publish: fixture")
        self.git(seed, "checkout", "-qb", "dev")
        shutil.rmtree(os.path.join(seed, "plugins", "alpha", "skills", "shared"))
        self.body_rel = "primitives-core/skills/shared/SKILL.md"
        self._write(seed, self.body_rel, b"another change already on dev\n")
        os.symlink(
            os.path.join("..", "..", "..", "primitives-core", "skills", "shared"),
            os.path.join(seed, "plugins", "alpha", "skills", "shared"),
        )
        self._write(seed, manifest, plugin_json_bytes("alpha", "0.2.0"))
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "dev: another PR ships 0.2.0")
        self.origin = os.path.join(self.root, "origin.git")
        subprocess.run([GIT, "clone", "-q", "--bare", seed, self.origin], check=True, timeout=60)

        # work: a PR branch cut from dev, so plugins/ is the symlink assembly
        self.work = os.path.join(self.root, "work")
        subprocess.run([GIT, "clone", "-q", "-b", "dev", self.origin, self.work], check=True, timeout=60)
        self.plugins = os.path.join(self.work, "plugins")

    def run_main(self, version, body=b"this PR's change\n"):
        self._write(self.work, "plugins/alpha/.claude-plugin/plugin.json", plugin_json_bytes("alpha", version))
        if body is not None:
            self._write(self.work, self.body_rel, body)
        lines = []
        rc = V.main(
            plugins_dir=self.plugins,
            tree=V.GitPublishedTree(repo=self.work),
            base_tree=V.GitPublishedTree(branch="dev", repo=self.work),
            out=lines.append,
        )
        return rc, "\n".join(lines)

    def test_claiming_devs_version_is_red(self):
        rc, text = self.run_main("0.2.0")
        self.assertEqual(rc, 1, text)
        self.assertIn("origin/dev", text)
        self.assertIn("plugins/alpha", text)

    def test_claiming_the_next_version_is_green(self):
        rc, text = self.run_main("0.3.0")
        self.assertEqual(rc, 0, text)

    def test_unchanged_symlink_assembly_matches_dev(self):
        """A branch equal to dev is green: dev's symlinks are compared as the bytes they reach."""
        rc, text = self.run_main("0.2.0", body=None)
        self.assertEqual(rc, 0, text)

    def test_dev_ahead_of_head_hints_to_update_the_branch(self):
        """A PR cut before dev moved: the red stands, and says to update rather than bump."""
        self.git(self.work, "reset", "-q", "--hard", "HEAD^")  # the PR predates dev's 0.2.0
        rc, text = self.run_main("0.1.5", body=b"this PR's change\n")
        self.assertEqual(rc, 1, text)
        self.assertIn("has moved past this tree", text)

    def test_no_hint_when_head_contains_dev(self):
        rc, text = self.run_main("0.2.0")
        self.assertEqual(rc, 1, text)
        self.assertNotIn("moved past", text)

    def test_escaping_symlink_on_dev_is_unmeasured_not_a_traceback(self):
        seed = os.path.join(self.root, "seed")
        os.symlink("/etc/hosts", os.path.join(seed, "escape"))
        self.git(seed, "add", "-A")
        self.git(seed, "commit", "-qm", "dev: an absolute symlink")
        self.git(seed, "push", "-q", self.origin, "dev")
        rc, text = self.run_main("0.3.0")
        self.assertEqual(rc, 1, text)
        self.assertIn("NOT evidence of a missing version bump", text)
        self.assertIn("origin/dev", text)

    def test_each_branch_keeps_its_own_sync_stamp(self):
        self.run_main("0.3.0")
        main_stamp = V.GitPublishedTree(repo=self.work).stamp_path
        dev_stamp = V.GitPublishedTree(branch="dev", repo=self.work).stamp_path
        self.assertNotEqual(main_stamp, dev_stamp)
        self.assertTrue(os.path.isfile(main_stamp))
        self.assertTrue(os.path.isfile(dev_stamp))

if __name__ == "__main__":
    unittest.main()
