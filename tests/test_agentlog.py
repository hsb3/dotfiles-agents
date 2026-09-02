"""Tests for primitives-core/hooks/_lib/agentlog.py and the contract it exists to hold.

Two halves. The first exercises the helper directly — root resolution, the
envelope, the override — against rows it really writes into a tempdir. The
second is the gate: it re-derives, from the hook sources, that there is still
exactly one append path, that no hook has grown a private writer again, and
that each stream name is bound inside the hook that name claims.

That last check is the one worth explaining. Asserting a stream name merely
*appears* somewhere in the tree cannot catch a name bound to the wrong write
site — `handoff-guard` and `handoff-surfacer` swapped would pass such a check
while mislabelling every row from both hooks. So each name is read back out of
its own hook file and compared against the hook's directory.

Stdlib-only. Every subprocess and every helper call in here writes into a
tempdir: no test may append to the real ledger under ~/.local/share.
"""

import ast
import json
import os
import re
import sys
import tempfile
import unittest

HOOKS_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
)

sys.path.insert(0, os.path.join(HOOKS_ROOT, "_lib"))
import agentlog  # noqa: E402  (path must be primed before this import)

#: hook directory -> (stream name, path-override env var).
#: Hand-written on purpose: this is the expectation the sources are checked
#: against, so deriving it from those same sources would assert nothing.
EXPECTED_STREAMS = {
    "config-custody": ("config-custody", "ATELIER_CUSTODY_LOG_PATH"),
    "context-watermark": ("context-watermark", "CONTEXT_WATERMARK_LOG_PATH"),
    "delegation-watermark": ("delegation-watermark", "DELEGATION_WATERMARK_LOG_PATH"),
    "handoff-freshness-guard": ("handoff-guard", "HANDOFF_GUARD_LOG_PATH"),
    "live-worker-git-guard": ("live-worker-git-guard", "LIVE_WORKER_GIT_GUARD_LOG_PATH"),
    "manager-package-gate": ("manager-package-gate", "MANAGER_PACKAGE_GATE_LOG_PATH"),
    "session-handoff-surfacer": ("handoff-surfacer", "HANDOFF_SURFACER_LOG_PATH"),
    "subagent-telemetry": ("delegation", "SUBAGENT_TELEMETRY_LOG_PATH"),
    "worktree-isolation": ("worktree-isolation", "WORKTREE_ISOLATION_LOG_PATH"),
}


def _hook_source(name):
    with open(os.path.join(HOOKS_ROOT, name, "hook.py"), encoding="utf-8") as fh:
        return fh.read()


def _hook_dirs():
    return sorted(
        d for d in os.listdir(HOOKS_ROOT)
        if os.path.isfile(os.path.join(HOOKS_ROOT, d, "hook.py"))
    )


