"""Hermetic tests for evals/load_harness_runs.py — the run-log corpus ingester.

No PocketBase, no network, no reading harness/runs/: every fixture is a small inline
log (a handful of lines, shaped from the real claude stream-json / opencode JSONL) or a
tempdir of empty files for the linkage tests. Stdlib-only, discovered by `make test`.

Covers: era detection (legacy/post/na); thinking_tokens drop + seq stability; role
mapping (both vendors); claude tool_use<->tool_result pair-join incl. no_result;
opencode step_finish rollup sums; mirror dedup (claude tool_use_result + opencode
filediff); base64 image extraction -> sha256 + {"$artifact": ...} marker; oversized
write externalization at the 5000-char boundary; legacy filename linkage incl.
claimed-log exclusion and the ambiguity warning.
"""

import base64
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evals"))
import load_harness_runs as L  # noqa: E402


def _log(*events: dict) -> str:
    """Serialize event dicts to a one-JSON-object-per-line log body."""
    return "\n".join(json.dumps(e) for e in events)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _init(tools: list[str], session: str = "sess-1") -> dict:
    return {"type": "system", "subtype": "init", "session_id": session, "tools": tools,
            "apiKeySource": "apiKeyHelper", "plugins": []}


def _assistant_tool(call_id: str, name: str, inp: dict) -> dict:
    return {"type": "assistant", "session_id": "sess-1",
            "message": {"role": "assistant", "usage": {"input_tokens": 5, "output_tokens": 7,
                        "cache_read_input_tokens": 2, "cache_creation_input_tokens": 3},
                        "content": [{"type": "tool_use", "id": call_id, "name": name, "input": inp}]}}


def _user_result(call_id: str, content, tur: dict | None = None,
                 is_error: bool = False, ts: str = "2026-07-21T19:00:48.339Z") -> dict:
    ev = {"type": "user", "session_id": "sess-1", "timestamp": ts,
          "message": {"role": "user", "content": [
              {"type": "tool_result", "tool_use_id": call_id, "content": content,
               "is_error": is_error}]}}
    if tur is not None:
        ev["tool_use_result"] = tur
    return ev


def _result(text: str = "done") -> dict:
    return {"type": "result", "subtype": "success", "session_id": "sess-1",
            "is_error": False, "result": text, "total_cost_usd": 0.01,
            "modelUsage": {"claude-sonnet-4-5": {"costUSD": 0.01}}}


def _oc(etype: str, part: dict, ts: int, session: str = "ses-oc") -> dict:
    return {"type": etype, "timestamp": ts, "sessionID": session, "part": part}


def _oc_tool(call_id: str, tool: str, inp: dict, output: str, start: int, end: int,
             status: str = "completed", metadata: dict | None = None,
             attachments: list | None = None) -> dict:
    state = {"status": status, "input": inp, "output": output,
             "time": {"start": start, "end": end}}
    if metadata is not None:
        state["metadata"] = metadata
    if attachments is not None:
        state["attachments"] = attachments
    return {"callID": call_id, "tool": tool, "type": "tool", "state": state}


def _oc_step_finish(cost: float, inp: int, out: int, read: int, write: int) -> dict:
    return {"type": "step-finish", "cost": cost,
            "tokens": {"input": inp, "output": out, "reasoning": 0,
                       "cache": {"read": read, "write": write}}}


class EraDetection(unittest.TestCase):
    def test_legacy_when_init_has_few_tools(self):
        p = L.parse_claude_log(_log(_init(["Read", "Edit", "Bash"]), _result()))
        self.assertEqual(p.era, "legacy")
        self.assertEqual(p.session_id, "sess-1")

    def test_post_when_init_has_many_tools(self):
        p = L.parse_claude_log(_log(_init([f"t{i}" for i in range(25)]), _result()))
        self.assertEqual(p.era, "post")

    def test_boundary_five_tools_is_legacy(self):
        self.assertEqual(L.parse_claude_log(_log(_init(["a", "b", "c", "d", "e"]))).era, "legacy")
        self.assertEqual(L.parse_claude_log(_log(_init(["a", "b", "c", "d", "e", "f"]))).era, "post")

    def test_opencode_era_is_na(self):
        p = L.parse_opencode_log(_log(_oc("text", {"text": "hi"}, 1000)))
        self.assertEqual(p.era, "na")
        self.assertEqual(p.session_id, "ses-oc")


