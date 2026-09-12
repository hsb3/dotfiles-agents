"""Behavior tests for the deployable evals PocketBase wrapper."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVE = ROOT / "evals" / "serve.sh"
START = ROOT / "evals" / "deploy" / "start.sh"


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


class DeployStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = Path(self.tmp.name)
        self.log = tmp / "pocketbase.log"
        self.fake = tmp / "pocketbase"
        self.fake.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" >> \"$FAKE_LOG\"\n"
            "if [ \"$1\" = superuser ]; then\n"
            "  case \"${FAKE_CREATE:-valid}\" in\n"
            "    valid) echo 'Successfully created new superuser \"probe@example.test\"!'; exit 0 ;;\n"
            "    duplicate) echo '2026/09/12 06:14:56 failed to create new superuser account: email: Value must be unique.' >&2; exit 1 ;;\n"
            "    invalid) echo 'password rejected' >&2; exit 1 ;;\n"
            "  esac\n"
            "fi\n",
            encoding="utf-8",
        )
        self.fake.chmod(0o755)

    def run_start(self, **env):
        base = {key: value for key, value in os.environ.items()
                if key not in {"PB_SUPERUSER_EMAIL", "PB_SUPERUSER_PASSWORD"}}
        base |= {"POCKETBASE_BIN": str(self.fake), "FAKE_LOG": str(self.log)}
        return subprocess.run(["/bin/sh", str(START)], text=True, capture_output=True, env=base | env)

    def test_bootstrap_credentials_are_required(self):
        for env, missing in (({}, "PB_SUPERUSER_EMAIL"),
                             ({"PB_SUPERUSER_EMAIL": "admin@example.test"}, "PB_SUPERUSER_PASSWORD")):
            with self.subTest(env=env):
                proc = self.run_start(**env)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(missing, proc.stderr)

    def test_valid_creation_and_existing_account_both_serve(self):
        for result in ("valid", "duplicate"):
            with self.subTest(result=result):
                proc = self.run_start(
                    FAKE_CREATE=result, PB_SUPERUSER_EMAIL="admin@example.test",
                    PB_SUPERUSER_PASSWORD="LongEnoughSecret123",
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.log.read_text(encoding="utf-8").splitlines(), [
            "superuser", "create", "admin@example.test", "LongEnoughSecret123", "--dir", "/pb/pb_data",
            "serve", "--http=0.0.0.0:8090", "--dir", "/pb/pb_data", "--origins=https://invalid.local",
            "superuser", "create", "admin@example.test", "LongEnoughSecret123", "--dir", "/pb/pb_data",
            "serve", "--http=0.0.0.0:8090", "--dir", "/pb/pb_data", "--origins=https://invalid.local",
        ])

    def test_invalid_creation_prevents_server_start(self):
        proc = self.run_start(
            FAKE_CREATE="invalid", PB_SUPERUSER_EMAIL="admin@example.test",
            PB_SUPERUSER_PASSWORD="LongEnoughSecret123",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("password rejected", proc.stderr)
        self.assertEqual(self.log.read_text(encoding="utf-8").splitlines(), [
            "superuser", "create", "admin@example.test", "LongEnoughSecret123", "--dir", "/pb/pb_data",
        ])
