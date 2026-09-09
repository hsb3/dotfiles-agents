#!/usr/bin/env python3
"""
context-watermark — UserPromptSubmit (session) + PostToolUse (subagent) hook.

Reads the transcript tail, computes an approximate current-context token count
from the last assistant usage block, and injects a reminder when the count
crosses a watermark. The watermarks scale with the lead model's context window
as a CAP, never a lift, and with a session-level complexity factor; both are
overridable. Anti-nag state is persisted per session (and per worker) so the
reminder does not fire on every event.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract:
  - UserPromptSubmit — stdin: session_id, transcript_path, cwd, prompt;
    stdout: {"additionalContext": ..., "systemMessage": ...} (TOP-LEVEL).
  - PostToolUse — fires in both the parent and a worker; only a worker's
    payload carries `agent_id`, and that presence is the whole test. stdout:
    {"hookSpecificOutput": {"hookEventName": "PostToolUse",
    "additionalContext": ...}} — the shape a subagent actually acts on.
  - exit 0 always, even on internal error, so neither a prompt nor a tool call
    is ever broken by this hook.

Thresholds, precedence, and the subagent tier are documented in README.md.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import subprocess
import sys
import traceback

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`. That
# relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)
import codex_lifecycle
import atelier_local  # noqa: E402
import model_tiers  # noqa: E402
import pending  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# The window caps the threshold and never lifts it: `[cost]`'s measured
# degradation band is an ABSOLUTE token count, so a pure fraction of a 1M
# window would overturn a measurement. At 200k these reproduce 120k/160k
# exactly; at 1M they stay there; at 64k they fall to 38.4k/51.2k.
SOFT_ABS = 120_000
HARD_ABS = 160_000
SOFT_FRAC = 0.60
HARD_FRAC = 0.80

# A worker cannot hand off, compact, or start a fresh session — the only move
# it has is to finish — so it gets one early soft line and no hard tier.
SUBAGENT_SOFT_RATIO = 0.5

# [untested] calibration, not measurement: a bigger repo makes each grounding
# read cost more, so the nudge comes earlier.
COMPLEXITY_SMALL = 5_000    # tracked files: below this, no discount
COMPLEXITY_LARGE = 20_000   # tracked files: above this, the floor factor
COMPLEXITY_MID_FACTOR = 0.85
COMPLEXITY_FLOOR = 0.75
COMPLEXITY_NEUTRAL = 1.00

TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB
REFIRE_EVERY_DEFAULT = 5  # prompts (or worker tool calls), while still above a tier
STATE_DIR_DEFAULT = "/tmp/context-watermark"
LOG_STREAM = "context-watermark"
LOG_PATH_ENV = "CONTEXT_WATERMARK_LOG_PATH"
ACTIVATION_KEY = "watermark"
GIT_TIMEOUT = 5  # under the hook's own 10s wiring timeout


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


TAIL_BYTES = _env_int("CONTEXT_WATERMARK_TAIL_BYTES", TAIL_BYTES_DEFAULT)
REFIRE_EVERY = _env_int("CONTEXT_WATERMARK_REFIRE_EVERY", REFIRE_EVERY_DEFAULT)
STATE_DIR = _env_path("CONTEXT_WATERMARK_STATE_DIR", STATE_DIR_DEFAULT)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

def compute_thresholds(window, complexity):
    """(soft, hard) for a context window in tokens, or the absolute pair when
    the window is unknown — never a fraction of an assumed one."""
    soft, hard = SOFT_ABS, HARD_ABS
    if window and window > 0:
        soft = min(SOFT_ABS, SOFT_FRAC * window)
        hard = min(HARD_ABS, HARD_FRAC * window)
    return int(soft * complexity), int(hard * complexity)


def complexity_for_count(count):
    """Tracked-file count -> factor. An unknown count is the neutral factor."""
    if count is None:
        return COMPLEXITY_NEUTRAL
    if count < COMPLEXITY_SMALL:
        return COMPLEXITY_NEUTRAL
    if count <= COMPLEXITY_LARGE:
        return COMPLEXITY_MID_FACTOR
    return COMPLEXITY_FLOOR


def tracked_file_count(cwd):
    """`git ls-files | wc -l` for `cwd`, or None outside a working tree."""
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "ls-files"], capture_output=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.count(b"\n")


def _positive(value, cast):
    try:
        parsed = cast(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _load_watermark_config(project_dir):
    """The `watermark:` key as {soft, hard, complexity}, keys omitted when the
    value is absent or unusable. `activation.py check` calls this."""
    raw = atelier_local.read_key(project_dir, ACTIVATION_KEY)
    if not isinstance(raw, dict):
        return {}
    config = {}
    for key, cast in (("soft", int), ("hard", int), ("complexity", float)):
        value = _positive(raw.get(key), cast)
        if value is not None:
            config[key] = value
    return config


def resolve_watermarks(project_dir, window, complexity):
    """(soft, hard, info) under the full precedence chain:
    env var > `watermark:` in the activation file > the computed default."""
    config = _load_watermark_config(project_dir)

    info = {"window": window, "complexity_source": "computed"}
    if "complexity" in config:
        complexity, info["complexity_source"] = config["complexity"], "activation"
    info["complexity"] = complexity

    computed = compute_thresholds(window, complexity)
    resolved = []
    for tier, value in zip(("soft", "hard"), computed):
        source = "computed"
        override = config.get(tier)
        if override is not None:
            value, source = override, "activation"
        env = _positive(os.environ.get("CONTEXT_WATERMARK_" + tier.upper()), int)
        if env is not None:
            value, source = env, "env"
        info[tier + "_source"] = source
        resolved.append(int(value))
    return resolved[0], resolved[1], info


def _session_complexity(session_id, cwd):
    """The complexity factor, computed once per session and cached.

    The hook fires on every prompt and every worker tool call; `git ls-files`
    on a large repo is a real cost to pay that often.
    """
    path = os.path.join(STATE_DIR, _state_key(session_id) + ".complexity.json")
    try:
        with open(path) as fh:
            cached = json.load(fh)
        if isinstance(cached, dict) and isinstance(cached.get("complexity"), float):
            return cached["complexity"], cached.get("tracked_files")
    except Exception:
        pass
    count = tracked_file_count(cwd)
    factor = complexity_for_count(count)
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"complexity": factor, "tracked_files": count}, fh)
    except Exception:
        pass
    return factor, count


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
    """Scan tail lines (newest last) for the last assistant message carrying a
    `.message.usage` block. Returns (usage, model) or (None, None).

    The model comes off the same line rather than a second scan: no hook
    payload carries a `model` field, so the transcript is the only source and
    reading it twice could disagree with itself.
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
            return usage, model if isinstance(model, str) else None
    return None, None


