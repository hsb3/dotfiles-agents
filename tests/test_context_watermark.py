"""Tests for primitives-core/hooks/context-watermark/hook.py.

Two lanes. The threshold arithmetic and the override precedence are called
in-process (they read the environment and the activation file per call, so a
tempdir plus a scrubbed env is a complete fixture). The event branches are run
as the hook really runs — JSON on stdin, JSON on stdout, env-configured state
and ledger paths — against generated JSONL transcripts.

Stdlib-only; every fixture lives in a tempdir owned by the test.
"""

import importlib.util
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_PATH = os.path.join(
    REPO_ROOT, "primitives-core", "hooks", "context-watermark", "hook.py")

SCRUBBED_ENV = (
    "CLAUDE_PROJECT_DIR",
    "ATELIER_ACTIVATION_FILE",
    "CONTEXT_WATERMARK_SOFT",
    "CONTEXT_WATERMARK_HARD",
    "CONTEXT_WATERMARK_NOTICE",
)

_SEQ = itertools.count()


def _load_hook():
    """Import the hook by path, the way the other hook tests do."""
    spec = importlib.util.spec_from_file_location("context_watermark_hook", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


hook = _load_hook()


class _ScrubbedEnv(unittest.TestCase):
    """Every test starts from an environment that cannot leak a threshold in."""

    def setUp(self):
        self._saved = {k: os.environ.pop(k, None) for k in SCRUBBED_ENV}
        self.addCleanup(self._restore)
        self.tmp = tempfile.mkdtemp(prefix="ctxwm-")

    def _restore(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def write_activation(self, body, project_dir=None):
        project_dir = project_dir or self.tmp
        path = os.path.join(project_dir, ".claude", "atelier.local.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return path


# ---------------------------------------------------------------------------
# The formula: tier defaults and the window cap
# ---------------------------------------------------------------------------

class ThresholdFormulaTests(_ScrubbedEnv):

    def test_frontier_defaults_include_the_earlier_notice(self):
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0, "frontier"),
                         (60_000, 120_000, 160_000))

    def test_heavy_mid_and_light_get_later_defaults(self):
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0, "heavy"),
                         (96_000, 192_000, 256_000))
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0, "mid"),
                         (120_000, 240_000, 320_000))
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0, "light"),
                         (160_000, 320_000, 480_000))

    def test_small_window_caps_all_three_stages(self):
        self.assertEqual(hook.compute_thresholds(64_000, 1.0, "light"),
                         (19_200, 38_400, 51_200))

    def test_complexity_scales_all_stages_down(self):
        self.assertEqual(hook.compute_thresholds(1_000_000, 0.85, "frontier"),
                         (51_000, 102_000, 136_000))

    def test_actual_window_caps_apply_after_complexity(self):
        self.assertEqual(hook.compute_thresholds(64_000, 2.0, "light"),
                         (19_200, 38_400, 51_200))

    def test_unknown_model_is_conservatively_frontier(self):
        self.assertEqual(hook.compute_thresholds(None, 1.0, "unknown"),
                         (60_000, 120_000, 160_000))

    def test_a_non_positive_window_is_unknown_not_a_tiny_one(self):
        """Unreachable through the catalog, but this hook never trusts input:
        a window of 1 would otherwise make both tiers 0 and fire forever."""
        self.assertEqual(hook.compute_thresholds(-200_000, 1.0, "frontier"),
                         (60_000, 120_000, 160_000))
        self.assertEqual(hook.compute_thresholds(0, 1.0, "frontier"),
                         (60_000, 120_000, 160_000))

    def test_unknown_tier_uses_frontier_defaults(self):
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0, "unknown"),
                         (60_000, 120_000, 160_000))

    def test_catalog_models_use_their_production_tiers_and_windows(self):
        cases = (
            ("gpt-6-astra", "frontier", (60_000, 120_000, 160_000)),
            ("claude-fable-5", "frontier", (60_000, 120_000, 160_000)),
            ("gpt-5.6-sol", "heavy", (96_000, 192_000, 256_000)),
            ("claude-opus-5", "heavy", (96_000, 192_000, 256_000)),
            ("gpt-5.6-terra", "mid", (120_000, 240_000, 320_000)),
            ("claude-sonnet-5", "mid", (120_000, 240_000, 320_000)),
            ("gpt-5.6-luna", "light", (160_000, 320_000, 480_000)),
            ("claude-haiku-4-5", "light", (160_000, 320_000, 480_000)),
        )
        for model, tier, stages in cases:
            with self.subTest(model=model):
                self.assertEqual(hook._model_tier(model), tier)
                self.assertEqual(hook.resolve_stages(
                    self.tmp, 1_000_000, 1.0, model)[:3], stages)
        self.assertEqual(hook._model_tier("unmapped-model"), "frontier")
        self.assertEqual(hook.compute_thresholds(200_000, 1.0, "heavy"),
                         (60_000, 120_000, 160_000))


