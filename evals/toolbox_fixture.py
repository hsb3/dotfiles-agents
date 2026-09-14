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
from load_harness_runs import build_run_row
from schema import collection_specs
from toolbox_access import set_authenticated_read


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
            self.package = build_package(
                self.source_root, self.root / "package", self.source_root / "evals" / "ui" / "dist"
            )
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
        set_authenticated_read(_FixturePB(self), apply=True)
        _json_request(self.url + "/api/collections/users/records", "POST", {
            "email": self.user_email, "password": self.user_password,
            "passwordConfirm": self.user_password, "verified": True,
        }, self.admin_token)
        self._seed_content_graph()
        first = None
        for index in range(27):
            run = _json_request(self.url + "/api/collections/runs/records", "POST", self._run_body(index), self.admin_token)
            if first is None:
                first = run
            if index == 0:
                self.baseline_run = run
            elif index == 1:
                self.with_run = run
        self.artifact_bytes = b"fixture protected evidence\n"
        self.artifact = _multipart_request(self.url + "/api/collections/artifacts/records", {
            "run": first["id"], "kind": "tool_output", "mime": "text/plain",
            "sha256": hashlib.sha256(self.artifact_bytes).hexdigest(), "byte_size": len(self.artifact_bytes),
        }, "fixture.txt", self.artifact_bytes, self.admin_token)
        for run, seq, call_id in ((self.baseline_run, 1001, "ui-fixture-baseline-call"),
                                  (self.with_run, 1001, "ui-fixture-with-call")):
            _json_request(self.url + "/api/collections/run_events/records", "POST", {
                "run": run["id"], "seq": seq, "vendor": "opencode", "role": "tool_call",
                "event_type": "tool_use", "tool_name": "read", "tool_call_id": call_id,
                "status": "completed", "is_error": False, "artifact": self.artifact["id"],
            }, self.admin_token)
            _json_request(self.url + "/api/collections/tool_calls/records", "POST", {
                "run": run["id"], "tool_call_id": call_id, "tool_name": "read",
                "input": {"path": "fixture.txt"}, "output": {"artifact": "shared"},
                "status": "completed", "is_error": False, "artifact": self.artifact["id"],
            }, self.admin_token)

    def _seed_content_graph(self):
        create = lambda name, body: _json_request(
            self.url + f"/api/collections/{name}/records", "POST", body, self.admin_token)
        source = create("sources", {
            "slug": "ui-fixture-source", "name": "UI Fixture Source", "publisher_kind": "first-party",
            "publishes": ["skill"], "trust_tier": "trusted", "maintenance": "active", "status": "active",
        })
        framework = create("frameworks", {
            "slug": "ui-fixture-framework", "name": "UI Fixture Framework", "kind": "job-taxonomy",
            "status": "active", "summary": "Synthetic browser fixture framework.",
        })
        job = create("framework_elements", {
            "framework": framework["id"], "slug": "ui-fixture-job", "name": "Inspect fixture data",
            "element_kind": "job", "description": "Select and inspect an extender.",
        })
        primitive = create("extenders", {
            "slug": "ui-fixture-primitive", "name": "UI Fixture Primitive", "kind": "skill",
            "origin": "authored", "source": source["id"], "shelf": "core", "disposition": "qualified",
            "description": "A synthetic selectable primitive.", "body": "# UI fixture primitive\n",
            "entry_file": "SKILL.md", "file_count": 3,
        })
        for relpath, role, content in (
            ("README.md", "doc", "# Fixture\n"), ("SKILL.md", "entrypoint", "# Skill\n"),
            ("hooks/check.py", "script", "print('fixture')\n"),
        ):
            create("files", {"extender": primitive["id"], "relpath": relpath, "role": role,
                             "content": content, "is_binary": False, "size_bytes": len(content),
                             "sha256": hashlib.sha256(content.encode()).hexdigest(), "language": "markdown"})
        create("distributions", {"slug": "ui-fixture-distribution", "kind": "plugin",
                                 "version": "0.0.0-fixture", "members": [primitive["id"]]})
        evaluation = create("eval_runs", {
            "slug": "ui-fixture-evaluation", "kind": "judged", "status": "running",
            "method": "Synthetic browser fixture", "notes": "Current campaign: ui-fixture-campaign.",
            "frameworks": [framework["id"]],
        })
        create("eval_responses", {"run": evaluation["id"], "role": "candidate", "agent_type": "fixture",
                                  "model": "fixture-model", "prompt": "fixture prompt: inspect the primitive",
                                  "response_text": "fixture response: primitive is readable", "extenders": [primitive["id"]],
                                  "tokens": 0, "duration_ms": 0})
        create("assessments", {"extender": primitive["id"], "framework": framework["id"], "element": job["id"],
                               "eval_run": evaluation["id"], "verdict": "present", "score": 1,
                               "evidence": "Fixture evidence for current campaign.", "assessor": "ui-fixture-assessor"})
        create("job_coverage", {"job": job["id"], "disposition": "author", "status": "covered",
                                "source": source["id"], "rationale": "Fixture coverage.", "eval_run": evaluation["id"]})

    def _run_body(self, index):
        paired = index < 2
        row = {
            "campaign": "ui-fixture-campaign" if paired else "toolbox-fixture",
            "harness": "opencode" if paired else ("claude" if index % 2 else "opencode"),
            "model": "ui-fixture-model" if paired else f"fixture-model-{index % 3}",
            "candidate": "ui-fixture-candidate" if paired else ("fixture-<img src=x onerror=alert(1)>" if index == 2 else f"fixture-{index:02d}"),
            "case": "ui-fixture-case" if paired else f"fixture-case-{index:02d}",
            "config": "baseline" if index == 0 else ("with" if index == 1 else "with"), "trial": 1 if paired else index + 1,
            "kind": "fixture", "grader_model": "ui-fixture-grader" if paired else None,
            "passed": False if index == 0 else bool(index % 2), "skill_used": bool(index % 2), "exit_code": 0 if paired else None,
            "num_turns": 0 if paired else None, "cost_usd": 0 if paired else round((index + 1) / 1000, 3),
            "duration_ms": 0 if paired else 1000 + index * 137, "input_tokens": 0 if paired else None,
            "output_tokens": None, "cache_creation_tokens": None, "cache_read_tokens": None,
            "error": None, "workspace": "fixture", "checks": {"fixture": "complete"},
            "grades": {"fixture-grade": "failed"} if index == 0 else {"fixture-grade": "passed"},
            "tool_names": ["read"], "ts": "2026-09-14T00:00:00", "cli_version": "fixture-0.40.3",
            "preconditions": {"harness": "opencode" if paired else "fixture", "cli_version": "fixture-0.40.3",
                              "model": "ui-fixture-model" if paired else f"fixture-model-{index % 3}",
                              "campaign": "ui-fixture-campaign" if paired else "toolbox-fixture", "grader_model": "ui-fixture-grader" if paired else None,
                              "timeout": 0, "auth_env_present": [], "network_assumption": "offline", "self_installs": []},
            "plugin_errors": [] if paired else None,
        }
        body = build_run_row(row, None, None)
        return body

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


class _FixturePB:
    def __init__(self, fixture):
        self.fixture = fixture

    def get_collection(self, name):
        return _json_request(self.fixture.url + "/api/collections/" + name, token=self.fixture.admin_token)

    def update_collection(self, name, body):
        self.fixture._patch_collection(name, body)


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