def _context_tokens_from_usage(usage):
    """ctx = input_tokens + cache_creation_input_tokens + cache_read_input_tokens.

    Any missing field is treated as 0 (defensive: docs do not guarantee all
    three fields are always present).
    """
    def _num(x):
        return x if isinstance(x, (int, float)) else 0

    return (
        _num(usage.get("input_tokens"))
        + _num(usage.get("cache_creation_input_tokens"))
        + _num(usage.get("cache_read_input_tokens"))
    )


def _window_for(model):
    """The model's context window in tokens, or None when it is unmapped."""
    try:
        return model_tiers.window_for(model_tiers.load(), model)
    except Exception:
        return None


def _subagent_transcript(transcript_path, agent_id):
    """A worker's OWN transcript, or None.

    Inside a worker, `transcript_path` names the MAIN SESSION transcript
    (measured 2026-09-08) — reading it would silently measure the parent.
    """
    key = pending.agent_key(agent_id)
    directory = pending.subagents_dir(transcript_path)
    if not key or not directory:
        return None
    path = os.path.join(directory, pending.AGENT_FILE_PREFIX + key + ".jsonl")
    return path if os.path.isfile(path) else None


# ---------------------------------------------------------------------------
# Anti-nag state
# ---------------------------------------------------------------------------

def _state_key(session_id, agent_id=None):
    raw = session_id if agent_id is None else "{0}-agent-{1}".format(session_id, agent_id)
    return "".join(c for c in raw if c.isalnum() or c in "-_") or "unknown"


def _state_path(session_id, agent_id=None):
    return os.path.join(STATE_DIR, _state_key(session_id, agent_id) + ".json")


def _load_state(session_id, agent_id=None):
    """The anti-nag state, or {} for anything unreadable — including valid JSON
    that is not an object, which would otherwise raise on every later call and
    never be rewritten."""
    try:
        with open(_state_path(session_id, agent_id)) as f:
            state = json.load(f)
    except Exception:
        return {}
    return state if isinstance(state, dict) else {}


def _save_state(session_id, state, agent_id=None):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_state_path(session_id, agent_id), "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def _tier_for(ctx_tokens, soft, hard):
    if hard is not None and ctx_tokens >= hard:
        return "hard"
    if ctx_tokens >= soft:
        return "soft"
    return "none"


