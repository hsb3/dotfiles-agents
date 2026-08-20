#!/usr/bin/env python3
"""
subagent-telemetry — SubagentStop hook.

Appends one JSONL row per delegation (agent_id, agent_type, model,
ctx_tokens) to a local ledger so the plugin's own tier usage can be measured
offline (by a sibling analysis script, e.g. delegation_stats.py) — data that
is not otherwise derivable from the parent transcript alone, since a
subagent's type, model and token usage live only in the SUBAGENT's own
sidecar + transcript.

Purely observational: never blocks, never injects context, never prints
anything (telemetry is silent).

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

On-disk layout this hook reads (verified against real files under
~/.claude/projects, 2026-08):

  <projects>/<slug>/<session_id>.jsonl                            parent transcript
  <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
  <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

Sidecar keys observed: agentType (always), description, toolUseId,
spawnDepth, model (only when the dispatch overrode the model), parentAgentId,
worktreePath, worktreeBranch, name, isFork. There is NO token/usage data on
the sidecar, so ctx_tokens comes from the subagent's own transcript tail.

Contract (SubagentStop):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, agent_id,
    agent_type.
  - `transcript_path` is the PARENT session's transcript, not the subagent's
    (observed: two sibling delegations reported byte-identical usage). Reading
    model/ctx_tokens off it describes the strategist, not the delegation — so
    it is used only to locate the sibling `subagents/` directory.
  - A prospective row is DROPPED unless a matching sidecar exists and yields
    an agent_type. SubagentStop also fires for agents that never get a
    `subagents/` entry; writing those inflated the ledger ~10x.
  - stdout: NOTHING, ever (telemetry must not surface to the user/agent).
  - exit 0 always; fail-open on any internal error (missing/unreadable
    sidecar or transcript, malformed stdin, etc) by writing no row at all.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import sys
import traceback

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB — same window as context-watermark
# Stream name is the stem this ledger already had (`delegation.jsonl`), not
# the hook name: the rows are the delegation record, and keeping the stem
# keeps old and new rows queryable as one series.
LOG_STREAM = "delegation"
LOG_PATH_ENV = "SUBAGENT_TELEMETRY_LOG_PATH"
SUBAGENTS_DIRNAME = "subagents"
AGENT_FILE_PREFIX = "agent-"
SIDECAR_SUFFIX = ".meta.json"
TRANSCRIPT_SUFFIX = ".jsonl"


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


TAIL_BYTES = _env_int("SUBAGENT_TELEMETRY_TAIL_BYTES", TAIL_BYTES_DEFAULT)


def _debug_enabled():
    """Diagnostics are opt-in: an unconditional error row would inflate a
    ledger whose row count is the thing being measured."""
    return os.environ.get("SUBAGENT_TELEMETRY_DEBUG", "").strip().lower() not in (
        "", "0", "false", "no",
    )


# ---------------------------------------------------------------------------
# Locating the delegation's own records
# ---------------------------------------------------------------------------

def _subagents_dir(transcript_path):
    """Candidate `subagents/` directory for the payload's transcript path.

    Two shapes are handled: the parent transcript `<session_id>.jsonl`, whose
    subagents live in the sibling directory `<session_id>/subagents/`; and a
    path that already points inside a `subagents/` directory (a nested
    delegation), in which case that directory is the answer. Returns None when
    no candidate exists on disk.
    """
    if not transcript_path:
        return None
    parent = os.path.dirname(transcript_path)
    if os.path.basename(parent) == SUBAGENTS_DIRNAME and os.path.isdir(parent):
        return parent
    candidate = os.path.join(os.path.splitext(transcript_path)[0], SUBAGENTS_DIRNAME)
    return candidate if os.path.isdir(candidate) else None


def _agent_key(agent_id):
    """Bare agent id usable as a filename component, or None.

    Observed payloads carry the id unprefixed ("a31412cbc7cdb39e8") while the
    files carry an "agent-" prefix; a prefixed id is accepted too. basename()
    is what keeps a hostile or malformed id from escaping the subagents dir.
    """
    if not isinstance(agent_id, str):
        return None
    key = os.path.basename(agent_id.strip())
    if key.startswith(AGENT_FILE_PREFIX):
        key = key[len(AGENT_FILE_PREFIX):]
    if not key or key in (".", ".."):
        return None
    return key


def _read_sidecar(path):
    """Parsed sidecar dict, or None if absent/unreadable/malformed/not an object."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _clean_str(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


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
# Row construction
# ---------------------------------------------------------------------------

def _build_row(payload):
    """The ledger row for this SubagentStop, or None if it is not a delegation
    we can describe (in which case nothing is written at all).

    Every field is sourced from the delegation's own records: agent_type and
    any model override from its sidecar, model/ctx_tokens from its own
    transcript. The parent transcript contributes only the directory to look in.
    """
    key = _agent_key(payload.get("agent_id"))
    if key is None:
        return None

    subagents_dir = _subagents_dir(payload.get("transcript_path"))
    if subagents_dir is None:
        return None

    meta = _read_sidecar(
        os.path.join(subagents_dir, AGENT_FILE_PREFIX + key + SIDECAR_SUFFIX)
    )
    if meta is None:
        return None

    agent_type = _clean_str(meta.get("agentType")) or _clean_str(payload.get("agent_type"))
    if agent_type is None:
        # A row with no agent type is the defect this hook exists to fix.
        return None

    transcript_model, ctx_tokens = _read_model_and_ctx_tokens(
        os.path.join(subagents_dir, AGENT_FILE_PREFIX + key + TRANSCRIPT_SUFFIX)
    )
    # A sidecar `model` is the dispatch-time override — the delegation decision
    # itself — so it outranks whatever the transcript happens to name.
    model = _clean_str(meta.get("model")) or transcript_model

    return {
        "session_id": payload.get("session_id", "unknown"),
        "agent_id": key,
        "agent_type": agent_type,
        "model": model,
        "ctx_tokens": ctx_tokens,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        row = _build_row(payload)
        if row is not None:
            agentlog.append(
                LOG_STREAM, row,
                agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV,
            )

        # Telemetry is silent: no stdout, ever.
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        # Fail-open: never break the subagent-stop flow on our own error, and
        # never leave a partial row behind. Diagnostics only under an explicit
        # opt-in, so the ledger's row count stays equal to the delegation count.
        if _debug_enabled():
            try:
                agentlog.append(LOG_STREAM, {
                    "error": "{0}: {1}".format(type(e).__name__, e),
                    "traceback": traceback.format_exc(limit=3),
                }, agentlog.resolve_project(), LOG_PATH_ENV)
            except Exception:
                pass
        sys.exit(0)


if __name__ == "__main__":
    main()
