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

    def _payload(self, agent_id, agent_type="", transcript_path=None):
        # agent_type is "" by default: that is what real SubagentStop payloads
        # carry in the large majority of cases (defect D1).
        return {
            "session_id": self.session_id,
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
            ["agent_id", "agent_type", "ctx_tokens", "model", "session_id"],
        )
        self.assertEqual(sorted(set(row) & envelope), sorted(envelope))
        # Envelope keys lead the row: a reader that truncates a long line
        # still sees what produced it.
        self.assertEqual(list(row)[: len(envelope)], list(agentlog.ENVELOPE_KEYS))
        self.assertEqual(row["stream"], "delegation")


if __name__ == "__main__":
    unittest.main()
