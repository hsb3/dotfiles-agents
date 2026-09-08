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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_PATH = os.path.join(
    REPO_ROOT, "primitives-core", "hooks", "context-watermark", "hook.py")

SCRUBBED_ENV = (
    "CLAUDE_PROJECT_DIR",
    "ATELIER_ACTIVATION_FILE",
    "CONTEXT_WATERMARK_SOFT",
    "CONTEXT_WATERMARK_HARD",
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
# The formula: the window caps, never lifts
# ---------------------------------------------------------------------------

class ThresholdFormulaTests(_ScrubbedEnv):

    def test_200k_window_reproduces_the_shipped_defaults(self):
        self.assertEqual(hook.compute_thresholds(200_000, 1.0), (120_000, 160_000))

    def test_1m_window_stays_at_the_absolute_cap(self):
        self.assertEqual(hook.compute_thresholds(1_000_000, 1.0), (120_000, 160_000))

    def test_64k_window_scales_down(self):
        self.assertEqual(hook.compute_thresholds(64_000, 1.0), (38_400, 51_200))

    def test_complexity_scales_both_tiers_down(self):
        self.assertEqual(hook.compute_thresholds(200_000, 0.85), (102_000, 136_000))

    def test_unknown_window_falls_back_to_the_absolute_pair(self):
        self.assertEqual(hook.compute_thresholds(None, 1.0), (120_000, 160_000))

    def test_the_named_constants_are_the_ruling_of_2026_09_08(self):
        self.assertEqual(
            (hook.SOFT_ABS, hook.HARD_ABS, hook.SOFT_FRAC, hook.HARD_FRAC),
            (120_000, 160_000, 0.60, 0.80))


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
        return hook.resolve_watermarks(self.tmp, window, complexity)

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


# ---------------------------------------------------------------------------
# Running the hook the way the harness runs it
# ---------------------------------------------------------------------------

def _assistant(ctx_tokens, model="claude-opus-4-8"):
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

    def session_payload(self, ctx_tokens, model="claude-opus-4-8", session=None):
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

    def test_a_known_1m_window_still_nudges_at_the_absolute_soft_line(self):
        proc = self.run_hook(self.session_payload(125_000))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertIn("additionalContext", out)
        row = self.rows()[-1]
        self.assertEqual(row["tier"], "soft")
        self.assertEqual(row["soft"], 120_000)
        self.assertEqual(row["window"], 1_000_000)

    def test_unknown_model_falls_back_to_the_absolute_pair_and_says_so(self):
        proc = self.run_hook(self.session_payload(130_000, model="gpt-9-turbo"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self.rows()[-1]
        self.assertIsNone(row["window"])
        self.assertTrue(row["window_fallback"])
        self.assertEqual((row["soft"], row["hard"]), (120_000, 160_000))
        self.assertEqual(row["tier"], "soft")

    def test_a_known_window_row_is_not_marked_as_a_fallback(self):
        self.run_hook(self.session_payload(10_000))
        self.assertFalse(self.rows()[-1]["window_fallback"])

    def test_env_override_still_wins_end_to_end(self):
        proc = self.run_hook(self.session_payload(30_000),
                             env={"CONTEXT_WATERMARK_SOFT": "25000"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("additionalContext", json.loads(proc.stdout))
        self.assertEqual(self.rows()[-1]["soft"], 25_000)

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
        _write_jsonl(parent, [_assistant(5_000, "claude-opus-4-8")])
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

    def test_a_worker_is_nudged_at_half_the_session_soft_line(self):
        proc = self.run_hook(self.subagent_payload(70_000))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        specific = out["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PostToolUse")
        self.assertNotIn("additionalContext", out)
        row = self.rows()[-1]
        self.assertEqual(row["scope"], "subagent")
        self.assertEqual(row["soft"], 60_000)
        self.assertIsNone(row["hard"])
        self.assertEqual(row["agent_id"], "a40d0f7528e04f941")
        self.assertEqual(row["window"], 200_000)

    def test_the_worker_nudge_names_the_action_to_take(self):
        proc = self.run_hook(self.subagent_payload(70_000))
        text = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("wrap up and report now", text.lower())
        self.assertNotIn("/clear", text)
        self.assertNotIn("/compact", text)

    def test_a_worker_below_the_line_is_left_alone(self):
        proc = self.run_hook(self.subagent_payload(20_000))
        self.assertEqual(proc.stdout.strip(), "")
        self.assertEqual(self.rows()[-1]["tier"], "none")

    def test_a_worker_never_gets_a_hard_tier(self):
        proc = self.run_hook(self.subagent_payload(190_000))
        self.assertEqual(self.rows()[-1]["tier"], "soft")
        text = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("hard", text.lower())

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
