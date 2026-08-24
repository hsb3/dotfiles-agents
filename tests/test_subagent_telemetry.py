"""Tests for primitives-core/hooks/subagent-telemetry/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, no
stdout ever, env-configured log path) against a fixture that mirrors Claude
Code's real on-disk layout:

    <projects>/<slug>/<session_id>.jsonl                       parent transcript
    <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
    <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

Sidecar key names below are the ones observed on real files (agentType,
description, toolUseId, spawnDepth, model, parentAgentId). Stdlib-only;
fixtures build into a tempdir per test, and the subprocess environment is
built from scratch with only PATH inherited.
"""

import datetime as dt
import importlib.util
import itertools
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "subagent-telemetry", "hook.py",
)

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "primitives-core", "hooks", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)


def _load_hook_module():
    """The hook loaded in-process, for the ONE thing the subprocess cannot
    report: the value of a module-level bound. Every behavioural test still
    runs the hook the way Claude Code does, as a subprocess."""
    spec = importlib.util.spec_from_file_location(
        "subagent_telemetry_under_test", os.path.abspath(HOOK_PATH))
    module = importlib.util.module_from_spec(spec)
    # Bytecode caching off for this import only: it would otherwise drop a
    # __pycache__ directory inside the shipped hook tree on every test run.
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


HOOK_MODULE = _load_hook_module()

_SEQ = itertools.count()

# Parent-session values. Any of these showing up in a ledger row means the hook
# is describing the foreman instead of the delegation (the TASK-036 defect).
PARENT_MODEL = "claude-parent-model-9"
PARENT_INPUT = 1
PARENT_CACHE_CREATION = 100000
PARENT_CACHE_READ = 900000
PARENT_CTX = PARENT_INPUT + PARENT_CACHE_CREATION + PARENT_CACHE_READ

SUBAGENT_MODEL = "claude-sonnet-5"
SUB_INPUT = 2
SUB_CACHE_CREATION = 2998
SUB_CACHE_READ = 32487
SUBAGENT_CTX = SUB_INPUT + SUB_CACHE_CREATION + SUB_CACHE_READ


def _iso(moment):
    """The exact ISO-8601 UTC millisecond shape agentlog stamps."""
    return moment.astimezone(dt.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def _ago(seconds):
    """An ISO-8601 UTC ms timestamp `seconds` in the past.

    Ageing lives in the FIXTURE, never the system clock: transcript stamps and
    sidecar mtimes are written into the past so "older than the threshold" is
    deterministic on any machine.
    """
    return _iso(dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=seconds))


def _parse(stamp):
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _session_id():
    return "subagent-telemetry-session-{0}".format(next(_SEQ))


def _assistant(model, input_tokens, cache_creation, cache_read):
    """One assistant transcript line carrying a usage block, as Claude Code writes it."""
    return {
        "type": "assistant",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": input_tokens,
                "cache_creation_input_tokens": cache_creation,
                "cache_read_input_tokens": cache_read,
                "output_tokens": 4555,
            },
        },
    }


def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _read_rows(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]


class SubagentTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "delegation.jsonl")
        self.session_id = _session_id()
        self.projects = os.path.join(self.tmp.name, "projects", "-slug")
        self.transcript_path = os.path.join(
            self.projects, "{0}.jsonl".format(self.session_id)
        )
        self.subagents_dir = os.path.join(self.projects, self.session_id, "subagents")
        _write_jsonl(self.transcript_path, [
            _assistant(PARENT_MODEL, PARENT_INPUT, PARENT_CACHE_CREATION, PARENT_CACHE_READ),
        ])

    # -- fixtures ------------------------------------------------------

    def _write_sidecar(self, agent_id, meta):
        os.makedirs(self.subagents_dir, exist_ok=True)
        path = os.path.join(self.subagents_dir, "agent-{0}.meta.json".format(agent_id))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(meta if isinstance(meta, str) else json.dumps(meta))
        return path

    def _write_subagent_transcript(self, agent_id, model=SUBAGENT_MODEL):
        path = os.path.join(self.subagents_dir, "agent-{0}.jsonl".format(agent_id))
        _write_jsonl(path, [
            _assistant(model, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        return path

    def _write_stamped_transcript(self, agent_id, lines):
        """A subagent transcript whose lines are given verbatim — the shape the
        start-time helper reads (walk forward to the first usable `timestamp`)."""
        path = os.path.join(self.subagents_dir, "agent-{0}.jsonl".format(agent_id))
        _write_jsonl(path, lines)
        return path

    def _age(self, path, seconds):
        """Push a file's mtime `seconds` into the past; returns the new mtime."""
        when = os.path.getmtime(path) - seconds
        os.utime(path, (when, when))
        return os.path.getmtime(path)

    def _pending_delegation(self, agent_id, age_seconds, agent_type="atelier:builder"):
        """A delegation that started `age_seconds` ago and has NOT stopped."""
        self._delegation(agent_id, agent_type=agent_type, transcript=False)
        started_at = _ago(age_seconds)
        self._write_stamped_transcript(agent_id, [
            {"type": "user", "timestamp": started_at, "message": {"role": "user"}},
            _assistant(SUBAGENT_MODEL, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        return started_at

    def _sibling_session(self, suffix="rehomed"):
        """Another session dir under the SAME slug — its own parent transcript
        and an (initially empty) `subagents/` dir. This is what a `/clear`
        mid-delegation leaves behind: the agent's transcript is re-homed here
        while its sidecar stays in the old session's directory.

        Returns (session_id, transcript_path, subagents_dir).
        """
        session_id = "{0}-{1}".format(self.session_id, suffix)
        transcript_path = os.path.join(self.projects, "{0}.jsonl".format(session_id))
        _write_jsonl(transcript_path, [
            _assistant(PARENT_MODEL, PARENT_INPUT, PARENT_CACHE_CREATION,
                       PARENT_CACHE_READ),
        ])
        subagents_dir = os.path.join(self.projects, session_id, "subagents")
        os.makedirs(subagents_dir, exist_ok=True)
        return session_id, transcript_path, subagents_dir

    def _put_sidecar(self, subagents_dir, agent_id, agent_type="atelier:builder"):
        path = os.path.join(subagents_dir, "agent-{0}.meta.json".format(agent_id))
        os.makedirs(subagents_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"agentType": agent_type, "spawnDepth": 1}))
        return path

    def _stop_payload(self, stop_hook_active=False):
        """A real `Stop` payload: no agent_id, no agent_type (measured shape)."""
        return {
            "session_id": self.session_id,
            "transcript_path": self.transcript_path,
            "cwd": self.cwd,
            "hook_event_name": "Stop",
            "stop_hook_active": stop_hook_active,
        }

    def _seed_ledger(self, rows):
        """Pre-existing ledger content, as another run would have left it."""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            for row in rows:
                fh.write((row if isinstance(row, str) else json.dumps(row)) + "\n")

    def _stall_rows(self):
        return [r for r in _read_rows(self.log_path)
                if r.get("event") == "stall" and r.get("session_id") == self.session_id]

    def _delegation_rows(self):
        return [r for r in _read_rows(self.log_path)
                if "event" not in r and "error" not in r]

    def _delegation(self, agent_id, agent_type="atelier:builder", model=None,
                    transcript=True):
        """A real delegation: sidecar + (optionally) the subagent's transcript."""
        meta = {
            "agentType": agent_type,
            "description": "Do a bounded slice",
            "toolUseId": "toolu_{0}".format(agent_id),
            "spawnDepth": 1,
        }
        if model is not None:
            meta["model"] = model
        self._write_sidecar(agent_id, meta)
        if transcript:
            self._write_subagent_transcript(agent_id)
        return agent_id

    def _payload(self, agent_id, agent_type="", transcript_path=None,
                 session_id=None):
        # agent_type is "" by default: that is what real SubagentStop payloads
        # carry in the large majority of cases (defect D1).
        return {
            "session_id": self.session_id if session_id is None else session_id,
            "transcript_path": self.transcript_path
            if transcript_path is None else transcript_path,
            "cwd": self.cwd,
            "hook_event_name": "SubagentStop",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "permission_mode": "default",
        }

    def _run_hook(self, stdin_text, extra_env=None):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # Sandbox the partitioned log root: a run that ever loses its
            # path override must not append synthetic rows to the real
            # ~/.local/share/agent-logs ledger. HOME too — expanduser("~")
            # falls back to the passwd entry when HOME is unset.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": os.path.join(self.tmp.name, "xdg"),
            "SUBAGENT_TELEMETRY_LOG_PATH": self.log_path,
        }
        # CLAUDE_PROJECT_DIR deliberately absent -> a stray write would land in
        # cwd, which test_no_stray_writes_outside_configured_paths checks.
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _run(self, payload, extra_env=None):
        result = self._run_hook(json.dumps(payload), extra_env=extra_env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "", "telemetry hook must be silent")
        return result

    # -- the delegation's own values, not the parent's ---------------------

    def test_agent_type_comes_from_sidecar(self):
        self._delegation("a1111111111111111", agent_type="atelier:scout")
        self._run(self._payload("a1111111111111111"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:scout")

    def test_model_and_ctx_tokens_are_the_subagents_not_the_parents(self):
        self._delegation("a2222222222222222")
        self._run(self._payload("a2222222222222222"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["model"], SUBAGENT_MODEL)
        self.assertEqual(row["ctx_tokens"], SUBAGENT_CTX)
        # The parent transcript is a live, readable file with different values;
        # picking it up is exactly defect D2.
        self.assertNotEqual(row["model"], PARENT_MODEL)
        self.assertNotEqual(row["ctx_tokens"], PARENT_CTX)

    def test_sidecar_model_override_wins_over_transcript_model(self):
        # A dispatch-time model override is recorded on the sidecar (observed
        # values: "opus", "sonnet"). It is the delegation decision, so it wins.
        self._delegation("a3333333333333333", model="opus")
        self._run(self._payload("a3333333333333333"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["model"], "opus")

    def test_row_carries_the_payload_agent_id_and_session(self):
        self._delegation("a4444444444444444")
        self._run(self._payload("a4444444444444444"))
        row = _read_rows(self.log_path)[0]
        self.assertEqual(row["agent_id"], "a4444444444444444")
        self.assertEqual(row["session_id"], self.session_id)

    # -- exactly N rows for N delegations ----------------------------------

    def test_n_delegations_produce_exactly_n_rows(self):
        real = ["a000000000000000{0}".format(i) for i in range(1, 4)]
        for i, agent_id in enumerate(real):
            self._delegation(agent_id, agent_type="atelier:builder-{0}".format(i))
        # SubagentStop also fires for agents that never get a subagents/ entry;
        # those events are what inflate the ledger ~10x (defect D3).
        phantom = ["b000000000000000{0}".format(i) for i in range(1, 8)]

        for agent_id in real + phantom:
            self._run(self._payload(agent_id))

        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), len(real), [r.get("agent_id") for r in rows])
        self.assertEqual([r["agent_id"] for r in rows], real)
        for row in rows:
            self.assertTrue(row["agent_type"], "every emitted row needs an agent_type")
            self.assertEqual(row["model"], SUBAGENT_MODEL)
            self.assertEqual(row["ctx_tokens"], SUBAGENT_CTX)

    # -- error paths: fail open, never a partial row ------------------------

    def test_no_subagents_directory_at_all(self):
        self._run(self._payload("a5555555555555555"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_subagents_directory_present_but_empty(self):
        os.makedirs(self.subagents_dir, exist_ok=True)
        self._run(self._payload("a6666666666666666"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_sidecar_is_malformed_json(self):
        self._write_sidecar("a7777777777777777", "{not: valid json,,,")
        self._write_subagent_transcript("a7777777777777777")
        self._run(self._payload("a7777777777777777"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_sidecar_is_json_but_not_an_object(self):
        self._write_sidecar("a8888888888888888", "[1, 2, 3]")
        self._run(self._payload("a8888888888888888"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_sidecar_missing_agent_type_falls_back_to_payload(self):
        self._write_sidecar("a9999999999999999", {"description": "x", "toolUseId": "t"})
        self._write_subagent_transcript("a9999999999999999")
        self._run(self._payload("a9999999999999999", agent_type="atelier:reviewer"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:reviewer")

    def test_sidecar_missing_agent_type_with_no_fallback_drops_the_row(self):
        self._write_sidecar("aaaaaaaaaaaaaaaaa", {"description": "x", "toolUseId": "t"})
        self._write_subagent_transcript("aaaaaaaaaaaaaaaaa")
        self._run(self._payload("aaaaaaaaaaaaaaaaa", agent_type=""))
        self.assertEqual(_read_rows(self.log_path), [])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root bypasses file permissions")
    def test_sidecar_present_but_unreadable(self):
        path = self._write_sidecar("abbbbbbbbbbbbbbbb", {"agentType": "atelier:builder"})
        self._write_subagent_transcript("abbbbbbbbbbbbbbbb")
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, stat.S_IRUSR | stat.S_IWUSR)
        self._run(self._payload("abbbbbbbbbbbbbbbb"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_subagent_transcript_missing_still_emits_the_delegation(self):
        # The sidecar proves the delegation happened; only usage is unknown.
        self._delegation("acccccccccccccccc", transcript=False)
        self._run(self._payload("acccccccccccccccc"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")
        self.assertIsNone(rows[0]["ctx_tokens"])
        self.assertIsNone(rows[0]["model"])

    def test_subagent_transcript_is_garbage(self):
        self._delegation("addddddddddddddddd", transcript=False)
        path = os.path.join(self.subagents_dir, "agent-addddddddddddddddd.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not json at all\n\x00\x01\n")
        self._run(self._payload("addddddddddddddddd"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")
        self.assertIsNone(rows[0]["ctx_tokens"])

    def test_missing_agent_id_in_payload(self):
        self._delegation("aeeeeeeeeeeeeeeee")
        payload = self._payload("aeeeeeeeeeeeeeeee")
        del payload["agent_id"]
        self._run(payload)
        self.assertEqual(_read_rows(self.log_path), [])

    def test_agent_id_cannot_escape_the_subagents_directory(self):
        self._delegation("affffffffffffffff")
        self._run(self._payload("../../../../etc/passwd"))
        self.assertEqual(_read_rows(self.log_path), [])

    def test_missing_transcript_path_in_payload(self):
        self._delegation("a0000000000000000")
        payload = self._payload("a0000000000000000")
        del payload["transcript_path"]
        self._run(payload)
        self.assertEqual(_read_rows(self.log_path), [])

    def test_garbage_stdin_writes_nothing_and_exits_zero(self):
        result = self._run_hook("not json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(_read_rows(self.log_path), [])

    def test_empty_stdin_writes_nothing_and_exits_zero(self):
        result = self._run_hook("")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(_read_rows(self.log_path), [])

    def test_debug_env_records_a_marked_error_row(self):
        # Diagnostics are opt-in so they cannot inflate the ledger's row count.
        result = self._run_hook("not json", extra_env={"SUBAGENT_TELEMETRY_DEBUG": "1"})
        self.assertEqual(result.returncode, 0)
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertIn("error", rows[0])

    # -- resolution shape ---------------------------------------------------

    def test_transcript_path_already_inside_subagents_dir(self):
        # A nested delegation's payload can point at the subagent transcript
        # itself; the sidecar dir is then that file's own directory.
        self._delegation("a1212121212121212")
        nested = os.path.join(self.subagents_dir, "agent-a1212121212121212.jsonl")
        self._run(self._payload("a1212121212121212", transcript_path=nested))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")

    def test_agent_id_with_agent_prefix_resolves(self):
        self._delegation("a1313131313131313")
        self._run(self._payload("agent-a1313131313131313"))
        rows = _read_rows(self.log_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")

    # -- D1: wall clock (started_at + duration_ms) -------------------------

    def test_started_at_comes_from_the_subagent_transcript_first_timestamp(self):
        self._delegation("ad1d1d1d1d1d1d1d1", transcript=False)
        started_at = _ago(120)
        self._write_stamped_transcript("ad1d1d1d1d1d1d1d1", [
            {"type": "user", "timestamp": started_at, "message": {"role": "user"}},
            _assistant(SUBAGENT_MODEL, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        self._run(self._payload("ad1d1d1d1d1d1d1d1"))
        row = self._delegation_rows()[0]
        self.assertEqual(row["started_at"], started_at)

    def test_duration_ms_equals_ts_minus_started_at(self):
        """D1 arithmetic, pinned: an overseer joins on agent_id and subtracts."""
        self._delegation("ad2d2d2d2d2d2d2d2", transcript=False)
        started_at = _ago(300)
        self._write_stamped_transcript("ad2d2d2d2d2d2d2d2", [
            {"type": "user", "timestamp": started_at, "message": {"role": "user"}},
            _assistant(SUBAGENT_MODEL, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        self._run(self._payload("ad2d2d2d2d2d2d2d2"))
        row = self._delegation_rows()[0]
        self.assertIsInstance(row["duration_ms"], int)
        self.assertGreaterEqual(row["duration_ms"], 300 * 1000)
        self.assertLess(row["duration_ms"], 300 * 1000 + 60 * 1000)
        derived = (_parse(row["ts"]) - _parse(row["started_at"])).total_seconds() * 1000
        self.assertAlmostEqual(derived, row["duration_ms"], delta=2000)

    def test_started_at_skips_a_leading_line_with_no_timestamp(self):
        # 4/44 real transcripts open with a `type: "fork-context-ref"` line that
        # carries no timestamp; taking line 0 blindly would yield None.
        self._delegation("ad3d3d3d3d3d3d3d3", transcript=False)
        started_at = _ago(45)
        self._write_stamped_transcript("ad3d3d3d3d3d3d3d3", [
            {"type": "fork-context-ref", "forkedFrom": "abc", "uuid": "u0"},
            {"type": "user", "timestamp": started_at, "message": {"role": "user"}},
            _assistant(SUBAGENT_MODEL, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        self._run(self._payload("ad3d3d3d3d3d3d3d3"))
        row = self._delegation_rows()[0]
        self.assertEqual(row["started_at"], started_at)

    def test_started_at_falls_back_to_sidecar_mtime(self):
        # No usable transcript timestamp at all -> sidecar mtime, which tracked
        # true dispatch to +0.1s in 9/11 real cases (and blew out in 2, which is
        # exactly why it is the fallback and not the primary).
        sidecar = self._delegation("ad4d4d4d4d4d4d4d4")
        sidecar_path = os.path.join(
            self.subagents_dir, "agent-{0}.meta.json".format(sidecar))
        mtime = self._age(sidecar_path, 600)
        self._run(self._payload("ad4d4d4d4d4d4d4d4"))
        rows = self._delegation_rows()
        self.assertEqual(len(rows), 1, "a missing start time must not drop the row")
        self.assertEqual(
            rows[0]["started_at"],
            _iso(dt.datetime.fromtimestamp(mtime, dt.timezone.utc)),
        )
        self.assertGreaterEqual(rows[0]["duration_ms"], 600 * 1000)

    def test_row_is_still_written_when_the_start_time_is_unknown(self):
        # Neither transcript nor sidecar yields anything parseable as a stamp.
        self._delegation("ad5d5d5d5d5d5d5d5", transcript=False)
        self._write_stamped_transcript("ad5d5d5d5d5d5d5d5", [
            {"type": "user", "timestamp": "not-a-timestamp"},
            {"type": "user", "timestamp": 17},
            _assistant(SUBAGENT_MODEL, SUB_INPUT, SUB_CACHE_CREATION, SUB_CACHE_READ),
        ])
        self._run(self._payload("ad5d5d5d5d5d5d5d5"))
        rows = self._delegation_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")

    # -- D7: how a reader classifies a row ---------------------------------

    def test_delegation_row_carries_no_event_key(self):
        """The reader rule, pinned: a row with NO `event` key is a delegation
        row. That is what keeps every pre-change row readable with no
        migration — they lack `event`, and lack `started_at`/`duration_ms`."""
        self._delegation("ad7d7d7d7d7d7d7d7")
        self._run(self._payload("ad7d7d7d7d7d7d7d7"))
        row = _read_rows(self.log_path)[0]
        self.assertNotIn("event", row)

    def test_a_debug_error_row_is_not_a_delegation_row(self):
        """The other row shape carrying no `event` key. The reader rule has to
        name `error` too, or an opt-in diagnostic reads as a delegation."""
        self._run_hook("not json", extra_env={"SUBAGENT_TELEMETRY_DEBUG": "1"})
        row = _read_rows(self.log_path)[0]
        self.assertNotIn("event", row)
        self.assertIn("error", row)
        self.assertEqual(self._delegation_rows(), [])

    # -- D2/D3: a stall is a queryable record ------------------------------

    def test_stop_event_reports_a_delegation_pending_past_the_threshold(self):
        started_at = self._pending_delegation("b1111111111111111", 1000,
                                              agent_type="atelier:builder")
        self._run(self._stop_payload())
        stalls = self._stall_rows()
        self.assertEqual(len(stalls), 1, _read_rows(self.log_path))
        stall = stalls[0]
        self.assertEqual(stall["event"], "stall")
        self.assertEqual(stall["session_id"], self.session_id)
        self.assertEqual(len(stall["pending"]), 1)
        entry = stall["pending"][0]
        self.assertEqual(entry["agent_id"], "b1111111111111111")
        self.assertEqual(entry["agent_type"], "atelier:builder")
        self.assertEqual(entry["started_at"], started_at)
        self.assertGreaterEqual(entry["pending_ms"], 900 * 1000)
        # A Stop is not a delegation: it must not fabricate a delegation row.
        self.assertEqual(self._delegation_rows(), [])

    def test_no_stall_row_under_the_threshold(self):
        self._pending_delegation("b2222222222222222", 60)
        self._run(self._stop_payload())
        self.assertEqual(_read_rows(self.log_path), [])

    def test_stall_threshold_is_env_overridable(self):
        self._pending_delegation("b3333333333333333", 30)
        # Default 900s would report nothing at this age...
        self._run(self._stop_payload())
        self.assertEqual(_read_rows(self.log_path), [])
        # ...the override makes the same fixture stall.
        self._run(self._stop_payload(),
                  extra_env={"SUBAGENT_TELEMETRY_STALL_SECONDS": "1"})
        stalls = self._stall_rows()
        self.assertEqual(len(stalls), 1)
        self.assertEqual(stalls[0]["pending"][0]["agent_id"], "b3333333333333333")

    def test_a_stalled_agent_is_named_once_per_tail_window(self):
        self._pending_delegation("b4444444444444444", 1000)
        self._run(self._stop_payload())
        self._run(self._stop_payload())
        self.assertEqual(len(self._stall_rows()), 1, _read_rows(self.log_path))

    def test_subagent_stop_writes_both_its_row_and_a_stall_for_a_sibling(self):
        self._delegation("b5555555555555555")
        self._pending_delegation("b6666666666666666", 1200)
        self._run(self._payload("b5555555555555555"))
        delegations = self._delegation_rows()
        self.assertEqual([r["agent_id"] for r in delegations], ["b5555555555555555"])
        stalls = self._stall_rows()
        self.assertEqual(len(stalls), 1)
        named = [e["agent_id"] for e in stalls[0]["pending"]]
        self.assertEqual(named, ["b6666666666666666"])
        self.assertNotIn("b5555555555555555", named)

    def test_stall_never_names_an_agent_that_has_no_sidecar(self):
        """Hazard 1, dissolved rather than patched: the pending universe IS the
        sidecar directory, the same predicate that gates a delegation row. A
        phantom SubagentStop (no sidecar) can neither produce a delegation row
        nor enter the pending set — one predicate, one code path.

        Mutation-checked: widening `_sidecar_keys` to accept any `agent-*` file
        makes this test red (see the transcript-only phantom below)."""
        real = ["b70000000000000{0:02d}".format(i) for i in range(1, 3)]
        for agent_id in real:
            self._pending_delegation(agent_id, 1500)
        phantom = ["c80000000000000{0:02d}".format(i) for i in range(1, 6)]
        # One phantom carries an aged TRANSCRIPT and no `.meta.json`. That is
        # the only shape where the sidecar predicate is load-bearing: a phantom
        # with no files at all is discarded for an unknown start time before
        # the predicate is ever consulted, so it would stay silent against a
        # pending universe that had been widened past the sidecar set.
        self._write_stamped_transcript(phantom[0], [
            {"type": "user", "timestamp": _ago(1500), "message": {"role": "user"}},
        ])

        for agent_id in phantom:
            self._run(self._payload(agent_id))
        self._run(self._stop_payload())

        rows = _read_rows(self.log_path)
        self.assertEqual(self._delegation_rows(), [], rows)
        named = sorted({e["agent_id"] for r in self._stall_rows() for e in r["pending"]})
        self.assertEqual(named, sorted(real))
        with open(self.log_path, encoding="utf-8") as fh:
            raw = fh.read() if rows else ""
        for agent_id in phantom:
            self.assertNotIn(agent_id, raw)

    def test_no_stall_row_when_every_sidecar_has_already_stopped(self):
        real = ["b90000000000000{0:02d}".format(i) for i in range(1, 4)]
        for agent_id in real:
            self._pending_delegation(agent_id, 1500)
        # Each one's delegation row is already in the ledger tail.
        self._seed_ledger([
            {"stream": "delegation", "session_id": self.session_id,
             "agent_id": agent_id, "agent_type": "atelier:builder"}
            for agent_id in real
        ])
        for agent_id in ["c9000000000000001", "c9000000000000002"]:
            self._run(self._payload(agent_id))
        self._run(self._stop_payload())
        self.assertEqual(self._stall_rows(), [])

    def test_a_settle_under_another_session_settles_the_agent(self):
        """REPLACES test_stopped_set_ignores_other_sessions, which pinned the
        opposite rule. After a `/clear` re-homes a live delegation, its stop
        row lands under the NEW session id while its sidecar stays under the
        OLD one — so a session-filtered settled set can never see the stop and
        the orphaned sidecar is reported pending past every threshold, forever.
        `agent_id` is globally unique, so it alone carries the join.

        Both settling shapes are checked: a delegation row (it stopped) and a
        prior stall row naming it (the dedup)."""
        self._pending_delegation("ba111111111111111", 1500)
        self._pending_delegation("ba222222222222222", 1500)
        self._seed_ledger([
            {"stream": "delegation", "session_id": "some-other-session",
             "agent_id": "ba111111111111111", "agent_type": "atelier:builder"},
            {"stream": "delegation", "event": "stall", "session_id": "some-other-session",
             "pending": [{"agent_id": "ba222222222222222"}]},
        ])
        self._run(self._stop_payload())
        self.assertEqual(self._stall_rows(), [], _read_rows(self.log_path))

    def test_stall_ages_off_the_sidecar_mtime_when_the_transcript_has_no_stamp(self):
        sidecar = os.path.join(
            self.subagents_dir, "agent-bb11111111111111.meta.json")
        self._delegation("bb11111111111111")
        self._age(sidecar, 1500)
        self._run(self._stop_payload())
        stalls = self._stall_rows()
        self.assertEqual(len(stalls), 1)
        self.assertGreaterEqual(stalls[0]["pending"][0]["pending_ms"], 900 * 1000)

    def test_stop_hook_active_payload_still_only_scans_and_stays_silent(self):
        self._pending_delegation("bc11111111111111", 1000)
        result = self._run(self._stop_payload(stop_hook_active=True))
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(self._stall_rows()), 1)

    def test_pending_entries_are_sorted_by_agent_id(self):
        for agent_id in ["bf11111111111111", "bd11111111111111", "be11111111111111"]:
            self._pending_delegation(agent_id, 1500)
        self._run(self._stop_payload())
        named = [e["agent_id"] for e in self._stall_rows()[0]["pending"]]
        self.assertEqual(named, sorted(named))

    # -- the stall scan fails open --------------------------------------

    def test_stop_event_with_no_subagents_directory_writes_nothing(self):
        result = self._run(self._stop_payload())
        self.assertEqual(result.stdout, "")
        self.assertEqual(_read_rows(self.log_path), [])

    def test_garbage_ledger_does_not_stop_the_delegation_row(self):
        self._seed_ledger(["not json at all", "\x00\x01{{{", ""])
        self._delegation("bg11111111111111")
        self._run(self._payload("bg11111111111111"))
        # Read tolerantly: the seeded junk lines are not rows.
        parsed = []
        with open(self.log_path, encoding="utf-8") as fh:
            for line in fh.read().splitlines():
                try:
                    parsed.append(json.loads(line))
                except ValueError:
                    continue
        self.assertEqual([r["agent_id"] for r in parsed], ["bg11111111111111"])
        self.assertEqual([r for r in parsed if r.get("event") == "stall"], [])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root bypasses file permissions")
    def test_unreadable_ledger_exits_zero_and_stays_silent(self):
        self._seed_ledger([])
        os.chmod(self.log_path, 0)
        self.addCleanup(os.chmod, self.log_path, stat.S_IRUSR | stat.S_IWUSR)
        self._pending_delegation("bh11111111111111", 1500)
        result = self._run(self._stop_payload())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        os.chmod(self.log_path, stat.S_IRUSR | stat.S_IWUSR)
        self.assertEqual(_read_rows(self.log_path), [])

    def test_no_stray_writes_on_the_stop_path(self):
        self._pending_delegation("bi11111111111111", 1500)
        self._run(self._stop_payload())
        stray = []
        for root, _dirs, files in os.walk(self.cwd):
            stray.extend(os.path.join(root, f) for f in files)
        self.assertEqual(stray, [])

    # -- P5: `/clear` re-homes a delegation away from its sidecar ----------

    def test_rehomed_delegation_still_records_a_row(self):
        """Measured on a live delegation: `/clear` mid-flight re-homes the
        agent's transcript under a NEW session id while the sidecar stays in
        the OLD session's `subagents/`. Resolving the sidecar only in the
        payload's own directory drops the row — for exactly the
        longest-running agent of a wave, the one worth measuring."""
        agent_id = "e1111111111111111"
        started_at = self._pending_delegation(agent_id, 1200)
        session_b, transcript_b, subagents_b = self._sibling_session()
        # The resumed half: transcript only, and NO sidecar (verified by ls on
        # the real pair of directories).
        _write_jsonl(os.path.join(subagents_b, "agent-{0}.jsonl".format(agent_id)), [
            {"type": "user", "timestamp": _ago(60), "message": {"role": "user"}},
            _assistant(SUBAGENT_MODEL, 5, 10, 20),
        ])
        self.assertFalse(os.path.exists(
            os.path.join(subagents_b, "agent-{0}.meta.json".format(agent_id))))

        self._run(self._payload(
            agent_id, transcript_path=transcript_b, session_id=session_b))

        rows = self._delegation_rows()
        self.assertEqual([r["agent_id"] for r in rows], [agent_id], rows)
        self.assertEqual(rows[0]["agent_type"], "atelier:builder")
        self.assertEqual(rows[0]["session_id"], session_b)
        # started_at is the TRUE beginning, off the sidecar's own half: session
        # B's head is only the resumed tail and would undercount the duration
        # by everything before the clear.
        self.assertEqual(rows[0]["started_at"], started_at)
        self.assertGreaterEqual(rows[0]["duration_ms"], 1200 * 1000)
        # ...while the usage tail comes from the LIVE half, which is the newer
        # of the two transcripts (5 + 10 + 20).
        self.assertEqual(rows[0]["ctx_tokens"], 35)
        self.assertEqual(self._stall_rows(), [], _read_rows(self.log_path))

    def test_a_sidecar_only_in_a_sibling_session_is_never_reported_pending(self):
        """The asymmetry, pinned so nobody "fixes" it into a storm. Widening
        the STARTED universe across sibling session dirs would name every
        delegation the project has ever run — their stop rows aged out of the
        256 KB ledger tail long ago — at every single Stop."""
        _session_b, _transcript_b, subagents_b = self._sibling_session()
        stale = "e4444444444444444"
        self._put_sidecar(subagents_b, stale)
        _write_jsonl(os.path.join(subagents_b, "agent-{0}.jsonl".format(stale)), [
            {"type": "user", "timestamp": _ago(99999), "message": {"role": "user"}},
        ])
        # One genuinely pending delegation in the CURRENT session's dir, so the
        # scan does produce a row and the assertion is about its contents.
        self._pending_delegation("e5555555555555555", 1500)

        self._run(self._stop_payload())

        named = [e["agent_id"] for r in self._stall_rows() for e in r["pending"]]
        self.assertEqual(named, ["e5555555555555555"])

    def test_rehomed_stop_row_suppresses_the_orphaned_sidecars_stall(self):
        """The other half of the same defect: the sidecar left behind in
        session A never receives a stop, so any later event resolving to A's
        directory reports it pending forever. The stop row landed under B."""
        agent_id = "e7777777777777777"
        self._pending_delegation(agent_id, 1500)
        session_b, transcript_b, subagents_b = self._sibling_session()
        _write_jsonl(os.path.join(subagents_b, "agent-{0}.jsonl".format(agent_id)), [
            {"type": "user", "timestamp": _ago(60), "message": {"role": "user"}},
        ])
        # The delegation stops, and is recorded under the NEW session id.
        self._run(self._payload(
            agent_id, transcript_path=transcript_b, session_id=session_b))
        self.assertEqual([r["session_id"] for r in self._delegation_rows()],
                         [session_b])

        # ...now a scan that still resolves to session A's directory.
        self._run(self._stop_payload())
        self.assertEqual(self._stall_rows(), [], _read_rows(self.log_path))

    def test_sibling_sidecar_probe_is_capped(self):
        """The bound. A slug can hold hundreds of session dirs; the probe only
        runs on a miss, only looks for the ONE exact filename, and stops after
        SIBLING_PROBE_LIMIT of the most recently modified siblings. Past that
        the row is dropped as before — silently, exit 0, no hang."""
        limit = HOOK_MODULE.SIBLING_PROBE_LIMIT
        self.assertGreater(limit, 0)
        agent_id = "e8888888888888888"
        session_b, transcript_b, subagents_b = self._sibling_session()
        _write_jsonl(os.path.join(subagents_b, "agent-{0}.jsonl".format(agent_id)), [
            {"type": "user", "timestamp": _ago(60), "message": {"role": "user"}},
        ])
        # The sidecar's session dir is aged furthest into the past, and more
        # than `limit` newer sibling dirs sit in front of it.
        self._put_sidecar(self.subagents_dir, agent_id)
        for i in range(limit + 3):
            filler = os.path.join(self.projects, "filler-{0:03d}".format(i), "subagents")
            os.makedirs(filler, exist_ok=True)
            self._age(os.path.dirname(filler), 10 * (i + 1))
        self._age(os.path.join(self.projects, self.session_id), 10 * (limit + 100))

        result = self._run(self._payload(
            agent_id, transcript_path=transcript_b, session_id=session_b))

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(_read_rows(self.log_path), [])

    def test_sibling_probe_finds_the_most_recent_sidecar_dir(self):
        """The ordering the cap rides on: the re-homed pair are adjacent in
        time, so the sidecar's dir is among the newest siblings. Filler dirs
        aged further back must not displace it."""
        agent_id = "e9999999999999999"
        started_at = self._pending_delegation(agent_id, 1400)
        session_b, transcript_b, subagents_b = self._sibling_session()
        _write_jsonl(os.path.join(subagents_b, "agent-{0}.jsonl".format(agent_id)), [
            {"type": "user", "timestamp": _ago(60), "message": {"role": "user"}},
        ])
        for i in range(HOOK_MODULE.SIBLING_PROBE_LIMIT + 3):
            filler = os.path.join(self.projects, "old-{0:03d}".format(i), "subagents")
            os.makedirs(filler, exist_ok=True)
            self._age(os.path.dirname(filler), 86400 * (i + 1))

        self._run(self._payload(
            agent_id, transcript_path=transcript_b, session_id=session_b))

        rows = self._delegation_rows()
        self.assertEqual([r["agent_id"] for r in rows], [agent_id], rows)
        self.assertEqual(rows[0]["started_at"], started_at)

    # -- silence and containment -------------------------------------------

    def test_hook_is_silent_on_success(self):
        self._delegation("a1414141414141414")
        result = self._run(self._payload("a1414141414141414"))
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_no_stray_writes_outside_configured_paths(self):
        self._delegation("a1515151515151515")
        self._run(self._payload("a1515151515151515"))
        stray = []
        for root, _dirs, files in os.walk(self.cwd):
            stray.extend(os.path.join(root, f) for f in files)
        self.assertEqual(stray, [])

    def test_row_shape_is_stable(self):
        """Envelope keys come from agentlog, never a hand-copied list here — a
        literal would drift silently the first time the envelope changes."""
        self._delegation("a1616161616161616")
        self._run(self._payload("a1616161616161616"))
        row = _read_rows(self.log_path)[0]
        envelope = set(agentlog.ENVELOPE_KEYS)
        self.assertEqual(
            sorted(set(row) - envelope),
            ["agent_id", "agent_type", "ctx_tokens", "duration_ms", "model",
             "session_id", "started_at"],
        )
        self.assertEqual(sorted(set(row) & envelope), sorted(envelope))
        # Envelope keys lead the row: a reader that truncates a long line
        # still sees what produced it.
        self.assertEqual(list(row)[: len(envelope)], list(agentlog.ENVELOPE_KEYS))
        self.assertEqual(row["stream"], "delegation")


if __name__ == "__main__":
    unittest.main()