class ThinkingDropAndSeq(unittest.TestCase):
    def test_thinking_tokens_dropped_and_seq_is_physical_line_index(self):
        log = _log(
            _init(["Read"]),                                    # line 0
            {"type": "system", "subtype": "thinking_tokens"},   # line 1 (dropped)
            _assistant_tool("c1", "Read", {"file_path": "/x"}),  # line 2
            {"type": "system", "subtype": "thinking_tokens"},   # line 3 (dropped)
            _result(),                                          # line 4
        )
        p = L.parse_claude_log(log)
        seqs = [e["seq"] for e in p.events]
        self.assertEqual(seqs, [0, 2, 4])                       # gaps preserved
        self.assertTrue(all(e["event_type"] != "system/thinking_tokens" for e in p.events))


class RoleMapping(unittest.TestCase):
    def test_claude_roles(self):
        log = _log(_init(["Read"]), _assistant_tool("c1", "Read", {"file_path": "/x"}),
                   _user_result("c1", "content-x"), _result())
        by_type = {e["event_type"]: e["role"] for e in L.parse_claude_log(log).events}
        self.assertEqual(by_type["system/init"], "system")
        self.assertEqual(by_type["assistant"], "assistant")
        self.assertEqual(by_type["user"], "tool_result")
        self.assertEqual(by_type["result/success"], "result")

    def test_opencode_roles(self):
        log = _log(
            _oc("step_start", {"type": "step-start"}, 1000),
            _oc("text", {"text": "hi"}, 1001),
            _oc("tool_use", _oc_tool("t1", "read", {"filePath": "/a"}, "out", 1002, 1003), 1002),
            _oc("step_finish", _oc_step_finish(0.1, 1, 2, 0, 0), 1004),
        )
        by_type = {e["event_type"]: e["role"] for e in L.parse_opencode_log(log).events}
        self.assertEqual(by_type["step_start"], "system")
        self.assertEqual(by_type["text"], "assistant")
        self.assertEqual(by_type["tool_use"], "tool_call")
        self.assertEqual(by_type["step_finish"], "system")


class ClaudePairJoin(unittest.TestCase):
    def test_matched_call_carries_output_and_ok_status(self):
        log = _log(_init(["Read"]), _assistant_tool("c1", "Read", {"file_path": "/x"}),
                   _user_result("c1", "the-output"))
        p = L.parse_claude_log(log)
        self.assertEqual(len(p.tool_calls), 1)
        call = p.tool_calls[0]
        self.assertEqual(call["tool_call_id"], "c1")
        self.assertEqual(call["output"], "the-output")
        self.assertEqual(call["status"], "ok")
        self.assertIsNotNone(call["started_ts"])

    def test_error_result_sets_error_status(self):
        log = _log(_init(["Bash"]), _assistant_tool("c1", "Bash", {"command": "x"}),
                   _user_result("c1", "boom", is_error=True))
        call = L.parse_claude_log(log).tool_calls[0]
        self.assertEqual(call["status"], "error")
        self.assertTrue(call["is_error"])

    def test_unmatched_call_is_no_result(self):
        log = _log(_init(["Read"]), _assistant_tool("c1", "Read", {"file_path": "/x"}))
        call = L.parse_claude_log(log).tool_calls[0]
        self.assertEqual(call["status"], "no_result")
        self.assertIsNone(call["output"])


