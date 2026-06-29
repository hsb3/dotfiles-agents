"""Tests over the GENERATED targets/ -- correctness the byte-diff drift guard cannot give.

The drift guard proves committed == rebuild; it never checks the committed bytes are SHAPED right,
that the build is deterministic run-to-run, or that no literal secret leaked in. This does.

Reads the committed targets/ and also drives translate.build() into temp dirs for the determinism
check. Stdlib-only.
"""

import glob
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import translate as T  # noqa: E402
import validate_primitives as V  # noqa: E402

TARGETS = os.path.join(T.REPO, "targets")


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class McpFragmentShape(unittest.TestCase):
    def test_claude_code_fragments(self):
        files = glob.glob(os.path.join(TARGETS, "claude-code", "mcp", "*.json"))
        self.assertTrue(files, "expected CC mcp fragments")
        for f in files:
            d = _load(f)
            self.assertIn("mcpServers", d)
            (entry,) = d["mcpServers"].values()
            self.assertIn(entry["type"], {"stdio", "http"})
            if entry["type"] == "stdio":
                self.assertIn("command", entry)
            else:
                self.assertIn("url", entry)

    def test_opencode_fragments(self):
        for f in glob.glob(os.path.join(TARGETS, "opencode", "mcp", "*.json")):
            d = _load(f)
            self.assertIn("mcp", d)
            (entry,) = d["mcp"].values()
            self.assertIn(entry["type"], {"local", "remote"})
            if entry["type"] == "local":
                self.assertIsInstance(entry["command"], list)
            else:
                self.assertIn("url", entry)

    def test_cma_mcp_fragments_are_remote_only(self):
        for f in glob.glob(os.path.join(TARGETS, "claude-agents", "mcp", "*.json")):
            d = _load(f)
            self.assertIn("mcp_servers", d)
            for s in d["mcp_servers"]:
                self.assertEqual(s["type"], "url")  # CMA is remote-only
                self.assertIn("url", s)
                self.assertIn("name", s)


class CmaPayloadShape(unittest.TestCase):
    def test_every_agent_payload_has_name_and_model(self):
        files = glob.glob(os.path.join(TARGETS, "claude-agents", "agents", "*.json"))
        self.assertTrue(files, "expected CMA agent payloads")
        for f in files:
            d = _load(f)
            self.assertTrue(d.get("name"), f"{f} missing name")
            self.assertTrue(d.get("model"), f"{f} missing model")
            self.assertIn("system", d)

    def test_skill_upload_sheets(self):
        for f in glob.glob(
            os.path.join(TARGETS, "claude-agents", "skills", "*.upload.json")
        ):
            d = _load(f)
            self.assertEqual(d.get("endpoint"), "POST /v1/skills")
            self.assertTrue(d.get("display_title"))
            self.assertIsInstance(d.get("files"), list)


class MarketplaceShape(unittest.TestCase):
    def test_marketplace_and_plugin_manifests(self):
        market = _load(
            os.path.join(TARGETS, "claude-code", ".claude-plugin", "marketplace.json")
        )
        for key in ("name", "owner", "plugins"):
            self.assertIn(key, market)
        for pj in glob.glob(
            os.path.join(
                TARGETS, "claude-code", "plugins", "*", ".claude-plugin", "plugin.json"
            )
        ):
            d = _load(pj)
            self.assertIn("name", d)
            self.assertIn("version", d)


class Determinism(unittest.TestCase):
    def test_build_twice_is_byte_identical(self):
        inputs = T.load_inputs()
        d1, d2 = tempfile.mkdtemp(), tempfile.mkdtemp()
        T.build(d1, *inputs)
        T.build(d2, *inputs)
        for t in T.TARGETS:
            self.assertEqual(
                T.diff_trees(os.path.join(d1, t), os.path.join(d2, t)),
                [],
                f"{t} differs between two builds",
            )


class SecretHygiene(unittest.TestCase):
    def _secret_problems(self, root):
        problems = []
        for f in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
            d = _load(f)
            for mapping in self._find_secret_maps(d):
                V.check_secret_values(mapping, os.path.relpath(f, T.REPO), problems)
        return problems

    def _find_secret_maps(self, obj):
        """Yield every env/environment/headers dict nested anywhere in a parsed JSON doc."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("env", "environment", "headers") and isinstance(v, dict):
                    yield v
                yield from self._find_secret_maps(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from self._find_secret_maps(v)

    def test_no_literal_secrets_in_targets(self):
        self.assertEqual(self._secret_problems(TARGETS), [])

    def test_scanner_would_catch_a_literal(self):
        # guard against a vacuous pass: a planted literal token MUST be caught
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "leak.json"), "w") as fh:
            json.dump(
                {"mcpServers": {"x": {"env": {"API_TOKEN": "ghp_literalLeak123"}}}}, fh
            )
        self.assertTrue(self._secret_problems(d))


if __name__ == "__main__":
    unittest.main()
