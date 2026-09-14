"""Disposable real-PocketBase wire regression for harness measurements and evidence."""

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
sys.path.insert(0, str(EVALS))
import load_harness_runs as loader  # noqa: E402
import load_eval_run  # noqa: E402


PB_BINARY = os.environ.get("PB_BINARY", "/opt/homebrew/bin/pocketbase")
EMAIL = "wire@example.test"
PASSWORD = "WirePassword12345"


def request(url, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read() or b"{}")


def claude_log(call_id, content):
    return "\n".join(json.dumps(event) for event in (
        {"type": "system", "subtype": "init", "session_id": call_id, "tools": ["Write"]},
        {"type": "assistant", "session_id": call_id, "message": {"role": "assistant",
         "content": [{"type": "tool_use", "id": call_id, "name": "Write",
                      "input": {"file_path": "/tmp/evidence.txt", "content": content}}]}},
        {"type": "user", "session_id": call_id, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": "written"}]}},
    ))


def ledger_row(trial, log_path, **metrics):
    row = {"campaign": "wire", "harness": "claude", "model": "wire-model",
           "candidate": "candidate", "case": f"case-{trial}", "config": "with",
           "trial": trial, "kind": "mechanical", "log_path": str(log_path),
           "preconditions": {"harness": "claude", "cli_version": "wire", "model": "wire-model",
                             "campaign": "wire", "network_assumption": "offline", "grader_model": None,
                             "timeout": 0, "auth_env_present": [], "self_installs": []},
           "plugin_errors": [], "exit_code": 0}
    row.update(metrics)
    return row


class ProjectionWireTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            version = subprocess.run([PB_BINARY, "--version"], text=True, capture_output=True,
                                     check=False).stdout.strip()
        except FileNotFoundError:
            raise unittest.SkipTest(f"PocketBase unavailable: {PB_BINARY} not found")
        if version != "pocketbase version 0.40.3":
            raise unittest.SkipTest(f"PocketBase 0.40.3 required, found: {version or 'unknown'}")

    def setUp(self):
        self.tmp = self.server = None
        self.old_pb_env = {}
        try:
            self.tmp = tempfile.TemporaryDirectory(prefix="projection-wire-")
            self.root = Path(self.tmp.name)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                self.port = sock.getsockname()[1]
            self.url = f"http://127.0.0.1:{self.port}"
            self.env = os.environ | {"PB_URL": self.url, "PB_ADMIN_EMAIL": EMAIL,
                                     "PB_ADMIN_PASSWORD": PASSWORD}
            self.old_pb_env = {key: os.environ.get(key) for key in self.env if key.startswith("PB_")}
            os.environ.update({key: value for key, value in self.env.items() if key.startswith("PB_")})
            data = self.root / "pb_data"
            subprocess.run([PB_BINARY, "superuser", "create", EMAIL, PASSWORD, "--dir", str(data)],
                           check=True, text=True, capture_output=True)
            self.server = subprocess.Popen([PB_BINARY, "serve", "--http", f"127.0.0.1:{self.port}",
                                            "--dir", str(data)], stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    request(self.url + "/api/health")
                    break
                except OSError:
                    time.sleep(.05)
            else:
                self.fail("PocketBase did not become healthy")
            subprocess.run([sys.executable, str(EVALS / "schema.py")], cwd=EVALS, env=self.env,
                           check=True, text=True, capture_output=True)
        except BaseException:
            self.tearDown()
            raise

    def tearDown(self):
        if getattr(self, "server", None) and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=10)
        if getattr(self, "tmp", None):
            self.tmp.cleanup()
        for key, value in getattr(self, "old_pb_env", {}).items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def ingest(self, rows):
        path = self.root / "results.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        parsed = loader.parse_ledger(str(path), loader.Scope(campaign="wire"))
        links, warnings = loader.link_logs(parsed, str(self.root))
        self.assertEqual(warnings, [])
        return loader.plan(loader.PB(), loader.build_aggregate(parsed, links), loader.Scope(campaign="wire"), False)

    def test_measurements_campaign_replay_and_shared_protected_artifact(self):
        manifest_path = self.root / "campaign.json"
        manifest = {"run": {"slug": "wire-campaign", "kind": "judged"}, "responses": [
            {"role": "judge", "tokens": 0, "duration_ms": 7}]}
        manifest_path.write_text(json.dumps(manifest))
        campaign_pb = load_eval_run.PB()
        load_eval_run.load_manifest(campaign_pb, str(manifest_path))
        first_response = campaign_pb.list_all("eval_responses")[0]
        manifest["responses"][0].pop("duration_ms")
        manifest_path.write_text(json.dumps(manifest))
        load_eval_run.load_manifest(campaign_pb, str(manifest_path))
        second_response = campaign_pb.list_all("eval_responses")[0]
        self.assertEqual(second_response["id"], first_response["id"])
        self.assertEqual(second_response["tokens"], 0)
        self.assertEqual(second_response["duration_ms"], 0)
        self.assertFalse(second_response["measurement"]["available"]["duration_ms"])
        projection = {key: second_response[key] for key in
                      ("id", "role", "tokens", "duration_ms", "measurement")}
        load_eval_run.load_manifest(campaign_pb, str(manifest_path))
        replay = campaign_pb.list_all("eval_responses")
        self.assertEqual(len(replay), 1)
        self.assertEqual({key: replay[0][key] for key in projection}, projection)
        evidence = "shared protected evidence\n" + "x" * loader.ARTIFACT_TEXT_THRESHOLD
        logs = []
        for trial in (1, 2):
            log = self.root / f"trial-{trial}.log"
            log.write_text(claude_log(f"call-{trial}", evidence))
            logs.append(log)
        observed = [ledger_row(1, logs[0], passed=False, skill_used=False, num_turns=0,
                               cost_usd=0, duration_ms=0, input_tokens=0, output_tokens=0),
                    ledger_row(2, logs[1], passed=False, skill_used=False, num_turns=0,
                               cost_usd=0, duration_ms=0, input_tokens=0, output_tokens=0)]
        first = self.ingest(observed)
        self.assertEqual(first["runs"], (2, 0, 0))
        self.assertEqual(first["artifacts"], (1, 0, 0))

        pb = loader.PB()
        runs = pb.list_all("runs", "campaign='wire'")
        self.assertEqual(len(runs), 2)
        for run in runs:
            measurement = run["measurement"]
            self.assertTrue(measurement["available"]["passed"])
            self.assertTrue(measurement["available"]["num_turns"])
            self.assertFalse(run["passed"])
            self.assertEqual(run["num_turns"], 0)

        artifacts = pb.list_all("artifacts")
        self.assertEqual(len(artifacts), 1)
        artifact = artifacts[0]
        event_refs = [(row["id"], row.get("artifact")) for row in pb.list_all("run_events")]
        call_refs = [(row["id"], row.get("artifact")) for row in pb.list_all("tool_calls")]
        self.assertEqual(sum(ref == artifact["id"] for _, ref in event_refs), 2)
        self.assertEqual(sum(ref == artifact["id"] for _, ref in call_refs), 2)
        rules = {"listRule": "@request.auth.id != ''", "viewRule": "@request.auth.id != '' && id != ''",
                 "createRule": "@request.auth.id != '' && byte_size >= 0",
                 "updateRule": "@request.auth.id != '' && sha256 != ''",
                 "deleteRule": "@request.auth.id != '' && mime != ''"}
        pb._req("PATCH", "/api/collections/artifacts", rules)
        before = pb.get_collection("artifacts")
        blob_before = next(field for field in before["fields"] if field["name"] == "blob")
        subprocess.run([sys.executable, str(EVALS / "schema.py")], cwd=EVALS, env=self.env,
                       check=True, text=True, capture_output=True)
        after = pb.get_collection("artifacts")
        blob_after = next(field for field in after["fields"] if field["name"] == "blob")
        for key, value in rules.items():
            self.assertEqual(after[key], value)
        self.assertEqual(blob_after["id"], blob_before["id"])
        self.assertTrue(blob_after.get("protected") or blob_after.get("options", {}).get("protected"))
        artifact = pb.find_first("artifacts", f"sha256='{artifact['sha256']}'")
        self.assertEqual(artifact["blob"], artifacts[0]["blob"])
        self.assertEqual([(row["id"], row.get("artifact")) for row in pb.list_all("run_events")], event_refs)
        self.assertEqual([(row["id"], row.get("artifact")) for row in pb.list_all("tool_calls")], call_refs)
        token = pb._req("POST", "/api/files/token", {})["token"]
        blob = urllib.parse.quote(artifact["blob"])
        with urllib.request.urlopen(f"{self.url}/api/files/artifacts/{artifact['id']}/{blob}?token={token}") as response:
            self.assertEqual(hashlib.sha256(response.read()).hexdigest(), artifact["sha256"])

        prior_runs = {run["id"]: (run["session_id"], run["era"],
                                   run["measurement"]["source_identity"]["log_sha256"])
                    for run in runs}
        for log in logs:
            log.unlink()
        missing = [ledger_row(1, logs[0]), ledger_row(2, logs[1])]
        changed = self.ingest(missing)
        self.assertEqual(changed["runs"], (0, 2, 0))
        for run in pb.list_all("runs", "campaign='wire'"):
            self.assertFalse(run["measurement"]["available"]["passed"])
            self.assertFalse(run["measurement"]["available"]["num_turns"])
            # PB projects cleared optional scalars to its bool/number defaults; measurement
            # is the versioned wire contract that keeps that default from fabricating data.
            self.assertFalse(run["passed"])
            self.assertEqual(run["num_turns"], 0)
            self.assertEqual((run["session_id"], run["era"],
                              run["measurement"]["source_identity"]["log_sha256"]), prior_runs[run["id"]])
        self.assertEqual([(row["id"], row.get("artifact")) for row in pb.list_all("run_events")], event_refs)
        self.assertEqual([(row["id"], row.get("artifact")) for row in pb.list_all("tool_calls")], call_refs)
        token = pb._req("POST", "/api/files/token", {})["token"]
        with urllib.request.urlopen(f"{self.url}/api/files/artifacts/{artifact['id']}/{blob}?token={token}") as response:
            self.assertEqual(hashlib.sha256(response.read()).hexdigest(), artifact["sha256"])
        self.assertEqual(self.ingest(missing)["runs"], (0, 0, 2))