class OpencodeRollup(unittest.TestCase):
    def test_rollup_sums_cost_tokens_and_duration(self):
        log = _log(
            _oc("step_start", {"type": "step-start"}, 1000),
            _oc("step_finish", _oc_step_finish(0.10, 3, 4, 1, 2), 1500),
            _oc("step_finish", _oc_step_finish(0.20, 5, 6, 3, 4), 5000),
        )
        p = L.parse_opencode_log(log)
        self.assertAlmostEqual(p.rollup["cost_usd"], 0.30)
        self.assertEqual(p.rollup["input_tokens"], 8)
        self.assertEqual(p.rollup["output_tokens"], 10)
        self.assertEqual(p.rollup["cache_read_tokens"], 4)
        self.assertEqual(p.rollup["cache_creation_tokens"], 6)
        self.assertEqual(p.rollup["duration_ms"], 4000)      # 5000 - 1000

    def test_rollup_fills_run_row_but_ledger_wins(self):
        p = L.parse_opencode_log(_log(_oc("step_finish", _oc_step_finish(0.2, 9, 9, 0, 0), 1000)))
        row = {"harness": "opencode", "candidate": "c", "case": "k", "config": "with",
               "trial": 0, "cost_usd": 0.99, "input_tokens": None}
        body = L.build_run_row(row, p, "harness/runs/x.log")
        self.assertEqual(body["era"], "na")
        self.assertEqual(body["cost_usd"], 0.99)              # ledger wins
        self.assertEqual(body["input_tokens"], 9)             # filled from rollup


def _valid_preconditions() -> dict:
    return {
        "harness": "opencode", "cli_version": "1.0", "model": "model",
        "campaign": "campaign", "grader_model": None, "timeout": 30,
        "auth_env_present": [], "network_assumption": "assumed-available",
        "self_installs": [],
    }


def _measurement_row(**overrides) -> dict:
    row = {
        "harness": "opencode", "candidate": "c", "case": "k", "config": "with",
        "trial": 0, "passed": False, "skill_used": False, "exit_code": 0,
        "plugin_errors": [], "error": None, "preconditions": _valid_preconditions(),
        "cost_usd": 0, "input_tokens": 0,
    }
    row.update(overrides)
    return row