# ---------------------------------------------------------------------------
# The complexity proxy: tracked-file count
# ---------------------------------------------------------------------------

class ComplexityTests(_ScrubbedEnv):

    def test_buckets(self):
        self.assertEqual(hook.complexity_for_count(0), 1.00)
        self.assertEqual(hook.complexity_for_count(4_999), 1.00)
        self.assertEqual(hook.complexity_for_count(5_000), 0.85)
        self.assertEqual(hook.complexity_for_count(20_000), 0.85)
        self.assertEqual(hook.complexity_for_count(20_001), 0.75)

    def test_unknown_count_is_the_neutral_factor(self):
        self.assertEqual(hook.complexity_for_count(None), 1.00)

    def test_non_git_tree_counts_nothing(self):
        self.assertIsNone(hook.tracked_file_count(self.tmp))

    def test_a_git_tree_counts_its_tracked_files(self):
        subprocess.run(["git", "init", "-q", self.tmp], check=True)
        with open(os.path.join(self.tmp, "a.txt"), "w") as fh:
            fh.write("a\n")
        subprocess.run(["git", "-C", self.tmp, "add", "a.txt"], check=True)
        self.assertEqual(hook.tracked_file_count(self.tmp), 1)


# ---------------------------------------------------------------------------
# Precedence: env > activation file > computed
# ---------------------------------------------------------------------------

ACTIVATION = """---
watermark:
  soft: 90000
  hard: 130000
  complexity: 0.9
---
"""