def _should_fire(state, tier):
    """Fire at most once per tier crossing, then at most every REFIRE_EVERY
    events while still at or above that tier.

    `prompts_since_fire` is given post-increment by the caller, so
    REFIRE_EVERY=N fires on the Nth subsequent event.
    """
    if tier != state.get("last_tier", "none"):
        return True
    return state.get("prompts_since_fire", 0) >= REFIRE_EVERY


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
    # A worker has no /handoff, no /clear and no successor session, so the only
    # move it can take is the one this names. It names its sender and disclaims
    # the model's limit because a live worker refused an earlier wording as
    # probable prompt injection: it could see millions of tokens still free.
    "subagent": (
        "atelier context-watermark: your context is ~{k}k tokens, past the ~{soft}k "
        "budget for a delegated worker. That is a quality line from a measured "
        "degradation band, NOT the model's context limit — a large remaining token "
        "budget is not evidence against it. Wrap up and report now: stop taking on new "
        "work, commit what is done, and return what is finished, what is not, and your "
        "evidence. If the remaining work is genuinely small, finishing it first and then "
        "reporting is an acceptable answer."
    ),
}


def _format_message(tier, ctx_tokens, soft, hard):
    return MESSAGES[tier].format(
        k=round(ctx_tokens / 1000),
        soft=round(soft / 1000),
        hard=round(hard / 1000) if hard else "",
    )


# ---------------------------------------------------------------------------
# Event branches
# ---------------------------------------------------------------------------

def _measure(transcript_path, project_dir, session_id, cwd):
    """(ctx_tokens, model, (soft, hard), error, info) for one transcript.

    Raises nothing the caller has to know about: a transcript it cannot read
    or that carries no usage block yields ctx_tokens None.
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return None, None, None, "transcript_path missing or not a file", None
    if codex_lifecycle.enabled():
        try:
            measured = codex_lifecycle.measure(transcript_path)
        except codex_lifecycle.PendingMeasurement as exc:
            return None, None, None, exc, None
        except (OSError, ValueError) as exc:
            return None, None, None, str(exc), None
        complexity, tracked = _session_complexity(session_id, cwd)
        soft, hard, info = resolve_watermarks(project_dir, measured["window"], complexity)
        info["tracked_files"] = tracked
        return measured["ctx_tokens"], measured["model"], (soft, hard), None, info
    usage, model = _find_last_assistant_usage(_read_tail(transcript_path, TAIL_BYTES))
    if usage is None:
        return None, None, None, "no assistant usage found in tail window", None
    complexity, tracked = _session_complexity(session_id, cwd)
    window = _window_for(model)
    soft, hard, info = resolve_watermarks(project_dir, window, complexity)
    info["tracked_files"] = tracked
    return _context_tokens_from_usage(usage), model, (soft, hard), None, info


def _row(scope, session_id, ctx_tokens, tier, fired, model=None, info=None,
         soft=None, hard=None, error=None, pending=False):
    row = {
        "scope": scope,
        "session_id": session_id,
        "ctx_tokens": ctx_tokens,
        "tier": tier,
        "fired": fired,
        "model": model,
        "window": (info or {}).get("window"),
        # "did this check measure a window?" — a missing model id and an
        # unmapped one are the same answer, and an error row measured nothing.
        "window_fallback": bool(info) and not info.get("window"),
        "complexity": (info or {}).get("complexity"),
        "soft": soft,
        "hard": hard,
    }
    if info:
        # No key for a value this scope has not got: a worker has no hard tier,
        # and naming a precedence tier for it would describe a resolution that
        # never reached the row.
        row["sources"] = {
            "soft": info.get("soft_source"),
            "complexity": info.get("complexity_source"),
        }
        if hard is not None:
            row["sources"]["hard"] = info.get("hard_source")
    if error:
        row["error"] = error
    if pending:
        row["pending"] = True
    return row


def handle_session(payload, log):
    """UserPromptSubmit: the session's own context against soft and hard."""
    session_id = payload.get("session_id", "unknown")
    cwd = payload.get("cwd") or os.getcwd()
    project_dir = (os.environ.get("CLAUDE_PROJECT_DIR") if os.environ.get("ATELIER_HARNESS") != "codex" else None) or cwd

    ctx_tokens, model, tiers, error, info = _measure(
        payload.get("transcript_path"), project_dir, session_id, cwd)
    if error:
        pending_measurement = isinstance(error, codex_lifecycle.PendingMeasurement)
        if codex_lifecycle.enabled() and not pending_measurement:
            codex_lifecycle.diagnostic(error)
        log(_row("session", session_id, None, "none", False,
                 error=None if pending_measurement else error,
                 pending=pending_measurement))
        return

    soft, hard = tiers
    tier = _tier_for(ctx_tokens, soft, hard)
    fired = False

    if tier == "none":
        _save_state(session_id, {"last_tier": "none", "prompts_since_fire": 0})
    else:
        state = _load_state(session_id)
        if tier != state.get("last_tier", "none"):
            check_state = state
        else:
            check_state = {**state,
                           "prompts_since_fire": state.get("prompts_since_fire", 0) + 1}
        if _should_fire(check_state, tier):
            fired = True
            # UserPromptSubmit takes a TOP-LEVEL additionalContext field, not
            # the hookSpecificOutput envelope PostToolUse takes. systemMessage
            # makes the nudge visible to the user; additionalContext is only
            # ever seen by the model.
            print(json.dumps({
                **({"hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": _format_message(tier, ctx_tokens, soft, hard)}}
                   if codex_lifecycle.enabled() else {
                    "additionalContext": _format_message(tier, ctx_tokens, soft, hard)}),
                "systemMessage": (
                    "atelier: context ~{0}k tokens — {1} watermark ({2}k/{3}k) crossed; "
                    "nudging /handoff + /clear.".format(
                        round(ctx_tokens / 1000), tier, round(soft / 1000),
                        round(hard / 1000))),
            }))
            _save_state(session_id, {"last_tier": tier, "prompts_since_fire": 0})
        else:
            _save_state(session_id, {
                "last_tier": tier,
                "prompts_since_fire": check_state.get("prompts_since_fire", 0)})

    log(_row("session", session_id, ctx_tokens, tier, fired, model, info, soft, hard))


