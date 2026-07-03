"""Tests for scripts/smoke.py's pure functions (the tool-driving sections need the real
CLIs and run only via `make smoke`). Stdlib unittest, zero-install — safe for `make ci`.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import smoke as S  # noqa: E402


class CmaValidator(unittest.TestCase):
    GOOD = {
        "name": "board-analyst",
        "model": "claude-sonnet-4-5",
        "system": "You are…",
        "skills": [],
        "metadata": {},
    }

    def test_valid_payload_clean(self):
        self.assertEqual(S.validate_cma_agent(self.GOOD), [])

    def test_missing_required_flagged(self):
        # AC (#24): the CMA schema check flags an agent payload missing a required field.
        for key in S.CMA_REQUIRED:
            payload = {k: v for k, v in self.GOOD.items() if k != key}
            problems = S.validate_cma_agent(payload)
            self.assertTrue(
                any(key in p and "required" in p for p in problems),
                f"expected `{key}` flagged, got: {problems}",
            )

    def test_empty_required_flagged(self):
        payload = dict(self.GOOD, model="  ")
        self.assertTrue(S.validate_cma_agent(payload))

    def test_wrong_optional_type_flagged(self):
        payload = dict(self.GOOD, skills="not-a-list")
        problems = S.validate_cma_agent(payload)
        self.assertTrue(any("skills" in p for p in problems))


class ToolErrored(unittest.TestCase):
    def test_error_line_detected_through_ansi(self):
        out = "\x1b[91m\x1b[1mError: \x1b[0mConfiguration is invalid at /x\n"
        self.assertTrue(S.tool_errored(out))

    def test_error_word_inside_dump_not_flagged(self):
        # config dumps echo agent prompts; the word Error mid-line must not trip it
        out = '{\n  "prompt": "explain the Error handling convention"\n}\n'
        self.assertFalse(S.tool_errored(out))


class Present(unittest.TestCase):
    def test_exact_token_found(self):
        self.assertTrue(S.present("handoff", "listed: handoff (skill)"))

    def test_prefix_of_longer_name_not_found(self):
        # `code` must not count as present when only `code-quality-reviewer` is listed
        self.assertFalse(S.present("code", "code-quality-reviewer (subagent)"))
        self.assertFalse(S.present("board", "board-analyst (subagent)"))

    def test_found_inside_json_dump(self):
        self.assertTrue(S.present("handoff", '"name": "handoff",'))


class MergedMcp(unittest.TestCase):
    def test_merges_fragments_and_names(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("alpha", "beta"):
                with open(os.path.join(d, f"{name}.json"), "w") as fh:
                    json.dump({"mcp": {name: {"type": "local"}}}, fh)
            config, names = S.merged_mcp(d, "mcp")
            self.assertEqual(sorted(config["mcp"]), ["alpha", "beta"])
            self.assertEqual(sorted(names), ["alpha", "beta"])

    def test_duplicate_server_name_raises(self):
        # A duplicate would be silently clobbered — a build regression, not a merge.
        with tempfile.TemporaryDirectory() as d:
            for fname in ("a.json", "b.json"):
                with open(os.path.join(d, fname), "w") as fh:
                    json.dump({"mcp": {"dup": {"type": "local"}}}, fh)
            with self.assertRaises(ValueError) as ctx:
                S.merged_mcp(d, "mcp")
            self.assertIn("dup", str(ctx.exception))

    def test_invalid_fragment_raises_with_filename(self):
        # AC (#24): a deliberately corrupted mcp fragment must fail the smoke — the
        # helper raises a ValueError naming the fragment; callers turn it into a ✗.
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bad.json"), "w") as fh:
                fh.write('{"mcp": {broken')
            with self.assertRaises(ValueError) as ctx:
                S.merged_mcp(d, "mcp")
            self.assertIn("bad.json", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