class AgentLogTests(unittest.TestCase):
    """The helper itself, asserted on rows it actually wrote."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.xdg = os.path.join(self.tmp.name, "xdg")
        self._env = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self._env)))
        os.environ["XDG_DATA_HOME"] = self.xdg
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def _rows(self, path):
        with open(path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]

    # -- root ------------------------------------------------------------

    def test_root_is_partitioned_by_harness_and_plugin(self):
        self.assertEqual(
            agentlog.log_root(),
            os.path.join(self.xdg, "agent-logs", "claude-code", "atelier"),
        )

    def test_relative_xdg_data_home_is_ignored(self):
        """A relative XDG_DATA_HOME would put the ledger somewhere relative to
        the process cwd — the scattering this root exists to end."""
        os.environ["XDG_DATA_HOME"] = "relative/share"
        root = agentlog.log_root()
        self.assertTrue(os.path.isabs(root), root)
        self.assertTrue(root.startswith(os.path.expanduser("~")), root)

    def test_missing_xdg_data_home_falls_back_to_local_share(self):
        os.environ.pop("XDG_DATA_HOME", None)
        self.assertEqual(
            agentlog.log_root(),
            os.path.join(
                os.path.expanduser("~"), ".local", "share",
                "agent-logs", "claude-code", "atelier",
            ),
        )

    def test_plugin_segment_is_overridable(self):
        self.assertTrue(agentlog.log_root("kaneo").endswith(
            os.path.join("agent-logs", "claude-code", "kaneo")
        ))

    def test_override_env_wins_over_the_root(self):
        target = os.path.join(self.tmp.name, "elsewhere.jsonl")
        os.environ["SOME_LOG_PATH"] = target
        self.assertEqual(agentlog.stream_path("s", "SOME_LOG_PATH"), target)

    def test_empty_override_falls_through_to_the_root(self):
        os.environ["SOME_LOG_PATH"] = ""
        self.assertTrue(agentlog.stream_path("s", "SOME_LOG_PATH").startswith(self.xdg))

    # -- envelope --------------------------------------------------------

    def test_envelope_keys_lead_the_row(self):
        agentlog.append("demo", {"z": 1}, project="/repo/x")
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertEqual(list(row)[: len(agentlog.ENVELOPE_KEYS)],
                         list(agentlog.ENVELOPE_KEYS))
        self.assertEqual(list(row)[-1], "z")

    def test_envelope_identifies_the_producer(self):
        agentlog.append("demo", {}, project="/repo/x")
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertEqual(row["v"], agentlog.SCHEMA_VERSION)
        self.assertEqual(row["plugin"], "atelier")
        self.assertEqual(row["harness"], "claude-code")
        self.assertEqual(row["stream"], "demo")
        self.assertEqual(row["project"], "/repo/x")

    def test_ts_is_iso_8601_utc_with_milliseconds(self):
        agentlog.append("demo", {})
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertRegex(row["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")

    def test_rows_sort_lexically_in_chronological_order(self):
        """The property the old epoch float did not have once stringified."""
        for _ in range(3):
            agentlog.append("demo", {})
        stamps = [r["ts"] for r in self._rows(
            os.path.join(agentlog.log_root(), "demo.jsonl")
        )]
        self.assertEqual(stamps, sorted(stamps))

    def test_caller_cannot_overwrite_an_envelope_key(self):
        """A call site still stamping its own epoch `ts` must not be able to
        reintroduce one into a field consumers now parse as ISO-8601."""
        agentlog.append("demo", {"ts": 1754668628.6, "plugin": "not-atelier"})
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertEqual(row["plugin"], "atelier")
        self.assertRegex(row["ts"], r"^\d{4}-")

    def test_payload_survives_beside_the_envelope(self):
        agentlog.append("demo", {"denied": False, "path": "Makefile"})
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertFalse(row["denied"])
        self.assertEqual(row["path"], "Makefile")

    def test_unserializable_payload_still_writes_a_row(self):
        agentlog.append("demo", {"obj": object()})
        row = self._rows(os.path.join(agentlog.log_root(), "demo.jsonl"))[0]
        self.assertIsInstance(row["obj"], str)

    # -- best-effort -----------------------------------------------------

    def test_unwritable_root_never_raises(self):
        """Logging must never break the hook it logs for."""
        blocker = os.path.join(self.tmp.name, "blocker")
        with open(blocker, "w") as fh:
            fh.write("not a directory")
        os.environ["SOME_LOG_PATH"] = os.path.join(blocker, "nested", "x.jsonl")
        agentlog.append("demo", {"a": 1}, override_env="SOME_LOG_PATH")

    def test_make_logger_binds_stream_and_project(self):
        log = agentlog.make_logger("bound", project="/repo/y")
        log({"n": 1})
        log({"n": 2})
        rows = self._rows(os.path.join(agentlog.log_root(), "bound.jsonl"))
        self.assertEqual([r["n"] for r in rows], [1, 2])
        self.assertEqual({r["stream"] for r in rows}, {"bound"})
        self.assertEqual({r["project"] for r in rows}, {"/repo/y"})

    # -- project resolution ----------------------------------------------

    def test_project_prefers_the_env_anchor_over_payload_cwd(self):
        os.environ["CLAUDE_PROJECT_DIR"] = "/anchor"
        self.assertEqual(agentlog.resolve_project("/payload"), "/anchor")

    def test_project_is_none_when_unresolvable(self):
        """Unlike the per-hook resolvers this replaced, an unknown project is
        no longer a reason to skip the row — it is just a null field."""
        self.assertIsNone(agentlog.resolve_project())


class OneAppendPathTests(unittest.TestCase):
    """The gate: one helper, one envelope, one root — re-derived from source."""

    def test_no_hook_defines_its_own_writer(self):
        offenders = []
        for name in _hook_dirs():
            src = _hook_source(name)
            for pattern in (r"def _log\(", r"def _append_row\(", r"def _write_log\("):
                if re.search(pattern, src):
                    offenders.append("{0}: {1}".format(name, pattern))
        self.assertEqual(offenders, [], "private writers bypass the envelope")

    def test_no_hook_appends_to_a_file_itself(self):
        """An append mode open() outside the helper is a write site the
        envelope cannot reach."""
        offenders = [
            name for name in _hook_dirs()
            if re.search(r"open\([^)]*['\"]a['\"]", _hook_source(name))
        ]
        self.assertEqual(offenders, [])

    def test_no_hook_defaults_into_the_project_tree(self):
        """The defect this closed: ledgers landing in whatever repo the
        session happened to be in."""
        offenders = [
            name for name in _hook_dirs()
            if re.search(r"['\"]logs['\"]\s*,\s*LOG_", _hook_source(name))
            or "/logs/" in _hook_source(name)
        ]
        self.assertEqual(offenders, [])

    def test_every_logging_hook_imports_the_shared_helper(self):
        for name, (stream, _env) in sorted(EXPECTED_STREAMS.items()):
            with self.subTest(hook=name):
                src = _hook_source(name)
                self.assertIn("import agentlog", src)
                self.assertIn('"..", "_lib"', src)

    def test_stream_names_are_bound_inside_the_hook_that_claims_them(self):
        """Re-derived per site: a name bound in the wrong hook (guard and
        surfacer swapped) is exactly what a tree-wide grep cannot catch."""
        for name, (stream, env) in sorted(EXPECTED_STREAMS.items()):
            with self.subTest(hook=name):
                src = _hook_source(name)
                found = re.findall(r'^LOG_STREAM = "([^"]+)"', src, re.M)
                self.assertEqual(found, [stream])
                found_env = re.findall(r'^LOG_PATH_ENV = "([^"]+)"', src, re.M)
                self.assertEqual(found_env, [env])

    def test_expected_streams_covers_every_hook_that_logs(self):
        """Add a logging hook, add it here — otherwise its stream name is
        bound by nothing and this suite silently stops covering it."""
        logging_hooks = {
            name for name in _hook_dirs()
            if re.search(r"^LOG_STREAM = ", _hook_source(name), re.M)
        }
        self.assertEqual(logging_hooks, set(EXPECTED_STREAMS))

    def test_helper_is_stdlib_only(self):
        """Zero-install is an invariant: a hook must run with nothing to pip."""
        with open(os.path.join(HOOKS_ROOT, "_lib", "agentlog.py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        # Parsed, not grepped: a prose line beginning "from its filename" is
        # not an import, and a regex here reported one.
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                modules.add((node.module or "").split(".")[0])
        self.assertEqual(modules - {"json", "os", "datetime"}, set())

    def test_helper_is_a_member_of_the_atelier_assembly(self):
        """The hooks import it as `../_lib`, so an assembly that ships the
        hooks without it installs seven hooks that cannot start."""
        link = os.path.join(
            os.path.dirname(__file__), "..", "plugins", "atelier", "hooks", "_lib",
        )
        self.assertTrue(os.path.islink(link), "plugins/atelier/hooks/_lib is not a symlink")
        self.assertTrue(
            os.path.isfile(os.path.join(link, "agentlog.py")),
            "plugins/atelier/hooks/_lib does not resolve to the helper",
        )

    def test_every_atelier_hook_can_reach_the_helper_through_the_assembly(self):
        """Resolve `../_lib/agentlog.py` from each hook's installed path, the
        way the hook itself will at runtime."""
        base = os.path.join(os.path.dirname(__file__), "..", "plugins", "atelier", "hooks")
        for name in sorted(EXPECTED_STREAMS):
            with self.subTest(hook=name):
                helper = os.path.join(base, name, "..", "_lib", "agentlog.py")
                self.assertTrue(os.path.isfile(helper), helper)


if __name__ == "__main__":
    unittest.main()
