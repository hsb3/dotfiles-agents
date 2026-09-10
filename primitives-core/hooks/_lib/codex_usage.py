"""Validated v2 Codex usage deltas from native cumulative token counters."""
import hashlib
import json
import os
import socket
import subprocess
from datetime import datetime

SCHEMA, VERSION = "codex-usage", 2
FIELDS = {"input": "input_tokens", "cached_input": "cached_input_tokens",
          "output": "output_tokens", "reasoning": "reasoning_output_tokens",
          "total": "total_tokens"}


def _counters(values):
    if not isinstance(values, dict):
        return None
    counters = {name: values.get(key) for name, key in FIELDS.items()}
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
           for value in counters.values()):
        return None
    if counters["cached_input"] > counters["input"] or counters["reasoning"] > counters["output"]:
        return None
    if counters["total"] != counters["input"] + counters["output"]:
        return None
    return counters


def _git_root(cwd):
    if not isinstance(cwd, str) or not cwd:
        return None
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        run = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             env=env, capture_output=True, text=True, timeout=3)
        return run.stdout.strip() if run.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _duration(started, timestamp):
    try:
        return int((datetime.fromisoformat(timestamp.replace("Z", "+00:00")) -
                    datetime.fromisoformat(started.replace("Z", "+00:00"))).total_seconds() * 1000)
    except (AttributeError, ValueError):
        return None


def _id(host, native, occurrence, state, segment, model, effort, delta, cumulative):
    text = json.dumps([host, native, occurrence, state, segment, model, effort, delta, cumulative],
                      sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(text).hexdigest()


def _event(state, occurrence, payload, meta, model, effort, delta=None, cumulative=None,
           segment=0, timestamp=None):
    native = meta.get("id") or payload.get("agent_id") or payload.get("session_id")
    host = socket.gethostname()
    child = bool(payload.get("agent_id"))
    return {
        "schema": SCHEMA, "schema_version": VERSION, "kind": "delta",
        "counter_state": state, "segment": segment,
        "observation_id": _id(host, native, occurrence, state, segment, model, effort, delta, cumulative),
        "lifecycle_id": meta.get("session_id") or payload.get("session_id"),
        "native_id": native, "parent_id": meta.get("parent_thread_id") if child else None,
        "role": meta.get("agent_role") or (payload.get("agent_type") if child else None),
        "model": model, "effort": effort,
        "requested_model": payload.get("requested_model"),
        "requested_tier": payload.get("requested_tier"),
        "package_path": None, "package_name": None, "package_version": None,
        "profile_path": None, "profile_hash": None,
        "host": host, "source_repo": payload.get("repo") or _git_root(payload.get("cwd")),
        "effective_cwd": payload.get("cwd"), "started_at": meta.get("timestamp"),
        "timing": {"lifetime_ms": _duration(meta.get("timestamp"), timestamp),
                   "active_ms": None, "tool_ms": None, "wait_ms": None},
        "tokens": delta, "cumulative_tokens": cumulative,
    }


def events(path, payload):
    """Return appendable observations. Any uncertain ownership is unknown."""
    if not path or not os.path.isfile(path):
        return [_event("error", 0, payload, {}, None, None)]
    expected = payload.get("agent_id") or payload.get("session_id")
    meta, model, effort, prior, segment = {}, None, None, None, 0
    ownership_bad, saw_counter, result = False, False, []
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            for occurrence, line in enumerate(stream):
                try:
                    item = json.loads(line)
                except ValueError:
                    result.append(_event("malformed-json", occurrence, payload, meta, model, effort))
                    continue
                if not isinstance(item, dict):
                    result.append(_event("malformed-json", occurrence, payload, meta, model, effort))
                    continue
                if (isinstance(item.get("v"), int) and item["v"] > VERSION) or (
                        isinstance(item.get("schema_version"), int) and item["schema_version"] > VERSION):
                    result.append(_event("unsupported-future-schema", occurrence, payload, meta, model, effort))
                    continue
                body = item.get("payload")
                if item.get("type") == "session_meta" and isinstance(body, dict):
                    if meta and body.get("id") != meta.get("id"):
                        ownership_bad = True
                    meta = body
                    if body.get("id") and body["id"] != expected:
                        ownership_bad = True
                    if body.get("forked_from_id"):
                        ownership_bad = True
                elif item.get("type") == "turn_context" and isinstance(body, dict):
                    model = body.get("model") if isinstance(body.get("model"), str) else model
                    effort = body.get("effort") if isinstance(body.get("effort"), str) else effort
                elif item.get("type") == "event_msg" and isinstance(body, dict) and body.get("type") == "token_count":
                    saw_counter = True
                    info = body.get("info")
                    current = _counters(info.get("total_token_usage") if isinstance(info, dict) else None)
                    if ownership_bad:
                        result.append(_event("inherited-baseline-unknown", occurrence, payload, meta, model, effort))
                    elif current is None:
                        result.append(_event("malformed-delta", occurrence, payload, meta, model, effort))
                    else:
                        decreased = prior and any(current[key] < prior[key] for key in current)
                        if decreased:
                            segment += 1
                            result.append(_event("reset", occurrence, payload, meta, model, effort, segment=segment))
                            prior = None
                        delta = current if prior is None else {key: current[key] - prior[key] for key in current}
                        if _counters({FIELDS[key]: delta[key] for key in delta}) is None:
                            result.append(_event("malformed-delta", occurrence, payload, meta, model, effort,
                                                 segment=segment))
                            prior = current
                        else:
                            result.append(_event("observed", occurrence, payload, meta, model, effort, delta,
                                                 current, segment, item.get("timestamp")))
                            prior = current
    except OSError:
        return [_event("error", 0, payload, meta, model, effort)]
    if result:
        return result
    return [_event("pending" if meta else "missing", 0, payload, meta, model, effort)]
