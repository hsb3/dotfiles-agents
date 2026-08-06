#!/usr/bin/env python3
"""
subagent-telemetry — SubagentStop hook.

Appends one JSONL row per delegation (agent_id, agent_type, model,
ctx_tokens) to a local ledger so the plugin's own tier usage can be measured
offline (by a sibling analysis script, e.g. delegation_stats.py) — data that
is not otherwise derivable from the parent transcript alone, since a
subagent's model and token usage live only in the SUBAGENT's own transcript.

Purely observational: never blocks, never injects context, never prints
anything on success (telemetry is silent).

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SubagentStop):
  - stdin JSON fields consumed: session_id, transcript_path (the SUBAGENT's
    own transcript), cwd, hook_event_name, agent_id, agent_type,
    last_assistant_message, permission_mode.
  - There is NO model field in the SubagentStop payload itself — model and
    token usage are read from the subagent's transcript tail (reusing
    context-watermark/hook.py's tail-read + usage-parsing approach), where
    the model lives on the same assistant message as the usage block
    (typically `message.model`).
  - stdout: NOTHING, ever (telemetry must not surface to the user/agent).
  - exit 0 always; fail-open on any internal error (missing/unreadable
    transcript, malformed stdin, etc).

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB — same window as context-watermark
LOG_FILENAME_DEFAULT = "delegation.jsonl"


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


TAIL_BYTES = _env_int("SUBAGENT_TELEMETRY_TAIL_BYTES", TAIL_BYTES_DEFAULT)


def _resolve_log_path(cwd):
    """SUBAGENT_TELEMETRY_LOG_PATH override, else <project-root>/logs/delegation.jsonl.

    The project root is CLAUDE_PROJECT_DIR (set by Claude Code for hook
    commands), so the hook stays portable across any project that installs
    the atelier plugin. The payload cwd is a last resort only — anchoring
    on cwd scatters stray logs/ dirs into whatever subdirectory an agent
    happens to be running in.
    """
    override = os.environ.get("SUBAGENT_TELEMETRY_LOG_PATH")
    if override:
        return override
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    return os.path.join(base, "logs", LOG_FILENAME_DEFAULT)


# ---------------------------------------------------------------------------
# Logging (best-effort; must never raise into the caller)
# ---------------------------------------------------------------------------

def _append_row(log_path, record):
    try:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        # Logging must never break the hook.
        pass


# ---------------------------------------------------------------------------
# Transcript parsing — same tail-read approach as context-watermark/hook.py,
# extended to also pull the model off the same assistant message.
# ---------------------------------------------------------------------------

def _read_tail(path, tail_bytes):
    """Read only the last `tail_bytes` of the file. Returns a str (may start
    mid-line; caller splits on newlines and discards the first partial line
    unless it's the only line)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > tail_bytes:
            f.seek(size - tail_bytes)
        else:
            f.seek(0)
        data = f.read()
    if size > tail_bytes:
        nl = data.find(b"\n")
        if nl != -1:
            data = data[nl + 1 :]
    return data.decode("utf-8", errors="replace")


def _find_last_assistant_model_and_usage(tail_text):
    """Scan tail lines (newest last) for the last assistant message that has
    a .message.usage block. Returns (model, usage) — either may be None.

    Transcript lines are JSONL; each line is a standalone JSON object. We
    walk from the end so the first usable line we find is the most recent.
    """
    lines = [ln for ln in tail_text.split("\n") if ln.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") != "assistant":
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if isinstance(usage, dict):
            model = message.get("model")
            return model, usage
    return None, None


def _context_tokens_from_usage(usage):
    """ctx = input_tokens + cache_creation_input_tokens + cache_read_input_tokens.

    Any missing field is treated as 0 (defensive: same assumption as
    context-watermark/hook.py — the three fields are not guaranteed present).
    """
    def _num(x):
        return x if isinstance(x, (int, float)) else 0

    return (
        _num(usage.get("input_tokens"))
        + _num(usage.get("cache_creation_input_tokens"))
        + _num(usage.get("cache_read_input_tokens"))
    )


def _read_model_and_ctx_tokens(transcript_path):
    """Best-effort: returns (model, ctx_tokens), either possibly None. Never
    raises — any failure (missing file, unreadable, malformed, no usage
    found) yields (None, None)."""
    try:
        if not transcript_path or not os.path.isfile(transcript_path):
            return None, None
        tail_text = _read_tail(transcript_path, TAIL_BYTES)
        model, usage = _find_last_assistant_model_and_usage(tail_text)
        if usage is None:
            return model, None
        return model, _context_tokens_from_usage(usage)
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)

        session_id = payload.get("session_id", "unknown")
        cwd = payload.get("cwd") or os.getcwd()
        agent_id = payload.get("agent_id")
        agent_type = payload.get("agent_type")
        transcript_path = payload.get("transcript_path")

        model, ctx_tokens = _read_model_and_ctx_tokens(transcript_path)

        log_path = _resolve_log_path(cwd)
        _append_row(log_path, {
            "session_id": session_id,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "model": model,
            "ctx_tokens": ctx_tokens,
        })

        # Telemetry is silent: no stdout, ever.
        sys.exit(0)

    except Exception as e:
        # Fail-open: never break the subagent-stop flow on our own error.
        try:
            log_path = _resolve_log_path(None)
            _append_row(log_path, {
                "session_id": None,
                "agent_id": None,
                "agent_type": None,
                "model": None,
                "ctx_tokens": None,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            })
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
