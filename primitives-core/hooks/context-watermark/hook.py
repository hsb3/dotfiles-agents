#!/usr/bin/env python3
"""
context-watermark — UserPromptSubmit (session) + PostToolUse (subagent) hook.

Reads the transcript tail, computes an approximate current-context token count
from the last assistant usage block, and injects a reminder when the count
crosses a watermark. The watermarks are keyed by layer (a worker, or the
session itself) and capped, never lifted, by the model's context window; every
stage is overridable. Anti-nag state is persisted per session (and per worker) so the
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

Thresholds, precedence, and the two layers are documented in README.md.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
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

# Tunable advisory defaults per layer, not performance facts. The context
# window caps each stage so smaller models are protected at 30/60/80 percent.
DEFAULT_STAGES = {
    "worker": (100_000, 160_000, 250_000),
    "session": (150_000, 250_000, 400_000),
}
STAGE_FRACS = (0.30, 0.60, 0.80)

TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB
REFIRE_EVERY_DEFAULT = 5  # prompts (or worker tool calls), while still above a tier
STATE_DIR_DEFAULT = "/tmp/context-watermark"
LOG_STREAM = "context-watermark"
LOG_PATH_ENV = "CONTEXT_WATERMARK_LOG_PATH"
ACTIVATION_KEY = "watermark"


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

def compute_thresholds(window, complexity, layer="session"):
    """(notice, soft, hard) for a layer, times complexity, then capped by a known window."""
    defaults = DEFAULT_STAGES.get(layer, DEFAULT_STAGES["session"])
    defaults = tuple(value * complexity for value in defaults)
    if window and window > 0:
        defaults = tuple(min(value, frac * window)
                         for value, frac in zip(defaults, STAGE_FRACS))
    return tuple(int(value) for value in defaults)


def _positive(value, cast):
    try:
        parsed = cast(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _flow_mapping(raw):
    """`{soft: 200000, hard: 250000}` -> dict; the activation parser keeps it a string."""
    if isinstance(raw, dict):
        return raw
    if not (isinstance(raw, str) and raw.startswith("{") and raw.endswith("}")):
        return {}
    pairs = (item.split(":", 1) for item in raw[1:-1].split(",") if ":" in item)
    return {k.strip().lower(): v.strip() for k, v in pairs}


def _load_watermark_config(project_dir, layer=None):
    """The `watermark:` key as {notice, soft, hard, complexity}, keys omitted when the
    value is absent or unusable. A `worker:`/`session:` sub-mapping overrides the flat
    keys for that layer; no layer is the flat view `activation.py check` reports."""
    raw = atelier_local.read_key(project_dir, ACTIVATION_KEY)
    if not isinstance(raw, dict):
        return {}
    config = {}
    for source in (raw, _flow_mapping(raw.get(layer)) if layer else {}):
        for key, cast in (("notice", int), ("soft", int), ("hard", int),
                          ("complexity", float)):
            value = _positive(source.get(key), cast)
            if value is not None:
                config[key] = value
    return config


def resolve_stages(project_dir, window, layer="session"):
    """(notice, soft, hard, info): env > activation file > computed, per stage."""
    config = _load_watermark_config(project_dir, layer)
    info = {"window": window, "layer": layer, "complexity_source": "computed"}
    complexity = 1.0
    if "complexity" in config:
        complexity, info["complexity_source"] = config["complexity"], "activation"
    info["complexity"] = complexity
    values = list(compute_thresholds(window, complexity, layer))
    for index, tier in enumerate(("notice", "soft", "hard")):
        source = "computed"
        value = config.get(tier)
        if value is not None:
            values[index], source = value, "activation"
        env = _positive(os.environ.get("CONTEXT_WATERMARK_" + tier.upper()), int)
        if env is not None:
            values[index], source = env, "env"
        info[tier + "_source"] = source
    values[0] = min(values[0], values[1])
    return values[0], values[1], values[2], info


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


def _tier_for(ctx_tokens, notice, soft, hard):
    if hard is not None and ctx_tokens >= hard:
        return "hard"
    if ctx_tokens >= soft:
        return "soft"
    if ctx_tokens >= notice:
        return "notice"
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
    "notice": (
        "atelier context-watermark: context is ~{k}k tokens, past the ~{notice}k "
        "notice watermark. This is advisory: reduce further grounding reads and "
        "continue the current bounded slice."
    ),
    "soft": (
        "atelier context-watermark: context is ~{k}k tokens, past the ~{soft}k soft "
        "watermark. This is advisory: checkpoint at the next safe boundary; finish "
        "small bounded work before arranging continuation."
    ),
    "hard": (
        "atelier context-watermark: context is ~{k}k tokens, past the ~{hard}k hard "
        "watermark. This is advisory and grants no authority: preserve the branch, "
        "worktree, uncommitted changes, and test proof in a manager-facilitated checkpoint "
        "before continuation."
    ),
    "session_hard": (
        "atelier context-watermark: context is ~{k}k tokens, past the ~{hard}k hard "
        "watermark. This is advisory: update the handoff now; if a coordinator owns "
        "your cycle, stop after the handoff and wait for it rather than compacting."
    ),
}


def _format_message(tier, ctx_tokens, notice, soft, hard, layer="worker"):
    key = "session_hard" if (tier, layer) == ("hard", "session") else tier
    return MESSAGES[key].format(
        k=round(ctx_tokens / 1000),
        notice=round(notice / 1000),
        soft=round(soft / 1000),
        hard=round(hard / 1000) if hard else "",
    )


# ---------------------------------------------------------------------------
# Event branches
# ---------------------------------------------------------------------------

def _measure(transcript_path, project_dir, layer):
    """(ctx_tokens, model, (notice, soft, hard), error, info) for one transcript.

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
        notice, soft, hard, info = resolve_stages(project_dir, measured["window"], layer)
        return measured["ctx_tokens"], measured["model"], (notice, soft, hard), None, info
    usage, model = _find_last_assistant_usage(_read_tail(transcript_path, TAIL_BYTES))
    if usage is None:
        return None, None, None, "no assistant usage found in tail window", None
    notice, soft, hard, info = resolve_stages(project_dir, _window_for(model), layer)
    return _context_tokens_from_usage(usage), model, (notice, soft, hard), None, info


