#!/usr/bin/env python3
"""
context-watermark — UserPromptSubmit hook.

Reads the session transcript's tail, computes an approximate current-context
token count from the last assistant usage block, and injects a reminder into
Claude's context when the count crosses SOFT/HARD watermarks. Anti-nag state
is persisted per session so the reminder does not fire on every prompt.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (UserPromptSubmit):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, prompt
  - stdout JSON: {"additionalContext": "...", "systemMessage": "..."}  (exit 0)
    additionalContext is injected into the model's context; systemMessage is
    shown to the USER in the TUI so a fire is visible/verifiable.
  - exit 0 always (this hook must never block a prompt) — even on internal
    error, we exit 0 with no JSON so the prompt flow is unaffected.

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

SOFT_DEFAULT = 70_000
HARD_DEFAULT = 100_000
TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB
REFIRE_EVERY_DEFAULT = 5  # prompts, while still above a tier
STATE_DIR_DEFAULT = "/tmp/context-watermark"
LOG_STREAM = "context-watermark"
LOG_PATH_ENV = "CONTEXT_WATERMARK_LOG_PATH"


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_path(name, default):
    v = os.environ.get(name)
    return v if v else default


SOFT = _env_int("CONTEXT_WATERMARK_SOFT", SOFT_DEFAULT)
HARD = _env_int("CONTEXT_WATERMARK_HARD", HARD_DEFAULT)
TAIL_BYTES = _env_int("CONTEXT_WATERMARK_TAIL_BYTES", TAIL_BYTES_DEFAULT)
REFIRE_EVERY = _env_int("CONTEXT_WATERMARK_REFIRE_EVERY", REFIRE_EVERY_DEFAULT)
STATE_DIR = _env_path("CONTEXT_WATERMARK_STATE_DIR", STATE_DIR_DEFAULT)


# ---------------------------------------------------------------------------
# Transcript parsing
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
    # Discard a possibly-truncated first line (unless we read from offset 0).
    if size > tail_bytes:
        nl = data.find(b"\n")
        if nl != -1:
            data = data[nl + 1 :]
    return data.decode("utf-8", errors="replace")


def _find_last_assistant_usage(tail_text):
    """Scan tail lines (newest last) for the last assistant message that has
    a .message.usage block. Returns the usage dict or None.

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
            return usage
    return None


def _context_tokens_from_usage(usage):
    """ctx = input_tokens + cache_creation_input_tokens + cache_read_input_tokens.

    Any missing field is treated as 0 (defensive: docs do not guarantee all
    three fields are always present — see spec's unverified-assumptions
    section).
    """
    def _num(x):
        return x if isinstance(x, (int, float)) else 0

    return (
        _num(usage.get("input_tokens"))
        + _num(usage.get("cache_creation_input_tokens"))
        + _num(usage.get("cache_read_input_tokens"))
    )


# ---------------------------------------------------------------------------
# Anti-nag state
# ---------------------------------------------------------------------------

def _state_path(session_id):
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "unknown"
    return os.path.join(STATE_DIR, f"{safe}.json")


def _load_state(session_id):
    try:
        with open(_state_path(session_id)) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(session_id, state):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_state_path(session_id), "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def _tier_for(ctx_tokens):
    if ctx_tokens >= HARD:
        return "hard"
    if ctx_tokens >= SOFT:
        return "soft"
    return "none"


def _should_fire(state, tier):
    """Anti-nag: fire at most once per tier crossing, then at most every
    REFIRE_EVERY prompts while still at/above that tier.

    `prompts_since_fire` counts prompts seen at this tier since the last
    fire, NOT counting the fire itself. A tier crossing always fires
    immediately (count resets to 0). On a repeat prompt at the same tier,
    the count is incremented first (by the caller) and this function is
    given the post-increment value, so REFIRE_EVERY=3 fires on the 3rd
    subsequent prompt.
    """
    last_tier = state.get("last_tier", "none")
    prompts_since_fire = state.get("prompts_since_fire", 0)

    if tier != last_tier:
        # Freshly crossed into (or out of / re-into) a tier.
        return True
    if prompts_since_fire >= REFIRE_EVERY:
        return True
    return False