class MeasurementContract(unittest.TestCase):
    def test_valid_failed_result_keeps_zero_false_and_ledger_identity(self):
        row = _measurement_row()
        body = L.build_run_row(row, None, None)
        measurement = body["measurement"]
        self.assertEqual(measurement["version"], 1)
        self.assertEqual(measurement["source"], "harness-ledger")
        self.assertTrue(measurement["available"]["passed"])
        self.assertTrue(measurement["available"]["skill_used"])
        self.assertTrue(measurement["available"]["cost_usd"])
        self.assertEqual(measurement["provenance"]["cost_usd"], "ledger")
        self.assertEqual(measurement["execution"]["validity"], "valid")
        self.assertEqual(measurement["execution"]["preconditions"], row["preconditions"])
        self.assertIsInstance(measurement["source_identity"]["record_sha256"], str)
        self.assertEqual(measurement["source_identity"]["record_canonicalization"],
                         "json-sorted-keys-utf8")
        self.assertFalse(measurement["source_identity"]["log_available"])
        self.assertIsNone(measurement["source_identity"]["log_sha256"])
        self.assertEqual(measurement["source_identity"]["log_observation"], "unobserved-local")
        self.assertEqual(body["plugin_errors"], [])
        self.assertEqual(body["preconditions"], row["preconditions"])

    def test_missing_values_remain_unavailable_but_zero_and_false_are_observed(self):
        body = L.build_run_row(_measurement_row(num_turns=None, duration_ms=None), None, None)
        measurement = body["measurement"]
        self.assertFalse(measurement["available"]["num_turns"])
        self.assertIsNone(measurement["provenance"]["num_turns"])
        self.assertEqual(body["num_turns"], None)
        self.assertFalse(body["passed"])
        self.assertEqual(body["cost_usd"], 0)

    def test_invalid_numeric_values_fail_before_db_write(self):
        for value in (True, -1, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    L.build_run_row(_measurement_row(duration_ms=value), None, None)

    def test_boolean_metrics_reject_coercible_non_booleans_before_writes(self):
        for field, value in (("passed", "false"), ("passed", 0), ("skill_used", "true"),
                             ("skill_used", 1)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    L.build_run_row(_measurement_row(**{field: value}), None, None)

    def test_negative_integer_exit_code_is_an_invalid_execution_not_bad_measurement(self):
        execution = L.build_run_row(_measurement_row(exit_code=-1), None, None)["measurement"]["execution"]
        self.assertEqual(execution["validity"], "invalid")
        self.assertIn("exit_code", execution["reason"])

    def test_empty_or_malformed_preconditions_are_unknown(self):
        for preconditions in ({}, dict(_valid_preconditions(), timeout="30")):
            with self.subTest(preconditions=preconditions):
                measurement = L.build_run_row(
                    _measurement_row(preconditions=preconditions), None, None
                )["measurement"]
                self.assertEqual(measurement["execution"]["validity"], "unknown")
                self.assertIn("preconditions", measurement["execution"]["reason"])

    def test_explicit_unsupported_is_skipped_and_process_failure_is_invalid(self):
        skipped = L.build_run_row(_measurement_row(
            passed=None, exit_code=None, error="unsupported: opencode cannot host kind=hook"
        ), None, None)["measurement"]["execution"]
        invalid = L.build_run_row(_measurement_row(exit_code=1), None, None)["measurement"]["execution"]
        self.assertEqual(skipped["validity"], "skipped")
        self.assertEqual(invalid["validity"], "invalid")
        self.assertIn("exit_code", invalid["reason"])
        identity = L.build_run_row(_measurement_row(
            passed=None, exit_code=None, error="unsupported: opencode cannot host kind=hook"
        ), None, None)["measurement"]["source_identity"]
        self.assertEqual(identity["log_observation"], "absent")

    def test_unsupported_row_with_process_or_plugin_failure_is_invalid(self):
        for overrides in ({"exit_code": -1}, {"plugin_errors": ["broken"]}):
            with self.subTest(overrides=overrides):
                execution = L.build_run_row(_measurement_row(
                    passed=None, error="unsupported: opencode cannot host kind=hook", **overrides
                ), None, None)["measurement"]["execution"]
                self.assertEqual(execution["validity"], "invalid")

    def test_log_digest_is_of_the_actual_log_bytes(self):
        raw = _log(_oc("text", {"text": "hi"}, 1)).encode()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "trial.log")
            with open(path, "wb") as fh:
                fh.write(raw)
            row = _measurement_row()
            key = L.run_key(row)
            aggregate = L.build_aggregate({key: row}, {key: path})
        identity = aggregate.runs[key]["measurement"]["source_identity"]
        self.assertTrue(identity["log_available"])
        self.assertEqual(identity["log_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(identity["log_observation"], "observed")

    def test_logless_replay_preserves_hosted_log_identity_and_fields(self):
        body = L.build_run_row(_measurement_row(), None, None)
        prior = dict(body, id="run-1", model_usage={"hosted": 1}, provenance={"tools": ["Read"]})
        prior["measurement"] = json.loads(json.dumps(body["measurement"]))
        identity = prior["measurement"]["source_identity"]
        identity.update(log_sha256="a" * 64, log_available=True, log_observation="observed")

        class PB:
            def update(self, *args):
                raise AssertionError("logless replay must be unchanged")

        _, counts = L._apply_runs(PB(), {L.run_key(body): body}, {L.run_key(body): prior}, False)
        self.assertEqual(counts, (0, 0, 1))
        self.assertEqual(prior["model_usage"], {"hosted": 1})
        self.assertEqual(prior["provenance"], {"tools": ["Read"]})

    def test_logless_replay_preserves_hosted_session_and_era_even_without_envelope(self):
        body = L.build_run_row(_measurement_row(), None, None)
        prior = {"id": "run-1", "session_id": "hosted-session", "era": "legacy"}
        updates = []

        class PB:
            def update(self, _coll, _id, update):
                updates.append(update)

        L._apply_runs(PB(), {L.run_key(body): body}, {L.run_key(body): prior}, False)
        self.assertEqual(updates[0]["session_id"], "hosted-session")
        self.assertEqual(updates[0]["era"], "legacy")

    def test_logless_replay_preserves_legacy_scalar_without_claiming_provenance(self):
        body = L.build_run_row(_measurement_row(num_turns=None), None, None)
        updates = []

        class PB:
            def update(self, _coll, _id, update):
                updates.append(update)

        L._apply_runs(PB(), {L.run_key(body): body},
                      {L.run_key(body): {"id": "run-1", "num_turns": 7}}, False)
        self.assertEqual(updates[0]["num_turns"], 7)
        measurement = updates[0]["measurement"]
        self.assertFalse(measurement["available"]["num_turns"])
        self.assertIsNone(measurement["provenance"]["num_turns"])

    def test_logless_replay_retains_prior_v1_log_rollup_availability(self):
        body = L.build_run_row(_measurement_row(duration_ms=None), None, None)
        prior_measurement = json.loads(json.dumps(body["measurement"]))
        prior_measurement["available"]["duration_ms"] = True
        prior_measurement["provenance"]["duration_ms"] = "log-rollup"
        prior_measurement["source_identity"].update(
            log_sha256="a" * 64, log_available=True, log_observation="observed"
        )
        updates = []

        class PB:
            def update(self, _coll, _id, update):
                updates.append(update)

        L._apply_runs(PB(), {L.run_key(body): body}, {L.run_key(body): {
            "id": "run-1", "duration_ms": 7, "measurement": prior_measurement,
        }}, False)
        self.assertEqual(updates[0]["duration_ms"], 7)
        self.assertTrue(updates[0]["measurement"]["available"]["duration_ms"])
        self.assertEqual(updates[0]["measurement"]["provenance"]["duration_ms"], "log-rollup")

    def test_empty_child_replay_does_not_write_existing_relations(self):
        class PB:
            def list_all(self, *args):
                return [{"id": "existing", "run": "run-a", "seq": 1}]

            def create(self, *args):
                raise AssertionError("no child creation")

            def update(self, *args):
                raise AssertionError("no child update")

        counts = L._apply_children(PB(), "run_events", [], {"a": "run-a"}, {},
                                   {"a": {"id": "run-a"}}, L._event_key,
                                   L.RUN_EVENT_FIELDS, L.EVENT_JSON, False)
        self.assertEqual(counts, (0, 0, 0))

    def test_parse_summary_separates_unreadable_reference_from_observed_log(self):
        row = L.build_run_row(_measurement_row(), None, "harness/runs/missing.log")
        aggregate = L.Aggregate({"run": row}, [], [], {}, {"legacy": 0, "post": 0, "na": 0})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            L._print_parse_summary(aggregate, [])
        self.assertIn("runs with log reference: 1/1", output.getvalue())
        self.assertIn("runs with observed log bytes: 0/1", output.getvalue())

    def test_missing_metric_uses_null_once_and_ignores_pb_default_afterward(self):
        body = L.build_run_row(_measurement_row(num_turns=None), None, None)
        existing = dict(body, id="run-1", num_turns=0)

        class PB:
            def create(self, *args):
                raise AssertionError("unexpected create")

            def update(self, *args):
                raise AssertionError("PB default must not cause update forever")

        _, counts = L._apply_runs(PB(), {L.run_key(body): body}, {L.run_key(body): existing}, False)
        self.assertEqual(counts, (0, 0, 1))

    def test_existing_sha_can_link_to_another_runs_event(self):
        sha_map = {"sha": "artifact-a"}
        body = L._child_body({"seq": 3, "_artifact_shas": ["sha"]}, "run-b", sha_map,
                             L.RUN_EVENT_FIELDS, L.EVENT_JSON)
        self.assertEqual(body["run"], "run-b")
        self.assertEqual(body["artifact"], "artifact-a")


class MirrorDedup(unittest.TestCase):
    def test_claude_byte_identical_stdout_becomes_marker(self):
        # Bash: tool_use_result.stdout duplicates the tool_result content -> dedup.
        tur = {"type": "text", "stdout": "listing\n", "stderr": ""}
        log = _log(_init(["Bash"]), _assistant_tool("c1", "Bash", {"command": "ls"}),
                   _user_result("c1", "listing\n", tur=tur))
        p = L.parse_claude_log(log)
        user_ev = next(e for e in p.events if e["event_type"] == "user")
        self.assertEqual(user_ev["payload"]["tool_use_result"]["stdout"], {"$deduped": "content"})
        self.assertEqual(user_ev["payload"]["tool_use_result"]["stderr"], "")

    def test_claude_non_identical_mirror_is_preserved(self):
        # Read: file.content (raw) differs from the line-numbered content -> NOT deduped.
        tur = {"type": "text", "file": {"content": "raw-body", "numLines": 1}}
        log = _log(_init(["Read"]), _assistant_tool("c1", "Read", {"file_path": "/x"}),
                   _user_result("c1", "1\traw-body", tur=tur))
        p = L.parse_claude_log(log)
        user_ev = next(e for e in p.events if e["event_type"] == "user")
        self.assertEqual(user_ev["payload"]["tool_use_result"]["file"]["content"], "raw-body")

    def test_opencode_filediff_patch_becomes_marker(self):
        diff = "@@ -1 +1 @@\n-a\n+b\n"
        meta = {"diff": diff, "filediff": {"patch": diff}, "truncated": False}
        log = _log(_oc("tool_use", _oc_tool("t1", "edit", {"filePath": "/a"}, "ok", 1, 2,
                                             metadata=meta), 1))
        p = L.parse_opencode_log(log)
        ev = p.events[0]
        self.assertEqual(ev["payload"]["part"]["state"]["metadata"]["filediff"]["patch"],
                         {"$deduped": "diff"})
        self.assertEqual(ev["payload"]["part"]["state"]["metadata"]["diff"], diff)  # canonical kept


class ImageExtraction(unittest.TestCase):
    def test_claude_image_excised_to_artifact_with_sha_marker(self):
        raw = b"\x89PNG-fake-bytes"
        sha = hashlib.sha256(raw).hexdigest()
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                "data": _b64(raw)}}]
        tur = {"type": "image", "file": {"base64": _b64(raw)}}
        log = _log(_init([f"t{i}" for i in range(25)]),
                   _assistant_tool("c1", "browser", {"action": "screenshot"}),
                   _user_result("c1", content, tur=tur))
        p = L.parse_claude_log(log)
        self.assertEqual(len(p.blobs), 2)                     # block + mirror, same sha
        self.assertTrue(all(b.sha256 == sha for b in p.blobs))
        self.assertEqual(p.blobs[0].kind, "screenshot")
        self.assertEqual(p.blobs[0].byte_size, len(raw))
        user_ev = next(e for e in p.events if e["event_type"] == "user")
        img = user_ev["payload"]["message"]["content"][0]["content"][0]["source"]["data"]
        self.assertEqual(img, {"$artifact": sha})
        self.assertEqual(user_ev["payload"]["tool_use_result"]["file"]["base64"],
                         {"$artifact": sha})
        self.assertIn(sha, user_ev["_artifact_shas"])

    def test_opencode_datauri_attachment_excised(self):
        raw = b"png-bytes-oc"
        sha = hashlib.sha256(raw).hexdigest()
        url = "data:image/png;base64," + _b64(raw)
        log = _log(_oc("tool_use", _oc_tool("t1", "browser", {}, "shot", 1, 2,
                                             attachments=[{"url": url}]), 1))
        p = L.parse_opencode_log(log)
        self.assertEqual(len(p.blobs), 1)
        self.assertEqual(p.blobs[0].sha256, sha)
        att = p.events[0]["payload"]["part"]["state"]["attachments"][0]["url"]
        self.assertEqual(att, {"$artifact": sha})


