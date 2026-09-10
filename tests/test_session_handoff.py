"""Session certificates: native hook replay and local persistent tracker fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "primitives-core/hooks/handoff-freshness-guard/hook.py"
HELPER = ROOT / "primitives-core/hooks/_lib/session_handoff.py"
sys.path.insert(0, str(HELPER.parent))
import session_handoff as session

class SessionHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".agents").mkdir()
        (self.root / ".agents/atelier.local.md").write_text(
            "---\nhandoff:\n  mode: external\n  scope: session\n  stamp: .state/handoff.stamp\n  location: Lead bridge\n---\n")
        (self.root / ".state").mkdir()
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.root),
                    "XDG_DATA_HOME": str(self.root / "data"), "ATELIER_HARNESS": "codex",
                    "ATELIER_WRITER_ID": "writer-a", "CODEX_THREAD_ID": "native-a",
                    "ATELIER_ACTIVATION_FILE": str(self.root / ".agents/atelier.local.md")}
        self.transcript = self.root / "rollout.jsonl"
        self.transcript.write_text("")
        self.stamp = self.root / ".state/handoff.stamp"
        key = hashlib.sha256(json.dumps(["codex", "writer-a", "native-a"], separators=(",", ":")).encode()).hexdigest()
        self.cert = self.stamp.with_name("handoff." + key + ".stamp")
        self.binding = Path(str(self.cert) + ".binding")

    def event(self, kind, call):
        with self.transcript.open("a") as f:
            f.write(json.dumps({"type": "response_item", "payload": {"type": kind, "call_id": call}}) + "\n")

    def hook(self, event="PreCompact", call="call-a", trigger="manual"):
        result = subprocess.run([sys.executable, str(HOOK)], cwd=self.root, env=self.env,
            input=json.dumps({"hook_event_name": event, "session_id": "native-a", "cwd": str(self.root),
                "tool_use_id": call, "trigger": trigger, "transcript_path": str(self.transcript)}),
            text=True, capture_output=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def seed(self):
        self.event("function_call", "call-a")
        self.hook("PreToolUse")
        self.assertTrue(self.binding.exists(), "native prehook did not establish a binding")
        # A valid certificate from an earlier completed handoff; the baseline only reads mtime.
        binding = json.loads(self.binding.read_text()) if self.binding.exists() else {}
        self.cert.write_text(json.dumps({"binding": binding, "card": "native-card", "body_sha256": "a" * 64}))
        self.stamp.touch()
        self.event("function_call_output", "call-a")
        self.assertEqual(self.hook(trigger="auto"), {}, "seed certificate was not fresh")

    def test_fresh_correct_hook_certificate_wrong_tool_identity_failed_update(self):
        self.seed()
        self.event("function_call", "call-b")
        self.hook("PreToolUse", "call-b")
        result = subprocess.run([sys.executable, str(HELPER), "persist", "--binding", str(self.binding),
            "--project", "fixture", "--body-file", str(self.root / "missing-body")],
            env=dict(self.env, ATELIER_WRITER_ID="wrong-writer"), capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.event("function_call_output", "call-b")
        self.assertFalse(self.hook().get("continue", True), "failed update retained correct hook freshness")

    def test_malformed_runtime_records_fail_closed(self):
        for item in ([], {"type": "response_item", "payload": []}):
            with self.subTest(item=item):
                self.transcript.write_text("")
                self.seed()
                with self.transcript.open("a") as f:
                    f.write(json.dumps(item) + "\n")
                self.assertFalse(self.hook().get("continue", True))
                self.assertNotIn("continue", self.hook(trigger="auto"))

    def test_failed_certificate_fsync_does_not_publish(self):
        with patch.object(session.os, "fsync", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                session.write(self.cert, {"card": "persisted"})
        self.assertFalse(self.cert.exists(), "failed certificate write left valid JSON")

    def test_failed_certificate_readback_does_not_publish(self):
        with patch.object(session, "read", side_effect=OSError("readback failure")):
            with self.assertRaises(OSError):
                session.write(self.cert, {"card": "persisted"})
        self.assertFalse(self.cert.exists(), "failed certificate readback left valid JSON")

    def test_consumed_certificate_cannot_be_reused(self):
        self.seed()
        self.assertEqual(self.hook(), {})
        self.assertFalse(self.cert.exists())
        self.assertFalse(self.hook().get("continue", True))

    def test_missing_registration_cannot_reuse_previous_binding(self):
        self.seed()
        self.event("function_call", "unhooked")
        self.event("function_call_output", "unhooked")
        self.assertFalse(self.hook().get("continue", True))

    def test_failed_invalidation_cannot_reuse_old_certificate(self):
        self.seed()
        self.event("function_call", "call-b")
        payload = {"session_id": "native-a", "tool_use_id": "call-b",
                   "transcript_path": str(self.transcript), "hook_event_name": "PreToolUse"}
        config = {"mode": "external", "stamp": ".state/handoff.stamp"}
        for target in ("write", "unlink"):
            with self.subTest(target=target), patch.dict(os.environ, self.env, clear=True):
                context = patch.object(session, "write", side_effect=PermissionError("denied")) if target == "write" else patch.object(Path, "unlink", side_effect=PermissionError("denied"))
                with context:
                    result = session.hook(str(self.root), config, payload)
                self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
        self.event("function_call_output", "call-b")
        self.assertFalse(self.hook().get("continue", True))

    def test_pending_tool_and_missing_identity_block(self):
        self.seed()
        self.event("function_call", "parallel")
        self.assertFalse(self.hook().get("continue", True))
        self.event("function_call_output", "parallel")
        self.env.pop("ATELIER_WRITER_ID")
        self.assertFalse(self.hook().get("continue", True))
        self.assertNotIn("continue", self.hook(trigger="auto"))

    def test_own_stamp_only_and_distinct_resume_keys(self):
        self.seed()
        config = {"mode": "external", "stamp": ".state/handoff.stamp"}
        sibling, _, _ = session.paths(self.root, config, "codex", "writer-b", "native-a")
        sibling.write_text("sibling certificate")
        self.event("function_call", "call-b")
        self.hook("PreToolUse", "call-b")
        self.assertFalse(self.cert.exists())
        self.assertEqual(sibling.read_text(), "sibling certificate")

    def test_mismatched_helper_cannot_delete_another_writers_certificate(self):
        self.seed()
        with patch.dict(os.environ, dict(self.env, ATELIER_WRITER_ID="writer-b"), clear=True):
            with self.assertRaises(ValueError):
                session.persist(self.binding, "fixture", self.root / "missing-body")
        self.assertTrue(self.cert.exists(), "wrong helper invalidated another writer")

    def test_containment_rejects_parent_and_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".state/link").symlink_to(outside)
        for value in ("../escape", "link/escape"):
            with self.assertRaises(ValueError):
                session.contained(self.root / ".state", value)