MESSAGES = {
    "soft": (
        "Session context is ~{k}k tokens, past the ~{soft}k soft watermark, "
        "where cost and performance measurably degrade. At the next natural task boundary, run /handoff to "
        "externalize state, then recommend the user /clear (preferred) or "
        "/compact."
    ),
    "hard": (
        "Session context is ~{k}k tokens, well past the ~{hard}k hard watermark "
        "and approaching heavy degradation territory. Recommend wrapping up the "
        "current step now: run /handoff, then tell the user to /clear "
        "(preferred) or /compact before continuing."
    ),
}


def _format_message(tier, ctx_tokens):
    k = round(ctx_tokens / 1000)
    return MESSAGES[tier].format(
        k=k, soft=round(SOFT / 1000), hard=round(HARD / 1000)
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    raw_stdin = ""
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)

        session_id = payload.get("session_id", "unknown")
        transcript_path = payload.get("transcript_path")
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(payload.get("cwd")),
        )

        if not transcript_path or not os.path.isfile(transcript_path):
            log({
                "session_id": session_id,
                "ctx_tokens": None,
                "tier": "none",
                "fired": False,
                "error": "transcript_path missing or not a file",
            })
            sys.exit(0)

        tail_text = _read_tail(transcript_path, TAIL_BYTES)
        usage = _find_last_assistant_usage(tail_text)

        if usage is None:
            log({
                "session_id": session_id,
                "ctx_tokens": None,
                "tier": "none",
                "fired": False,
                "error": "no assistant usage found in tail window",
            })
            sys.exit(0)

        ctx_tokens = _context_tokens_from_usage(usage)
        tier = _tier_for(ctx_tokens)

        state = _load_state(session_id)
        fired = False

        if tier == "none":
            # Reset anti-nag state once back under the soft line.
            _save_state(session_id, {"last_tier": "none", "prompts_since_fire": 0})
        else:
            last_tier = state.get("last_tier", "none")
            if tier != last_tier:
                # Fresh tier crossing: always fires, counter resets.
                check_state = state
            else:
                # Same tier as last time: bump the counter BEFORE deciding,
                # so REFIRE_EVERY=N fires on the Nth subsequent prompt.
                bumped = state.get("prompts_since_fire", 0) + 1
                check_state = {**state, "prompts_since_fire": bumped}

            if _should_fire(check_state, tier):
                fired = True
                message = _format_message(tier, ctx_tokens)
                # UserPromptSubmit uses a TOP-LEVEL additionalContext field
                # (not nested under hookSpecificOutput) — confirmed against
                # both https://code.claude.com/docs/en/hooks and
                # https://code.claude.com/docs/en/hooks-guide.
                # systemMessage makes the nudge VISIBLE to the user in the
                # TUI (evidence the hook fired); additionalContext is only
                # ever seen by the model.
                out = {
                    "additionalContext": message,
                    "systemMessage": (
                        f"atelier: context ~{round(ctx_tokens / 1000)}k tokens — "
                        f"{tier} watermark crossed; nudging /handoff + /clear."
                    ),
                }
                print(json.dumps(out))
                _save_state(session_id, {"last_tier": tier, "prompts_since_fire": 0})
            else:
                _save_state(session_id, {
                    "last_tier": tier,
                    "prompts_since_fire": check_state.get("prompts_since_fire", 0),
                })

        log({
            "session_id": session_id,
            "ctx_tokens": ctx_tokens,
            "tier": tier,
            "fired": fired,
        })

        sys.exit(0)

    except Exception as e:
        # Fail-open: never break prompt flow. Log what we can.
        try:
            agentlog.append(LOG_STREAM, {
                "session_id": None,
                "ctx_tokens": None,
                "tier": "none",
                "fired": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            }, override_env=LOG_PATH_ENV)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