class OversizedWriteBoundary(unittest.TestCase):
    def test_exactly_threshold_is_kept_inline(self):
        body = "x" * L.ARTIFACT_TEXT_THRESHOLD                # 5000 -> not > threshold
        log = _log(_init([f"t{i}" for i in range(25)]),
                   _assistant_tool("c1", "Write", {"file_path": "/f", "content": body}))
        p = L.parse_claude_log(log)
        self.assertEqual(p.blobs, [])
        self.assertEqual(p.tool_calls[0]["input"]["content"], body)

    def test_over_threshold_is_externalized_as_write_content(self):
        body = "y" * (L.ARTIFACT_TEXT_THRESHOLD + 1)          # 5001 -> externalized
        sha = hashlib.sha256(body.encode()).hexdigest()
        log = _log(_init([f"t{i}" for i in range(25)]),
                   _assistant_tool("c1", "Write", {"file_path": "/f", "content": body}))
        p = L.parse_claude_log(log)
        self.assertEqual(len(p.blobs), 1)
        self.assertEqual(p.blobs[0].kind, "write_content")
        self.assertEqual(p.blobs[0].byte_size, len(body))
        self.assertEqual(p.tool_calls[0]["input"]["content"], {"$artifact": sha})

    def test_opencode_write_content_externalized(self):
        body = "z" * (L.ARTIFACT_TEXT_THRESHOLD + 5)
        log = _log(_oc("tool_use", _oc_tool("t1", "write", {"filePath": "/f", "content": body},
                                            "ok", 1, 2), 1))
        p = L.parse_opencode_log(log)
        self.assertEqual(len(p.blobs), 1)
        self.assertEqual(p.blobs[0].kind, "write_content")