class PrecedenceTests(_ScrubbedEnv):

    def resolve(self, window=200_000, complexity=1.0):
        return hook.resolve_stages(self.tmp, window, complexity)[1:]

    def test_computed_default_when_nothing_overrides(self):
        soft, hard, info = self.resolve()
        self.assertEqual((soft, hard), (120_000, 160_000))
        self.assertEqual(info["soft_source"], "computed")
        self.assertEqual(info["hard_source"], "computed")

    def test_activation_file_beats_the_computed_default(self):
        self.write_activation(ACTIVATION)
        soft, hard, info = self.resolve()
        self.assertEqual((soft, hard), (90_000, 130_000))
        self.assertEqual(info["soft_source"], "activation")
        self.assertEqual(info["complexity"], 0.9)
        self.assertEqual(info["complexity_source"], "activation")

    def test_env_beats_the_activation_file(self):
        self.write_activation(ACTIVATION)
        os.environ["CONTEXT_WATERMARK_SOFT"] = "70000"
        soft, hard, info = self.resolve()
        self.assertEqual((soft, hard), (70_000, 130_000))
        self.assertEqual(info["soft_source"], "env")
        self.assertEqual(info["hard_source"], "activation")

    def test_garbage_env_falls_through_to_the_activation_file(self):
        self.write_activation(ACTIVATION)
        os.environ["CONTEXT_WATERMARK_SOFT"] = "not-a-number"
        os.environ["CONTEXT_WATERMARK_HARD"] = ""
        soft, hard, _ = self.resolve()
        self.assertEqual((soft, hard), (90_000, 130_000))

    def test_garbage_activation_values_fall_through_to_computed(self):
        self.write_activation(
            "---\nwatermark:\n  soft: soon\n  hard:\n  complexity: lots\n---\n")
        soft, hard, info = self.resolve()
        self.assertEqual((soft, hard), (120_000, 160_000))
        self.assertEqual(info["complexity"], 1.0)

    def test_a_watermark_key_with_no_children_is_inert(self):
        self.write_activation("---\nwatermark:\nenforce: strict\n---\n")
        self.assertEqual(self.resolve()[:2], (120_000, 160_000))

    def test_an_activation_file_without_frontmatter_never_raises(self):
        self.write_activation("watermark:\n  soft: 90000\n")
        self.assertEqual(self.resolve()[:2], (120_000, 160_000))

    def test_a_partial_override_leaves_the_other_tier_computed(self):
        self.write_activation("---\nwatermark:\n  hard: 111000\n---\n")
        soft, hard, info = self.resolve(window=64_000)
        self.assertEqual((soft, hard), (38_400, 111_000))
        self.assertEqual(info["soft_source"], "computed")

    def test_activation_complexity_replaces_the_computed_factor(self):
        self.write_activation("---\nwatermark:\n  complexity: 0.5\n---\n")
        soft, hard, info = self.resolve(complexity=0.85)
        self.assertEqual((soft, hard), (60_000, 80_000))
        self.assertEqual(info["complexity_source"], "activation")

    def test_activation_file_env_override_is_honoured(self):
        other = os.path.join(self.tmp, "elsewhere.md")
        with open(other, "w", encoding="utf-8") as fh:
            fh.write("---\nwatermark:\n  soft: 42000\n---\n")
        os.environ["ATELIER_ACTIVATION_FILE"] = other
        self.addCleanup(os.environ.pop, "ATELIER_ACTIVATION_FILE", None)
        self.assertEqual(self.resolve()[0], 42_000)

    def test_notice_can_be_overridden_but_never_exceeds_soft(self):
        self.write_activation("---\nwatermark:\n  notice: 150000\n  soft: 90000\n---\n")
        notice, soft, hard, info = hook.resolve_stages(
            self.tmp, 1_000_000, 1.0, "claude-opus-5")
        self.assertEqual((notice, soft, hard), (90_000, 90_000, 256_000))
        self.assertEqual((info["notice_source"], info["soft_source"]),
                         ("activation", "activation"))


# ---------------------------------------------------------------------------
# Running the hook the way the harness runs it
# ---------------------------------------------------------------------------

def _assistant(ctx_tokens, model="claude-opus-5"):
    return {
        "type": "assistant",
        "message": {
            "model": model,
            "usage": {
                "input_tokens": ctx_tokens,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            },
        },
    }


def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


