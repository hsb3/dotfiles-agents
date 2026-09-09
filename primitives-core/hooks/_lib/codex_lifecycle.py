"""Codex rollout measurements and the shared worker identity boundary."""

import json
import os


class PendingMeasurement(ValueError):
    """The runtime has not emitted its first token_count yet."""


def enabled():
    return os.environ.get("ATELIER_HARNESS") == "codex"


def prepare(payload):
    """Inactive projects are silent; mapped workers keep their owned checkout."""
    if not enabled():
        return payload
    import codex_workers
    if not codex_workers.active(payload):
        return None
    return codex_workers.effective_payload(payload)


def diagnostic(message):
    print(json.dumps({"systemMessage": "atelier: could not measure Codex lifecycle: " + str(message)}))


def entries(path):
    if not path or not os.path.isfile(path):
        raise ValueError("rollout transcript missing")
    if os.path.getsize(path) > 64 * 1024 * 1024:
        raise ValueError("rollout exceeds 64 MiB measurement limit")
    with open(path, encoding="utf-8", errors="replace") as source:
        for line in source:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                yield item


def measure(path):
    """Use runtime occupancy and effective window, including post-compact estimates.

    Cached input is already part of input_tokens. total_token_usage is cumulative
    across requests, so neither is added to last_token_usage.total_tokens.
    """
    model = None
    info = None
    started = None
    saw_measurement_info = False
    for item in entries(path):
        body = item.get("payload") or {}
        if item.get("type") == "session_meta":
            timestamp = body.get("timestamp") or item.get("timestamp")
            if isinstance(timestamp, str) and timestamp:
                started = timestamp
        elif item.get("type") == "turn_context":
            model = body.get("model") or model
        elif item.get("type") == "event_msg" and body.get("type") == "token_count":
            candidate = body.get("info")
            if candidate is not None:
                saw_measurement_info = True
                info = candidate if isinstance(candidate, dict) else None
    if not saw_measurement_info and started is not None:
        raise PendingMeasurement("runtime token_count initialization pending")
    usage = (info or {}).get("last_token_usage") or {}
    tokens = usage.get("total_tokens")
    window = (info or {}).get("model_context_window")
    if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
        raise ValueError("no runtime last_token_usage.total_tokens")
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        raise ValueError("no runtime model_context_window")
    return {"ctx_tokens": tokens, "window": window, "model": model,
            "started_at": started}
