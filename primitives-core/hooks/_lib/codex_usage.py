"""Versioned, cumulative Codex usage observations."""
import hashlib
import json
import os
import socket

SCHEMA = "codex-usage"
VERSION = 2
TOKEN_KEYS = {"input": ("input_tokens", "input"), "cached_input": ("cached_input_tokens", "cached_input"), "output": ("output_tokens", "output"), "reasoning": ("reasoning_tokens", "reasoning"), "total": ("total_tokens", "total")}


def _integer(values, names):
    for name in names:
        value = values.get(name)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    return None


def _tokens(values):
    if not isinstance(values, dict):
        return None
    result = {name: _integer(values, names) for name, names in TOKEN_KEYS.items()}
    if any(value is None for value in result.values()):
        return None
    if result["cached_input"] > result["input"] or result["reasoning"] > result["output"]:
        return None
    return result


def _records(path):
    future, result = False, []
    if not path or not os.path.isfile(path):
        return result, future
    with open(path, encoding="utf-8", errors="replace") as source:
        for line in source:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            if isinstance(row.get("v"), int) and row["v"] > VERSION:
                future = True
                continue
            result.append(row)
    return result, future


def _identity(payload, subject, snapshot):
    body = json.dumps([payload.get("session_id"), subject, snapshot], sort_keys=True,
                      separators=(",", ":"), default=str).encode()
    return hashlib.sha256(body).hexdigest()


def observe(path, payload, subject):
    """Return one explicit v2 cumulative observation; never sum snapshots."""
    rows, future = _records(path)
    meta, model, latest, previous, last_total, saw_counter = {}, None, None, None, None, False
    for row in rows:
        body = row.get("payload")
        if row.get("type") == "session_meta" and isinstance(body, dict):
            meta = body
        elif row.get("type") == "turn_context" and isinstance(body, dict):
            model = body.get("model") if isinstance(body.get("model"), str) else model
        elif row.get("type") == "event_msg" and isinstance(body, dict) and body.get("type") == "token_count":
            saw_counter = True
            info = body.get("info")
            values = info.get("total_token_usage") if isinstance(info, dict) else None
            raw_total = _integer(values, TOKEN_KEYS["total"]) if isinstance(values, dict) else None
            if raw_total is not None and last_total is not None and raw_total < last_total:
                previous, latest = {"total": last_total}, None
            if raw_total is not None:
                last_total = raw_total
            current = _tokens(values)
            if current is not None:
                previous, latest = latest, current
    owner = meta.get("id") if isinstance(meta.get("id"), str) else None
    expected = payload.get("agent_id") or payload.get("session_id")
    state = "observed"
    if future:
        state, latest = "unsupported-future-schema", None
    elif previous and latest is None:
        state = "reset"
    elif latest is None:
        state = "malformed" if saw_counter else "missing"
    elif previous and latest["total"] < previous["total"]:
        state, latest = "reset", None
    elif owner and expected and owner != expected:
        state, latest = "inherited-history-unknown", None
    source_repo = payload.get("original_cwd") or payload.get("source_repo")
    return {
        "schema": SCHEMA, "schema_version": VERSION, "kind": "cumulative",
        "counter_state": state, "observation_id": _identity(payload, subject, latest),
        "lifecycle_id": payload.get("session_id"), "native_id": payload.get("agent_id"),
        "parent_id": payload.get("parent_agent_id") or (payload.get("session_id") if payload.get("agent_id") else None),
        "role": payload.get("agent_type"), "model": model,
        "requested_model": payload.get("requested_model"), "requested_tier": payload.get("requested_tier"),
        "effort": payload.get("reasoning_effort"), "package": os.environ.get("ATELIER_PACKAGE_ID"),
        "profile": os.environ.get("ATELIER_PROFILE"), "host": socket.gethostname(),
        "source_repo": source_repo, "effective_cwd": payload.get("cwd"),
        "started_at": meta.get("timestamp"), "timing": {"lifetime_ms": None, "active_ms": None, "tool_ms": None, "wait_ms": None},
        "tokens": latest,
    }