def handle_subagent(payload, log):
    """PostToolUse inside a worker: soft only, at half the session's line."""
    session_id = payload.get("session_id", "unknown")
    agent_id = payload.get("agent_id")
    cwd = payload.get("cwd") or os.getcwd()
    project_dir = (os.environ.get("CLAUDE_PROJECT_DIR") if os.environ.get("ATELIER_HARNESS") != "codex" else None) or cwd

    transcript = (payload.get("transcript_path") if codex_lifecycle.enabled()
                  else _subagent_transcript(payload.get("transcript_path"), agent_id))
    if not transcript:
        log(dict(_row("subagent", session_id, None, "none", False,
                      error="no subagent transcript for this agent_id"),
                 agent_id=agent_id))
        return

    ctx_tokens, model, tiers, error, info = _measure(
        transcript, project_dir, session_id, cwd)
    if error:
        pending_measurement = isinstance(error, codex_lifecycle.PendingMeasurement)
        if codex_lifecycle.enabled() and not pending_measurement:
            codex_lifecycle.diagnostic(error)
        log(dict(_row("subagent", session_id, None, "none", False,
                      error=None if pending_measurement else error,
                      pending=pending_measurement),
                 agent_id=agent_id))
        return

    soft = int(tiers[0] * SUBAGENT_SOFT_RATIO)
    tier = _tier_for(ctx_tokens, soft, None)
    fired = False

    if tier == "none":
        _save_state(session_id, {"last_tier": "none", "prompts_since_fire": 0}, agent_id)
    else:
        state = _load_state(session_id, agent_id)
        if tier != state.get("last_tier", "none"):
            check_state = state
        else:
            check_state = {**state,
                           "prompts_since_fire": state.get("prompts_since_fire", 0) + 1}
        if _should_fire(check_state, tier):
            fired = True
            # PostToolUse reaches a subagent only through this envelope
            # (measured 2026-09-08: the worker acted on it).
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": _format_message(
                    "subagent", ctx_tokens, soft, None),
            }}))
            _save_state(session_id, {"last_tier": tier, "prompts_since_fire": 0},
                        agent_id)
        else:
            _save_state(session_id, {
                "last_tier": tier,
                "prompts_since_fire": check_state.get("prompts_since_fire", 0)},
                agent_id)

    # `soft` here is the resolved SESSION line halved, so the row carries both
    # terms: `sources.soft` names where the session value came from, not this one.
    log(dict(_row("subagent", session_id, ctx_tokens, tier, fired, model, info, soft),
             agent_id=agent_id, session_soft=tiers[0],
             subagent_soft_ratio=SUBAGENT_SOFT_RATIO))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        payload = json.loads(sys.stdin.read())
        if isinstance(payload, dict):
            payload = codex_lifecycle.prepare(payload)
            if payload is None:
                return
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(payload.get("cwd")))

        if payload.get("agent_id"):
            handle_subagent(payload, log)
        elif payload.get("hook_event_name") != "PostToolUse":
            handle_session(payload, log)
        # PostToolUse without an agent_id is the PARENT's own tool call: the
        # session is already watched on every prompt, so there is nothing to
        # say and no row to write.
        sys.exit(0)

    except Exception as e:
        if codex_lifecycle.enabled():
            codex_lifecycle.diagnostic(e)
        # Fail-open: never break a prompt or a tool call. Log what we can.
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