def _row(scope, session_id, ctx_tokens, tier, fired, model=None, info=None,
         notice=None, soft=None, hard=None, error=None, pending=False):
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
        row["layer"] = info.get("layer")
        row["notice"] = notice
        row["sources"] = {
            "notice": info.get("notice_source"),
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
        payload.get("transcript_path"), project_dir, "session")
    if error:
        pending_measurement = isinstance(error, codex_lifecycle.PendingMeasurement)
        if codex_lifecycle.enabled() and not pending_measurement:
            codex_lifecycle.diagnostic(error)
        log(_row("session", session_id, None, "none", False,
                 error=None if pending_measurement else error,
                 pending=pending_measurement))
        return

    notice, soft, hard = tiers
    tier = _tier_for(ctx_tokens, notice, soft, hard)
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
                    "additionalContext": _format_message(
                        tier, ctx_tokens, notice, soft, hard, "session")}}
                   if codex_lifecycle.enabled() else {
                    "additionalContext": _format_message(
                        tier, ctx_tokens, notice, soft, hard, "session")}),
                "systemMessage": (
                    "atelier: context ~{0}k tokens — {1} watermark ({2}k/{3}k/{4}k) crossed.".format(
                        round(ctx_tokens / 1000), tier, round(notice / 1000),
                        round(soft / 1000), round(hard / 1000))),
            }))
            _save_state(session_id, {"last_tier": tier, "prompts_since_fire": 0})
        else:
            _save_state(session_id, {
                "last_tier": tier,
                "prompts_since_fire": check_state.get("prompts_since_fire", 0)})

    log(_row("session", session_id, ctx_tokens, tier, fired, model, info,
             notice, soft, hard))


def handle_subagent(payload, log):
    """PostToolUse inside a worker: the same advisory stages as its session."""
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
        transcript, project_dir, "worker")
    if error:
        pending_measurement = isinstance(error, codex_lifecycle.PendingMeasurement)
        if codex_lifecycle.enabled() and not pending_measurement:
            codex_lifecycle.diagnostic(error)
        log(dict(_row("subagent", session_id, None, "none", False,
                      error=None if pending_measurement else error,
                      pending=pending_measurement),
                 agent_id=agent_id))
        return

    notice, soft, hard = tiers
    tier = _tier_for(ctx_tokens, notice, soft, hard)
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
                    tier, ctx_tokens, notice, soft, hard),
            }}))
            _save_state(session_id, {"last_tier": tier, "prompts_since_fire": 0},
                        agent_id)
        else:
            _save_state(session_id, {
                "last_tier": tier,
                "prompts_since_fire": check_state.get("prompts_since_fire", 0)},
                agent_id)

    log(dict(_row("subagent", session_id, ctx_tokens, tier, fired, model, info,
                  notice, soft, hard), agent_id=agent_id))


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
