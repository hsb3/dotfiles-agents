"""Behavior tests for the deployable evals PocketBase wrapper."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVE = ROOT / "evals" / "serve.sh"


class ServeWrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = Path(self.tmp.name)
        fake = tmp / "pocketbase"
        fake.write_text("#!/usr/bin/env sh\nprintf '%s\\n' \"$@\"\n", encoding="utf-8")
        fake.chmod(0o755)
        self.env = os.environ | {"PATH": f"{tmp}:{os.environ['PATH']}", "PB_DATA_DIR": str(tmp / "data")}

    def run_wrapper(self, *args, **env):
        return subprocess.run(
            [str(SERVE), *args], text=True, capture_output=True,
            env=self.env | env, check=True,
        ).stdout.splitlines()

    def test_serve_uses_bind_not_rest_endpoint_and_forwards_data_dir(self):
        args = self.run_wrapper(PB_URL="https://private.example/api", PB_BIND="127.0.0.9:8181")
        self.assertEqual(args, ["serve", "--dir", self.env["PB_DATA_DIR"], "--http", "127.0.0.9:8181"])

    def test_non_serve_preserves_args_and_data_dir(self):
        args = self.run_wrapper("superuser", "create", "new@example.test", "secret")
        self.assertEqual(args, ["superuser", "create", "new@example.test", "secret", "--dir", self.env["PB_DATA_DIR"]])
