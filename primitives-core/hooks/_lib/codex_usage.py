"""Codex v2 usage emits a delta for each cumulative runtime counter."""
import hashlib
import json
import os
import socket
from datetime import datetime

SCHEMA, VERSION = "codex-usage", 2
KEYS = {"input": "input_tokens", "cached_input": "cached_input_tokens",
        "output": "output_tokens", "reasoning": "reasoning_output_tokens", "total": "total_tokens"}


def _tokens(values):
    if not isinstance(values, dict):
        return None
    result = {name: values.get(key) for name, key in KEYS.items()}
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in result.values()):
        return None
    return result if result["cached_input"] <= result["input"] and result["reasoning"] <= result["output"] else None


def _event(state, occurrence, payload, meta, model, effort, tokens=None, cumulative=None, segment=0, timestamp=None):
    native = meta.get("id") or payload.get("agent_id") or payload.get("session_id")
    host = socket.gethostname()
    raw = json.dumps([host, native, occurrence, model, cumulative or tokens], sort_keys=True).encode()
    try:
        lifetime = int((datetime.fromisoformat(timestamp.replace("Z", "+00:00")) -
                        datetime.fromisoformat(meta["timestamp"].replace("Z", "+00:00"))).total_seconds() * 1000)
    except (AttributeError, KeyError, ValueError):
        lifetime = None
    child = meta.get("thread_source") == "subagent" or payload.get("agent_id")
    return {"schema": SCHEMA, "schema_version": VERSION, "kind": "delta", "counter_state": state,
            "segment": segment, "observation_id": hashlib.sha256(raw).hexdigest(),
            "lifecycle_id": meta.get("session_id") or payload.get("session_id"), "native_id": native,
            "parent_id": meta.get("parent_thread_id") if child else None,
            "role": meta.get("agent_role") if child else None, "model": model, "effort": effort,
            "requested_model": payload.get("requested_model"), "requested_tier": payload.get("requested_tier"),
            "package": os.environ.get("ATELIER_PACKAGE_ID"), "profile": os.environ.get("ATELIER_PROFILE"),
            "host": host, "source_repo": payload.get("repo") or payload.get("source") or payload.get("original_cwd"),
            "effective_cwd": payload.get("cwd"), "started_at": meta.get("timestamp"),
            "timing": {"lifetime_ms": lifetime, "active_ms": None, "tool_ms": None, "wait_ms": None},
            "tokens": tokens, "cumulative_tokens": cumulative}


def events(path, payload):
    """Return replayable v2 events. Counters are deltas, never snapshot sums."""
    if not path or not os.path.isfile(path):
        return [_event("error", 0, payload, {}, None, None)]
    meta, model, effort, prior, segment, result = {}, None, None, None, 0, []
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            for occurrence, line in enumerate(stream):
                try:
                    row = json.loads(line)
                except ValueError:
                    result.append(_event("malformed-json", occurrence, payload, meta, model, effort))
                    continue
                body = row.get("payload") if isinstance(row, dict) else None
                if row.get("type") == "session_meta" and isinstance(body, dict):
                    meta = body
                elif row.get("type") == "turn_context" and isinstance(body, dict):
                    model = body.get("model") if isinstance(body.get("model"), str) else model
                    effort = body.get("effort") if isinstance(body.get("effort"), str) else effort
                elif row.get("type") == "event_msg" and isinstance(body, dict) and body.get("type") == "token_count":
                    info = body.get("info")
                    current = _tokens(info.get("total_token_usage") if isinstance(info, dict) else None)
                    if current is None:
                        result.append(_event("malformed", occurrence, payload, meta, model, effort))
                    elif meta.get("forked_from_id"):
                        result.append(_event("inherited-baseline-unknown", occurrence, payload, meta, model, effort))
                        meta.pop("forked_from_id", None); prior = current
                    else:
                        if prior and current["total"] < prior["total"]:
                            segment += 1
                            result.append(_event("reset", occurrence, payload, meta, model, effort, segment=segment))
                            prior = None
                        delta = current if prior is None else {key: current[key] - prior[key] for key in current}
                        result.append(_event("observed", occurrence, payload, meta, model, effort, delta, current, segment, row.get("timestamp")))
                        prior = current
    except OSError:
        return [_event("error", 0, payload, meta, model, effort)]
    return result or [_event("missing", 0, payload, meta, model, effort)]
