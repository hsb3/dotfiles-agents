#!/usr/bin/env python3
"""Run a disposable packaged PocketBase toolbox fixture on loopback until Ctrl-C."""

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from package_toolbox import build_package
from schema import collection_specs


BUSINESS_COLLECTIONS = (
    "runs", "artifacts",
)
SCHEMA_ORDER = (
    "frameworks", "sources", "extenders", "framework_elements", "files", "distributions",
    "frontmatter_dimensions", "eval_runs", "eval_responses", "assessments", "job_coverage",
    "relationships", "coverage_gaps", "runs", "artifacts", "run_events", "tool_calls",
)


def _json_request(url, method="GET", body=None, token=None):
    request = urllib.request.Request(url, method=method)
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", token)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"{}")


def _multipart_request(url, body, filename, content, token):
    boundary = "fixture" + uuid.uuid4().hex
    dash = b"--" + boundary.encode()
    payload = b"\r\n".join([
        dash, b'Content-Disposition: form-data; name="@jsonPayload"', b"", json.dumps(body).encode(),
        dash, f'Content-Disposition: form-data; name="blob"; filename="{filename}"'.encode(),
        b"Content-Type: text/plain", b"", content, dash + b"--", b"",
    ])
    request = urllib.request.Request(url, data=payload, method="POST")
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    request.add_header("Authorization", token)
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"{}")


class ToolboxFixture:
    """An actual PocketBase process with only synthetic records and credentials."""

    def __init__(self, source_root, pocketbase=None):
        self.source_root = Path(source_root)
        self.pocketbase = pocketbase or shutil.which("pocketbase")
        if not self.pocketbase:
            raise FileNotFoundError("pocketbase binary not found; pass --pocketbase")
        self.superuser_email = "fixture-admin@example.test"
        self.superuser_password = "FixtureAdminPassword123"
        self.user_email = "fixture-user@example.test"
        self.user_password = "FixtureUserPassword123"
        self.tmp = None
        self.process = None

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="toolbox-fixture-")
        self.process = None
        try:
            self.root = Path(self.tmp.name)
            self.package = build_package(self.source_root, self.root / "package")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                self.port = sock.getsockname()[1]
            self.url = f"http://127.0.0.1:{self.port}"
            env = {
                "PATH": os.environ.get("PATH", ""), "PB_DATA_DIR": str(self.root / "pb_data"),
                "PB_CORS_ORIGINS": self.url, "PB_BIND": "127.0.0.1",
                "PB_SUPERUSER_EMAIL": self.superuser_email, "PB_SUPERUSER_PASSWORD": self.superuser_password,
                "POCKETBASE_BIN": str(self.pocketbase), "PORT": str(self.port),
            }
            self.process = subprocess.Popen(["/bin/sh", str(self.package / "start.sh")], cwd=self.package, env=env)
            self._wait_for_health()
            self.admin_token = _json_request(self.url + "/api/collections/_superusers/auth-with-password", "POST", {
                "identity": self.superuser_email, "password": self.superuser_password,
            })["token"]
            self._apply_schema()
            self._set_rules_and_seed()
            self.user_token = _json_request(self.url + "/api/collections/users/auth-with-password", "POST", {
                "identity": self.user_email, "password": self.user_password,
            })["token"]
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.tmp:
            self.tmp.cleanup()
            self.tmp = None

    def _wait_for_health(self):
        for _ in range(100):
            try:
                _json_request(self.url + "/api/health")
                return
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(.1)
        self.process.terminate()
        raise RuntimeError("fixture PocketBase did not become healthy")

    def _set_rules_and_seed(self):
        self._patch_collection("users", {
            "listRule": "id = @request.auth.id", "viewRule": "id = @request.auth.id",
            "createRule": None, "updateRule": None, "deleteRule": None,
        })
        for collection in BUSINESS_COLLECTIONS:
            self._patch_collection(collection, {
                "listRule": "@request.auth.id != ''", "viewRule": "@request.auth.id != ''",
                "createRule": None, "updateRule": None, "deleteRule": None,
            })
        _json_request(self.url + "/api/collections/users/records", "POST", {
            "email": self.user_email, "password": self.user_password,
            "passwordConfirm": self.user_password, "verified": True,
        }, self.admin_token)
        first = None
        for index in range(27):
            run = _json_request(self.url + "/api/collections/runs/records", "POST", {
                "harness": "claude" if index % 2 else "opencode",
                "candidate": "fixture-<img src=x onerror=alert(1)>" if index == 0 else f"fixture-{index:02d}",
                "case": f"fixture-case-{index:02d}", "campaign": "toolbox-fixture", "trial": index + 1,
                "model": f"fixture-model-{index % 3}", "passed": bool(index % 2),
                "cost_usd": round((index + 1) / 1000, 3), "duration_ms": 1000 + index * 137,
            }, self.admin_token)
            if first is None:
                first = run
        self.artifact_bytes = b"fixture protected evidence\n"
        self.artifact = _multipart_request(self.url + "/api/collections/artifacts/records", {
            "run": first["id"], "kind": "tool_output", "mime": "text/plain",
            "sha256": hashlib.sha256(self.artifact_bytes).hexdigest(), "byte_size": len(self.artifact_bytes),
        }, "fixture.txt", self.artifact_bytes, self.admin_token)

    def _patch_collection(self, name, body):
        _json_request(self.url + "/api/collections/" + name, "PATCH", body, self.admin_token)

    def _apply_schema(self):
        """Apply existing schema specs directly, without the credential-file-aware PB client."""
        ids = {}
        for name in SCHEMA_ORDER:
            spec = next(spec for spec in collection_specs({key: ids.get(key, "") for key in SCHEMA_ORDER})
                        if spec["name"] == name)
            created = _json_request(self.url + "/api/collections", "POST", spec, self.admin_token)
            ids[name] = created["id"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pocketbase", default=shutil.which("pocketbase"))
    args = parser.parse_args(argv)
    with ToolboxFixture(args.source_root, args.pocketbase) as fixture:
        print(f"URL={fixture.url}")
        print(f"EMAIL={fixture.user_email}")
        print(f"PASSWORD={fixture.user_password}")
        print("Fixture runs until Ctrl-C; all data is deleted on exit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