class JsonFieldCoercion(unittest.TestCase):
    """PB coerces a JSON-string value in a `json` field to its parsed form on write; the
    loader must send the parsed form so a re-ingest diffs as unchanged (not update-forever)."""

    def test_coerce_parses_pretty_printed_json_string(self):
        out = '[\n  {\n    "content": "explore",\n    "status": "pending"\n  }\n]'
        self.assertEqual(L._coerce_json(out), [{"content": "explore", "status": "pending"}])

    def test_coerce_keeps_plain_text_output(self):
        blob = "./server.py\n./lib.py\n./Makefile"          # bash stdout, not JSON
        self.assertEqual(L._coerce_json(blob), blob)

    def test_coerce_first_byte_rule_like_pb(self):
        # PB attempts the parse only when the UNTRIMMED first byte can start a JSON
        # value. Live-corpus proof: '7853\n' (digit first) came back int, while
        # '     266' (space first) stayed a verbatim string.
        self.assertEqual(L._coerce_json("7853\n"), 7853)
        self.assertEqual(L._coerce_json("     266"), "     266")
        self.assertEqual(L._coerce_json("123"), 123)
        self.assertIs(L._coerce_json("true"), True)
        self.assertEqual(L._coerce_json("nope"), "nope")  # 'n' start but invalid JSON

    def test_coerce_passes_through_non_strings_and_empty(self):
        self.assertEqual(L._coerce_json({"a": 1}), {"a": 1})   # already parsed
        self.assertEqual(L._coerce_json([1, 2]), [1, 2])
        self.assertIsNone(L._coerce_json(None))
        self.assertEqual(L._coerce_json(""), "")                # empty -> existing None/"" logic
        self.assertEqual(L._coerce_json("   "), "   ")

    def test_child_body_coerces_opencode_json_string_output_to_list(self):
        out = '[\n  {\n    "content": "explore",\n    "status": "pending"\n  }\n]'
        log = _log(_oc("tool_use", _oc_tool("t1", "todowrite", {"todos": []}, out, 1, 2), 1))
        call = L.parse_opencode_log(log).tool_calls[0]
        self.assertEqual(call["output"], out)                  # raw string in the parse model
        body = L._child_body(call, "run-1", {}, L.TOOL_CALL_FIELDS, L.TOOLCALL_JSON)
        self.assertIsInstance(body["output"], list)            # coerced at DB-body build
        self.assertEqual(body["output"][0]["content"], "explore")
        self.assertIsInstance(body["input"], dict)             # already a dict, unchanged

    def test_child_body_keeps_plain_text_output_a_string(self):
        log = _log(_oc("tool_use", _oc_tool("t1", "bash", {"command": "ls"},
                                            "./server.py\n./lib.py", 1, 2), 1))
        call = L.parse_opencode_log(log).tool_calls[0]
        body = L._child_body(call, "run-1", {}, L.TOOL_CALL_FIELDS, L.TOOLCALL_JSON)
        self.assertEqual(body["output"], "./server.py\n./lib.py")


