"""Session certificates: native hook replay and local persistent tracker fixture."""
import hashlib
import json
import multiprocessing
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
                    "ATELIER_TOOL_CALL_ID": "call-a",
                    "ATELIER_ACTIVATION_FILE": str(self.root / ".agents/atelier.local.md")}
        self.transcript = self.root / "rollout.jsonl"
        self.transcript.write_text("")
        self.stamp = self.root / ".state/handoff.stamp"
        key = hashlib.sha256(json.dumps(["codex", "writer-a", "native-a"], separators=(",", ":")).encode()).hexdigest()
        self.cert = self.stamp.with_name("handoff." + key + ".stamp")
        self.binding = Path(str(self.cert) + ".binding")

    def transaction(self):
        return Path(str(self.binding) + "." + session.digest(session.read(self.binding)["epoch"]))

    def event(self, kind, call):
        with self.transcript.open("a") as f:
            f.write(json.dumps({"type": "response_item", "payload": {"type": kind, "call_id": call}}) + "\n")

    def hook(self, event="PreCompact", call="call-a", trigger="manual", command=None):
        result = subprocess.run([sys.executable, str(HOOK)], cwd=self.root, env=self.env,
            input=json.dumps({"hook_event_name": event, "session_id": "native-a", "cwd": str(self.root),
                "tool_use_id": call, "trigger": trigger, "transcript_path": str(self.transcript),
                "tool_name": "Bash", "tool_input": {"command": command}}),
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
        result = subprocess.run([sys.executable, str(HELPER), "persist", "--binding", str(self.transaction()),
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
                session.persist(self.transaction(), "fixture", self.root / "missing-body")
        self.assertTrue(self.cert.exists(), "wrong helper invalidated another writer")

    def test_containment_rejects_parent_and_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".state/link").symlink_to(outside)
        for value in ("../escape", "link/escape"):
            with self.assertRaises(ValueError):
                session.contained(self.root / ".state", value)

    def test_unsupported_runtime_allows_tools_but_refuses_manual_compact(self):
        for harness in ("claude-code", "opencode"):
            self.env["ATELIER_HARNESS"] = harness
            self.assertNotEqual(self.hook("PreToolUse").get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            self.assertEqual(self.hook().get("decision"), "block")
            self.assertNotIn("decision", self.hook(trigger="auto"))

    def test_parallel_helper_cannot_borrow_newer_binding(self):
        self.event("function_call", "call-a")
        self.hook("PreToolUse")
        self.event("function_call", "call-b")
        self.assertNotEqual(self.hook("PreToolUse", "call-b").get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
        with patch.dict(os.environ, self.env, clear=True), patch.object(session, "kata") as backend:
            with self.assertRaisesRegex(ValueError, "current sequential"):
                session.persist(self.transaction(), "fixture", self.root / "body")
            backend.assert_not_called()
        self.assertFalse(self.cert.exists())

    def test_parallel_ordinary_calls_proceed_uncertified(self):
        self.seed()
        original = self.transaction()
        self.event("function_call", "call-a2")
        self.event("function_call", "call-b")
        payload = {"hook_event_name": "PreToolUse", "session_id": "native-a",
                   "tool_use_id": "call-a2", "transcript_path": str(self.transcript)}
        with patch.dict(os.environ, self.env, clear=True), patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            denied = session.hook(self.root, {"mode": "external", "stamp": ".state/handoff.stamp"}, payload)
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertTrue(self.cert.exists())
        for call in ("call-a2", "call-b"):
            command = "printf ok"
            result = self.hook("PreToolUse", call, command=command)
            self.assertNotEqual(result.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            self.assertFalse(self.cert.exists())
            command = result.get("hookSpecificOutput", {}).get("updatedInput", {}).get("command", command)
            self.assertEqual(subprocess.check_output(["sh", "-c", command], text=True), "ok")
        with patch.dict(os.environ, self.env, clear=True), patch.object(session, "kata") as backend:
            with self.assertRaises(ValueError):
                session.persist(original, "fixture", self.root / "body")
            backend.assert_not_called()
        self.event("function_call_output", "call-a2")
        self.event("function_call_output", "call-b")
        self.assertFalse(self.hook().get("continue", True))

    def test_delayed_helper_cannot_borrow_binding_after_its_parent_completed(self):
        self.event("function_call", "call-a")
        result = self.hook("PreToolUse")
        original = result["hookSpecificOutput"]["additionalContext"].split("Session handoff binding: ", 1)[1]
        self.event("function_call_output", "call-a")
        self.event("function_call", "call-b")
        self.hook("PreToolUse", "call-b")
        self.cert.write_text("B certificate")
        body = self.root / "body"
        body.write_text("Delayed A handoff")
        with patch.dict(os.environ, self.env, clear=True), patch.object(session, "kata", side_effect=RuntimeError("backend reached")) as backend:
            with self.assertRaises((ValueError, RuntimeError)):
                session.persist(original, "fixture", body)
            backend.assert_not_called()
        self.assertEqual(self.cert.read_text(), "B certificate")

    def persist_fixture(self, failure=None, predecessor=None):
        self.event("function_call", "call-a")
        self.hook("PreToolUse")
        body = self.root / "body"
        body.write_text("\n  Exact handoff with trailing newline.\n")
        card = {}
        def backend(project, *args):
            if args == ("show", "work"):
                return {"issue": {"short_id": "work", "status": "open", "metadata": {}}, "labels": []}
            if args[0] == "list": return {"issues": []}
            if args[0] == "create":
                if failure == "write": raise subprocess.CalledProcessError(1, "kata")
                metadata = dict(args[i+1].split("=", 1) for i, arg in enumerate(args) if arg == "--meta")
                card.update(short_id="own", status="open", body=args[args.index("--body")+1], metadata=metadata)
                self.persisted_card = card
                return {"issue": card.copy()}
            if failure == "readback": raise OSError("backend readback failed")
            if failure == "stale":
                self.event("function_call", "call-b")
            return {"issue": card.copy(), "links": []}
        with patch.dict(os.environ, self.env, clear=True), patch.object(session, "repository", return_value=("repo", "branch")), patch.object(session, "kata", side_effect=backend):
            return session.persist(self.transaction(), "fixture", body, predecessor=predecessor)

    def test_persistence_normalization_and_complete_metadata(self):
        result = self.persist_fixture()
        self.assertEqual(result["card"], "own")
        self.assertEqual(self.persisted_card["metadata"].get("handoff.repository"), "repo")
        self.assertEqual(self.persisted_card["metadata"].get("work.branch"), "branch")
        proof = session.read(self.cert)
        self.assertEqual(proof["body_sha256"], hashlib.sha256(b"Exact handoff with trailing newline.").hexdigest())

    def test_backend_failure_and_stale_completion_cannot_certify(self):
        for failure in ("write", "readback", "stale"):
            with self.subTest(failure=failure):
                self.transcript.write_text("")
                with self.assertRaises((OSError, ValueError, subprocess.CalledProcessError)):
                    self.persist_fixture(failure)
                self.assertFalse(self.cert.exists())

    def test_discovery_scans_beyond_display_page_and_retains_unknown(self):
        cards = [{"short_id": str(i), "title": "Handoff " + str(i), "metadata": {}, "status": "open"} for i in range(13)]
        cards[0]["metadata"] = cards[-1]["metadata"] = {"handoff.writer": "duplicate"}
        readbacks = []
        def backend(project, *args):
            if args[0] == "list":
                self.assertEqual(args[-2:], ("--limit", "0"))
                return {"issues": cards}
            readbacks.append(args[1])
            return {"issue": cards[int(args[1])], "links": []}
        with patch.object(session, "repository", return_value=("repo", "branch")), patch.object(session, "kata", side_effect=backend):
            first = session.discover("fixture", self.root)
            self.assertEqual(len(readbacks), 13)
            self.assertEqual(first["rows"][0]["conflicts"], ["12"])
            self.assertEqual(first["remaining"], 3)
            last = session.discover("fixture", self.root, **first["continuation"])
            self.assertEqual(len({r["card"] for r in first["rows"] + last["rows"]}), 13)
            self.assertTrue(all(r["relevance"] == "unknown" for r in first["rows"] + last["rows"]))
            self.assertIsNone(last["continuation"])

    def test_mirrored_card_is_never_a_native_destination(self):
        for metadata in ({"github_issue": 12}, {"github_issue": None}, {"github_url": "https://example.invalid/issue"}):
            with self.assertRaises(ValueError):
                session.native_card({"status": "open", "metadata": metadata})

    def test_predecessor_must_be_a_handoff_before_any_backend_write(self):
        with self.assertRaises(ValueError):
            self.persist_fixture(predecessor="work")
        self.assertFalse(hasattr(self, "persisted_card"), "ordinary work card was accepted as predecessor")

    @unittest.skipUnless(os.name == "posix", "POSIX helper protocol")
    def test_delayed_backend_edit_cannot_outlive_newer_certification(self):
        import fcntl
        ctx = multiprocessing.get_context("fork")
        events, release = ctx.Queue(), ctx.Event()
        self.event("function_call", "call-a")
        self.hook("PreToolUse")
        original = self.transaction()
        store = self.root / "backend.json"
        store.write_text(json.dumps({"short_id": "own", "status": "open", "body": "seed",
            "metadata": {"handoff.writer": session.read(self.binding)["key"]}}))
        for name in ("A", "B"):
            (self.root / name).write_text("body " + name)

        def worker(name, transaction, call):
            real_flock = fcntl.flock
            def acquire(file, operation):
                if name == "B": events.put("B_lock")
                return real_flock(file, operation)
            def backend(project, *args):
                if args[0] == "edit" and name == "A":
                    events.put("A_wait")
                    if not release.wait(10): raise RuntimeError("A barrier timed out")
                issue = json.loads(store.read_text())
                if args[0] == "list": return {"issues": [issue]}
                if args[0] == "edit":
                    issue["body"] = args[args.index("--body") + 1]
                if args[0] == "meta": issue["metadata"][args[3]] = args[4]
                if args[0] in ("edit", "meta"): store.write_text(json.dumps(issue))
                return {"issue": issue, "links": []}
            try:
                with patch.dict(os.environ, dict(self.env, ATELIER_TOOL_CALL_ID=call), clear=True), patch.object(session, "repository", return_value=("repo", "branch")), patch.object(session, "kata", side_effect=backend), patch.object(fcntl, "flock", side_effect=acquire):
                    session.persist(transaction, "fixture", self.root / name)
                events.put(name + "_done")
            except Exception as error:
                events.put(name + "_error:" + str(error))

        a = ctx.Process(target=worker, args=("A", original, "call-a"))
        b = None
        try:
            a.start()
            self.assertEqual(events.get(timeout=10), "A_wait")
            self.event("function_call_output", "call-a")
            self.event("function_call", "call-b")
            self.hook("PreToolUse", "call-b")
            b = ctx.Process(target=worker, args=("B", self.transaction(), "call-b"))
            b.start()
            seen = [events.get(timeout=10)]
            # With the lock B is waiting; without it B has already certified its body.
            self.assertIn(seen[0], ("B_lock", "B_done"))
            release.set()
            while not any(s.startswith("A_error:") for s in seen) or "B_done" not in seen:
                seen.append(events.get(timeout=10))
            a.join(10); b.join(10)
            self.assertFalse(a.is_alive() or b.is_alive())
            self.event("function_call_output", "call-b")
            with patch.dict(os.environ, self.env, clear=True):
                session.check(self.root, {"mode": "external", "stamp": ".state/handoff.stamp"},
                              {"session_id": "native-a", "transcript_path": str(self.transcript)}, 30)
            actual = json.loads(store.read_text())["body"]
            self.assertEqual(actual, "body B", "accepted B certificate survived a stale A backend overwrite")
            self.assertEqual(session.read(self.cert)["body_sha256"], hashlib.sha256(actual.encode()).hexdigest())
        finally:
            release.set()
            for process in (a, b):
                if process is not None and process.pid is not None:
                    if process.is_alive(): process.terminate()
                    process.join(10)
            events.close()

    @unittest.skipUnless(os.name == "posix", "POSIX helper protocol")
    def test_distinct_writers_use_distinct_helper_locks(self):
        import fcntl
        acquired = []
        real_flock = fcntl.flock
        def observe(file, operation):
            acquired.append(Path(file.name))
            return real_flock(file, operation)
        with patch.object(fcntl, "flock", side_effect=observe):
            self.persist_fixture()
            self.transcript.write_text("")
            self.env["ATELIER_WRITER_ID"] = "writer-b"
            self.cert, self.binding, _ = session.paths(self.root,
                {"mode": "external", "stamp": ".state/handoff.stamp"}, "codex", "writer-b", "native-a")
            self.persist_fixture()
        self.assertEqual(len(acquired), 2)
        self.assertEqual(acquired[0].parent, acquired[1].parent)
        self.assertNotEqual(acquired[0], acquired[1])

    def test_unavailable_os_lock_never_runs_unlocked(self):
        with patch.dict(sys.modules, {"fcntl": None}):
            with self.assertRaisesRegex(ValueError, "POSIX advisory locks"):
                self.persist_fixture()
        self.assertFalse(hasattr(self, "persisted_card"))
