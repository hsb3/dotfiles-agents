"""Validated v2 Codex usage deltas from native cumulative token counters."""
import hashlib
import json
import os
import socket
import subprocess
from datetime import datetime
from pathlib import Path

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
    except (AttributeError, TypeError, ValueError):
        return None


def _provenance(payload):
    package = Path(__file__).resolve().parents[2]
    name = version = None
    for manifest in (package / ".claude-plugin/plugin.json", package / ".codex-plugin/plugin.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            name, version = data.get("name"), data.get("version")
            break
        except (OSError, ValueError):
            pass
    profile = payload.get("profile_path")
    try:
        raw = Path(profile).read_bytes()
        profile_hash = hashlib.sha256(raw).hexdigest()
    except (OSError, TypeError):
        profile, profile_hash = None, None
    return {"package_path": str(package), "package_name": name, "package_version": version,
            "profile_path": profile, "profile_hash": profile_hash}


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
        **payload["_provenance"],
        "host": host, "source_repo": payload.get("repo"),
        "effective_cwd": payload.get("cwd"), "started_at": meta.get("timestamp"),
        "timing": {"lifetime_ms": _duration(meta.get("timestamp"), timestamp),
                   "active_ms": None, "tool_ms": None, "wait_ms": None},
        "tokens": delta, "cumulative_tokens": cumulative,
    }


def events(path, payload):
    """Return appendable observations. Any uncertain ownership is unknown."""
    payload = dict(payload)
    payload["repo"] = payload.get("repo") or _git_root(payload.get("cwd"))
    payload["_provenance"] = _provenance(payload)
    if not path or not os.path.isfile(path):
        return [_event("error", 0, payload, {}, None, None)]
    expected = payload.get("agent_id") or payload.get("session_id")
    meta, model, effort, prior, segment = {}, None, None, None, 0
    ownership_bad, result = False, []
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            lines = list(stream)
        objects = []
        for line in lines:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                objects.append(item)
        identities = [
            item["payload"].get("id") for item in objects
            if item.get("type") == "session_meta" and isinstance(item.get("payload"), dict)
            and isinstance(item["payload"].get("id"), str) and item["payload"]["id"]
        ]
        ownership_bad = len(set(identities)) != 1 or identities[0] != expected
        canonical = next((
            item["payload"] for item in objects
            if item.get("type") == "session_meta" and isinstance(item.get("payload"), dict)
            and item["payload"].get("id") == expected
        ), {})
        meta = canonical
        ownership_bad = ownership_bad or any(
            item.get("payload", {}).get("forked_from_id") for item in objects
            if item.get("type") == "session_meta" and isinstance(item.get("payload"), dict))
        for occurrence, line in enumerate(lines):
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
                    meta = body
                    if body.get("forked_from_id"):
                        ownership_bad = True
                elif item.get("type") == "turn_context" and isinstance(body, dict):
                    model = body.get("model") if isinstance(body.get("model"), str) else model
                    effort = body.get("effort") if isinstance(body.get("effort"), str) else effort
                elif item.get("type") == "event_msg" and isinstance(body, dict) and body.get("type") == "token_count":
                    info = body.get("info")
                    current = _counters(info.get("total_token_usage") if isinstance(info, dict) else None)
                    timestamp = item.get("timestamp")
                    before_start = _duration(meta.get("timestamp"), timestamp)
                    if ownership_bad or (before_start is not None and before_start < 0):
                        result.append(_event("inherited-baseline-unknown", occurrence, payload, meta, model, effort))
                        if current is not None:
                            prior = current
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
                                                 current, segment, timestamp))
                            prior = current
    except OSError:
        return [_event("error", 0, payload, meta, model, effort)]
    if result:
        return result
    return [_event("pending" if meta else "missing", 0, payload, meta, model, effort)]