class Linkage(unittest.TestCase):
    def _touch(self, d: str, name: str) -> None:
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            fh.write("")

    def test_explicit_claim_excludes_post_log_from_legacy_prefix_match(self):
        with tempfile.TemporaryDirectory() as d:
            legacy = "claude-cand-case-with-0-20260721-150000.log"
            post = "claude-cand-case-with-0-20260721-164425.log"
            self._touch(d, legacy)
            self._touch(d, post)
            rows = {
                "skillfix|claude|m|cand|case|with|0": {
                    "harness": "claude", "candidate": "cand", "case": "case",
                    "config": "with", "trial": 0, "campaign": "skillfix",
                    "log_path": "harness/runs/" + post},
                "|claude|m|cand|case|with|0": {
                    "harness": "claude", "candidate": "cand", "case": "case",
                    "config": "with", "trial": 0, "campaign": ""},
            }
            links, warnings = L.link_logs(rows, d)
            self.assertEqual(links["skillfix|claude|m|cand|case|with|0"],
                             "harness/runs/" + post)
            # legacy row prefix-matches only the remaining (legacy) log, unambiguously
            self.assertEqual(os.path.basename(links["|claude|m|cand|case|with|0"]), legacy)
            self.assertEqual(warnings, [])

    def test_ambiguous_prefix_picks_earliest_and_warns(self):
        with tempfile.TemporaryDirectory() as d:
            early = "claude-c-k-with-0-20260721-150000.log"
            late = "claude-c-k-with-0-20260721-164425.log"
            self._touch(d, late)
            self._touch(d, early)
            rows = {"|claude|m|c|k|with|0": {"harness": "claude", "candidate": "c",
                    "case": "k", "config": "with", "trial": 0, "campaign": ""}}
            links, warnings = L.link_logs(rows, d)
            self.assertEqual(os.path.basename(links["|claude|m|c|k|with|0"]), early)
            self.assertEqual(len(warnings), 1)
            self.assertIn("ambiguous", warnings[0])

    def test_zero_match_warns_and_links_none(self):
        with tempfile.TemporaryDirectory() as d:
            rows = {"|claude|m|c|k|with|0": {"harness": "claude", "candidate": "c",
                    "case": "k", "config": "with", "trial": 0, "campaign": ""}}
            links, warnings = L.link_logs(rows, d)
            self.assertIsNone(links["|claude|m|c|k|with|0"])
            self.assertEqual(len(warnings), 1)
            self.assertIn("no log matches", warnings[0])


if __name__ == "__main__":
    unittest.main()
