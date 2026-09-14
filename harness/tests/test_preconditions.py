"""Environment preconditions — shape/stability, secret-safety, self-install scan.

`env_preconditions` must never leak a secret VALUE (only auth-var NAMES); its
shape must stay stable/JSON-serializable. `detect_self_installs` must be
deterministic (sorted, deduped), truncate long lines, and cap a pathological
list.
"""

import json
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.preconditions import (  # noqa: E402
    AUTH_ENV_VARS,
    detect_self_installs,
    env_preconditions,
    render_header,
    render_note,
)


class _StubAdapter:
    name = "stub"

    def cli_version(self):
        return "stub-1.2.3"


def _args(**over):
    ns = types.SimpleNamespace(
        model="claude-x",
        campaign="camp",
        grader_model="grader-y",
        timeout=600,
    )
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


class TestEnvPreconditions(unittest.TestCase):
    def test_shape_and_json_serializable(self):
        result = env_preconditions(_StubAdapter(), _args())
        expected_keys = {
            "harness", "cli_version", "model", "grader_model", "timeout",
            "campaign", "auth_env_present", "network_assumption",
        }
        self.assertEqual(set(result), expected_keys)
        # Must round-trip through json.dumps (what the ledger/log header do).
        json.dumps(result, sort_keys=True)
        self.assertEqual(result["harness"], "stub")
        self.assertEqual(result["cli_version"], "stub-1.2.3")
        self.assertEqual(result["model"], "claude-x")
        self.assertEqual(result["campaign"], "camp")
        self.assertEqual(result["grader_model"], "grader-y")
        self.assertEqual(result["timeout"], 600)
        self.assertEqual(result["network_assumption"], "assumed-available")

    def test_model_defaults_to_default_when_falsy(self):
        result = env_preconditions(_StubAdapter(), _args(model=None))
        self.assertEqual(result["model"], "default")

    def test_campaign_defaults_to_empty_string(self):
        result = env_preconditions(_StubAdapter(), _args(campaign=None))
        self.assertEqual(result["campaign"], "")

    def test_stable_across_repeated_calls(self):
        args = _args()
        first = env_preconditions(_StubAdapter(), args)
        second = env_preconditions(_StubAdapter(), args)
        self.assertEqual(first, second)

    def test_auth_env_present_is_sorted_names_only(self):
        secret = "sk-live-topsecretvalue"
        env_backup = dict(os.environ)
        try:
            for var in AUTH_ENV_VARS:
                os.environ.pop(var, None)
            os.environ["ANTHROPIC_API_KEY"] = secret
            os.environ["GEMINI_API_KEY"] = "another-secret-value"
            result = env_preconditions(_StubAdapter(), _args())
            self.assertEqual(
                result["auth_env_present"], ["ANTHROPIC_API_KEY", "GEMINI_API_KEY"]
            )
            dumped = json.dumps(result, sort_keys=True)
            self.assertNotIn(secret, dumped)
            self.assertNotIn("another-secret-value", dumped)
            self.assertIn("ANTHROPIC_API_KEY", dumped)
            self.assertIn("GEMINI_API_KEY", dumped)
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_no_auth_env_present_when_none_set(self):
        env_backup = dict(os.environ)
        try:
            for var in AUTH_ENV_VARS:
                os.environ.pop(var, None)
            result = env_preconditions(_StubAdapter(), _args())
            self.assertEqual(result["auth_env_present"], [])
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_render_note_contains_key_facts(self):
        note = render_note(env_preconditions(_StubAdapter(), _args()))
        self.assertIn("harness=stub", note)
        self.assertIn("cli=stub-1.2.3", note)
        self.assertIn("campaign=camp", note)
        self.assertIn("model=claude-x", note)

    def test_render_header_is_hash_prefixed_json_line(self):
        precond = env_preconditions(_StubAdapter(), _args())
        precond["self_installs"] = []
        header = render_header(precond)
        self.assertTrue(header.startswith("# preconditions: "))
        payload = header[len("# preconditions: "):]
        self.assertEqual(json.loads(payload), precond)


class TestDetectSelfInstalls(unittest.TestCase):
    def test_empty_or_none_log_yields_empty_list(self):
        self.assertEqual(detect_self_installs(""), [])
        self.assertEqual(detect_self_installs(None), [])

    def test_positive_matches_across_signatures(self):
        raw = "\n".join([
            "some normal output",
            "$ npm install --save-dev foo",
            "$ npx playwright install chromium",
            "$ pip install requests",
            "everything else is noise",
        ])
        found = detect_self_installs(raw)
        self.assertTrue(any("npm install" in f for f in found))
        self.assertTrue(any("playwright install" in f for f in found))
        self.assertTrue(any("pip install" in f for f in found))

    def test_negative_no_false_positive_on_unrelated_text(self):
        raw = "\n".join([
            "Installing dependencies is not something we do here.",
            "the word install alone should not trigger anything",
            "npm run build",
            "npm test",
        ])
        self.assertEqual(detect_self_installs(raw), [])

    def test_dedupe_and_sort(self):
        raw = "\n".join([
            "npm install foo",
            "npm install foo",
            "brew install bar",
        ])
        found = detect_self_installs(raw)
        self.assertEqual(found, sorted(set(found)))
        self.assertEqual(len(found), 2)

    def test_truncates_long_lines(self):
        long_line = "npm install " + ("x" * 300)
        found = detect_self_installs(long_line)
        self.assertEqual(len(found), 1)
        self.assertLessEqual(len(found[0]), 120)

    def test_caps_list_length(self):
        lines = [f"npm install pkg{i}" for i in range(50)]
        found = detect_self_installs("\n".join(lines))
        self.assertLessEqual(len(found), 20)

    def test_deterministic_across_calls(self):
        raw = "\n".join([f"pip install pkg{i}" for i in range(30)])
        first = detect_self_installs(raw)
        second = detect_self_installs(raw)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