class HookRunTests(_ScrubbedEnv):
    """Subprocess runs: stdin JSON in, stdout JSON out, ledger on disk."""

    def setUp(self):
        super().setUp()
        self.state_dir = os.path.join(self.tmp, "state")
        self.log_path = os.path.join(self.tmp, "logs", "context-watermark.jsonl")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.project, exist_ok=True)

    def run_hook(self, payload, env=None):
        sandbox = os.path.join(self.tmp, "sandbox")
        environ = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.path.join(sandbox, "home"),
            "XDG_DATA_HOME": os.path.join(sandbox, "xdg"),
            "CONTEXT_WATERMARK_STATE_DIR": self.state_dir,
            "CONTEXT_WATERMARK_LOG_PATH": self.log_path,
        }
        environ.update(env or {})
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input=json.dumps(payload),
            capture_output=True, text=True, env=environ, timeout=30)
        return proc

    def rows(self):
        if not os.path.isfile(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def session_payload(self, ctx_tokens, model="claude-opus-5", session=None):
        session = session or "session-{0}".format(next(_SEQ))
        transcript = os.path.join(self.tmp, "transcripts", session + ".jsonl")
        _write_jsonl(transcript, [_assistant(ctx_tokens, model)])
        return {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session,
            "transcript_path": transcript,
            "cwd": self.project,
            "prompt": "go",
        }

    # -- session branch ---------------------------------------------------

    def test_a_known_heavy_model_uses_its_soft_line(self):
        proc = self.run_hook(self.session_payload(200_000))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("additionalContext", out)
        row = self.rows()[-1]
        self.assertEqual(row["tier"], "soft")
        self.assertEqual(row["soft"], 192_000)
        self.assertEqual(row["window"], 1_000_000)

    def test_notice_soft_and_hard_transition_without_repeating(self):
        session = "session-{0}".format(next(_SEQ))
        for tokens, expected in ((100_000, "notice"), (200_000, "soft"),
                                 (260_000, "hard")):
            proc = self.run_hook(self.session_payload(tokens, session=session))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(self.rows()[-1]["tier"], expected)
            self.assertIn(expected + " watermark", proc.stdout.lower())

    def test_notice_does_not_nag_until_its_refire_interval(self):
        session = "session-{0}".format(next(_SEQ))
        first = self.run_hook(self.session_payload(100_000, session=session))
        second = self.run_hook(self.session_payload(100_000, session=session))
        self.assertIn("additionalContext", first.stdout)
        self.assertEqual(second.stdout.strip(), "")

    def test_warning_does_not_write_into_the_project_tree(self):
        proc = self.run_hook(self.session_payload(100_000))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(os.listdir(self.project), [])

    def _dirty_project_snapshot(self):
        tracked = os.path.join(self.project, "tracked.txt")
        untracked = os.path.join(self.project, "untracked.txt")
        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("committed\n")
        subprocess.run(["git", "init", "-q", self.project], check=True)
        subprocess.run(["git", "-C", self.project, "add", "tracked.txt"], check=True)
        subprocess.run([
            "git", "-C", self.project, "-c", "user.name=test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
        with open(tracked, "w", encoding="utf-8") as fh:
            fh.write("dirty tracked\n")
        with open(untracked, "w", encoding="utf-8") as fh:
            fh.write("dirty untracked\n")
        index = subprocess.run(
            ["git", "-C", self.project, "rev-parse", "--git-path", "index"],
            capture_output=True, text=True, check=True).stdout.strip()
        if not os.path.isabs(index):
            index = os.path.join(self.project, index)

        def read_bytes(path):
            with open(path, "rb") as fh:
                return fh.read()

        def snapshot():
            return {
                "branch": subprocess.run(
                    ["git", "-C", self.project, "branch", "--show-current"],
                    capture_output=True, text=True, check=True).stdout,
                "index": read_bytes(index),
                "diff": subprocess.run(
                    ["git", "-C", self.project, "diff", "--binary"],
                    capture_output=True, check=True).stdout,
                "tracked": read_bytes(tracked),
                "untracked": read_bytes(untracked),
            }
        return snapshot

    def test_all_stages_preserve_a_dirty_project_in_claude_and_codex(self):
        snapshot = self._dirty_project_snapshot()
        before = snapshot()
        for tokens in (100_000, 200_000, 260_000):
            self.run_hook(self.session_payload(tokens))
            self.assertEqual(snapshot(), before)

        rollout = os.path.join(self.tmp, "codex.jsonl")
        rows = []
        for tokens in (20_000, 40_000, 52_000):
            _write_jsonl(rollout, [
                {"type": "turn_context", "payload": {"model": "gpt-5.6-terra"}},
                {"type": "event_msg", "payload": {"type": "token_count", "info": {
                    "last_token_usage": {"total_tokens": tokens}, "model_context_window": 64_000}}},
            ])
            with mock.patch.dict(os.environ, {"ATELIER_HARNESS": "codex"}), \
                    mock.patch.object(hook, "STATE_DIR", self.state_dir), \
                    mock.patch("sys.stdout", io.StringIO()):
                hook.handle_session({
                    "session_id": "codex-{0}".format(tokens), "transcript_path": rollout,
                    "cwd": self.project}, rows.append)
            self.assertEqual(snapshot(), before)
        self.assertEqual([row["tier"] for row in rows], ["notice", "soft", "hard"])

    def test_unknown_model_falls_back_to_the_absolute_pair_and_says_so(self):
        proc = self.run_hook(self.session_payload(130_000, model="gpt-9-turbo"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self.rows()[-1]
        self.assertIsNone(row["window"])
        self.assertTrue(row["window_fallback"])
        self.assertEqual((row["soft"], row["hard"]), (120_000, 160_000))
        self.assertEqual(row["tier"], "soft")

    def test_a_transcript_with_no_model_at_all_is_still_a_fallback(self):
        """`window_fallback` answers "did this check measure a window?", so a
        usage block with no model beside it is the same answer as an unmapped
        model id — not a quieter one."""
        session = "session-{0}".format(next(_SEQ))
        transcript = os.path.join(self.tmp, "transcripts", session + ".jsonl")
        record = _assistant(130_000)
        record["message"].pop("model")
        _write_jsonl(transcript, [record])
        self.run_hook({
            "hook_event_name": "UserPromptSubmit", "session_id": session,
            "transcript_path": transcript, "cwd": self.project, "prompt": "go"})
        row = self.rows()[-1]
        self.assertIsNone(row["model"])
        self.assertTrue(row["window_fallback"])
        self.assertEqual((row["soft"], row["hard"]), (120_000, 160_000))

    def test_a_known_window_row_is_not_marked_as_a_fallback(self):
        self.run_hook(self.session_payload(10_000))
        self.assertFalse(self.rows()[-1]["window_fallback"])

    def test_env_override_still_wins_end_to_end(self):
        proc = self.run_hook(self.session_payload(30_000),
                             env={"CONTEXT_WATERMARK_SOFT": "25000"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("additionalContext", json.loads(proc.stdout))
        self.assertEqual(self.rows()[-1]["soft"], 25_000)

    def test_a_state_file_holding_a_json_non_object_repairs_itself(self):
        """A valid-JSON list where the state dict belongs used to kill this
        (session, agent) pair forever: every later call raised on `.get` and
        nothing ever rewrote the file."""
        payload = self.session_payload(125_000)
        os.makedirs(self.state_dir, exist_ok=True)
        state = os.path.join(
            self.state_dir, "".join(
                c for c in payload["session_id"] if c.isalnum() or c in "-_") + ".json")
        with open(state, "w") as fh:
            fh.write("[1, 2, 3]")
        proc = self.run_hook(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("additionalContext", json.loads(proc.stdout))
        self.assertNotIn("error", self.rows()[-1])

    def test_the_ledger_names_the_tier_that_supplied_each_value(self):
        proc = self.run_hook(self.session_payload(125_000),
                             env={"CONTEXT_WATERMARK_SOFT": "100000"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self.rows()[-1]
        self.assertEqual(row["sources"], {
            "notice": "computed", "soft": "env", "hard": "computed",
            "complexity": "computed"})

    def test_the_activation_file_beats_the_computed_default_end_to_end(self):
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
        with open(os.path.join(self.project, ".claude", "atelier.local.md"), "w") as fh:
            fh.write("---\nwatermark:\n  soft: 20000\n  hard: 30000\n---\n")
        proc = self.run_hook(self.session_payload(25_000))
        self.assertEqual(self.rows()[-1]["soft"], 20_000)
        self.assertIn("additionalContext", json.loads(proc.stdout))

        # ... and the environment still beats the file.
        proc = self.run_hook(self.session_payload(25_000),
                             env={"CONTEXT_WATERMARK_SOFT": "26000"})
        row = self.rows()[-1]
        self.assertEqual((row["soft"], row["tier"]), (26_000, "none"))
        self.assertEqual(row["sources"]["hard"], "activation")

    def test_malformed_payload_exits_zero_and_says_nothing(self):
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input="{not json",
            capture_output=True, text=True, timeout=30,
            env={"PATH": os.environ.get("PATH", ""),
                 "HOME": os.path.join(self.tmp, "sandbox", "home"),
                 "XDG_DATA_HOME": os.path.join(self.tmp, "sandbox", "xdg"),
                 "CONTEXT_WATERMARK_STATE_DIR": self.state_dir,
                 "CONTEXT_WATERMARK_LOG_PATH": self.log_path})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    # -- subagent branch --------------------------------------------------

    def subagent_payload(self, ctx_tokens, agent_id="a40d0f7528e04f941",
                         model="claude-haiku-4-5-20251001", write_worker=True,
                         session=None):
        """A PostToolUse payload as it arrives INSIDE a worker.

        `transcript_path` names the MAIN SESSION transcript there — measured
        2026-09-08 — so the fixture writes the parent's file at that path and
        the worker's own beside it under `subagents/`.
        """
        session = session or "session-{0}".format(next(_SEQ))
        parent = os.path.join(self.tmp, "transcripts", session + ".jsonl")
        _write_jsonl(parent, [_assistant(5_000, "claude-opus-5")])
        if write_worker:
            worker = os.path.join(
                self.tmp, "transcripts", session, "subagents",
                "agent-{0}.jsonl".format(agent_id))
            _write_jsonl(worker, [_assistant(ctx_tokens, model)])
        return {
            "hook_event_name": "PostToolUse",
            "session_id": session,
            "agent_id": agent_id,
            "transcript_path": parent,
            "cwd": self.project,
            "tool_name": "Bash",
        }

    def test_a_worker_uses_the_same_window_capped_stages(self):
        proc = self.run_hook(self.subagent_payload(70_000))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        specific = out["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PostToolUse")
        self.assertNotIn("additionalContext", out)
        row = self.rows()[-1]
        self.assertEqual(row["scope"], "subagent")
        self.assertEqual((row["notice"], row["soft"], row["hard"]),
                         (60_000, 120_000, 160_000))
        self.assertEqual(row["tier"], "notice")
        self.assertEqual(row["agent_id"], "a40d0f7528e04f941")
        self.assertEqual(row["window"], 200_000)

    def test_the_worker_notice_is_advisory_and_preserves_bounded_work(self):
        proc = self.run_hook(self.subagent_payload(70_000))
        text = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
        lower = text.lower()
        self.assertIn("atelier", lower)  # provenance: not an injected instruction
        self.assertIn("context-watermark", lower)
        self.assertIn("advisory", lower)
        self.assertIn("bounded slice", lower)
        self.assertNotIn("terminate", lower)

    def test_a_worker_below_the_line_is_left_alone(self):
        proc = self.run_hook(self.subagent_payload(20_000))
        self.assertEqual(proc.stdout.strip(), "")
        self.assertEqual(self.rows()[-1]["tier"], "none")

    def test_a_worker_keeps_each_explicit_stage_source(self):
        proc = self.run_hook(self.subagent_payload(70_000),
                             env={"CONTEXT_WATERMARK_SOFT": "120000"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self.rows()[-1]
        self.assertEqual(row["sources"]["soft"], "env")
        self.assertEqual(row["sources"]["hard"], "computed")
        self.assertEqual(row["soft"], 120_000)

    def test_a_worker_reaches_the_hard_stage_with_its_own_budget(self):
        proc = self.run_hook(self.subagent_payload(190_000))
        self.assertEqual(self.rows()[-1]["tier"], "hard")
        text = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("hard watermark", text.lower())

    def test_the_worker_transcript_is_read_not_the_parents(self):
        """The parent's own transcript sits at 5k tokens in this fixture."""
        self.run_hook(self.subagent_payload(70_000))
        self.assertEqual(self.rows()[-1]["ctx_tokens"], 70_000)

    def test_a_missing_worker_transcript_logs_and_stays_quiet(self):
        proc = self.run_hook(self.subagent_payload(70_000, write_worker=False))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")
        self.assertIn("error", self.rows()[-1])

    def test_post_tool_use_outside_a_worker_produces_nothing(self):
        payload = self.subagent_payload(70_000)
        payload.pop("agent_id")
        proc = self.run_hook(payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")
        self.assertEqual(self.rows(), [])


class WatermarkConfigLoaderTests(_ScrubbedEnv):
    """`activation.py check` reports this key through the hook's own loader."""

    def test_the_loader_is_the_one_the_checker_calls(self):
        self.write_activation(ACTIVATION)
        self.assertEqual(
            hook._load_watermark_config(self.tmp),
            {"soft": 90_000, "hard": 130_000, "complexity": 0.9})

    def test_no_file_is_an_empty_config(self):
        self.assertEqual(hook._load_watermark_config(self.tmp), {})


if __name__ == "__main__":
    unittest.main()
