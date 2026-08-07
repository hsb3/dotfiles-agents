#!/usr/bin/env python3
"""
delegation-watermark — PostToolUse hook.

Counts the delegable tool calls the MAIN session has performed since its last
delegation, and nudges once the streak crosses a watermark. The companion of
context-watermark: that one watches how much context a session is carrying,
this one watches how much labor it is retaining.

Motivation (the source lab's finding F7, the work-list trigger gap): a
strategist that never delegates looks, from the inside, exactly like a
strategist doing careful work. The failure is only visible in aggregate — e.g.
a session that ran 6+ hours with 93 self-performed tool calls and zero
dispatches. A watermark makes the aggregate visible without anyone asking for
it.

Purely observational: never blocks, never edits, fail-open on every error.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PostToolUse):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, tool_name,
    agent_id (present ONLY when the hook fires inside a subagent — the hook
    exits silently in that case; workers are not nudged to delegate).
  - stdout JSON (exit 0):
      {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                              "additionalContext": "..."},
       "systemMessage": "..."}
    additionalContext nests under hookSpecificOutput; systemMessage is
    top-level.
  - exit 0 always.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

SOFT_DEFAULT = 25          # delegable calls since the last dispatch before the first nudge
REFIRE_EVERY_DEFAULT = 15  # further calls before nudging again, while the streak keeps growing
MAX_BYTES_DEFAULT = 64 * 1024 * 1024  # refuse to scan a pathological transcript
STATE_DIR_DEFAULT = "/tmp/delegation-watermark"
LOG_FILENAME_DEFAULT = "delegation-watermark.jsonl"

# The whole transcript is scanned, not a tail window: a tail that happens to
# exclude the last dispatch reports an inflated streak and fires on a session
# that IS delegating. Measured on real transcripts, a full scan of a 2 MB
# transcript costs ~4 ms (~25 ms end-to-end including interpreter startup)
# because the cheap substring test below rejects non-tool lines before any
# JSON parsing.
TOOL_USE_MARKER = '"tool_use"'

# Work a cheaper agent could have done. TodoWrite/Skill/AskUserQuestion and the
# like are session bookkeeping, not labor, so they do not count toward a streak.
DELEGABLE_TOOLS = {
    "Read", "Grep", "Glob", "Bash", "Edit", "Write", "MultiEdit", "NotebookEdit",
}
DISPATCH_TOOLS = {"Task", "Agent"}


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


SOFT = _env_int("DELEGATION_WATERMARK_SOFT", SOFT_DEFAULT)
REFIRE_EVERY = _env_int("DELEGATION_WATERMARK_REFIRE_EVERY", REFIRE_EVERY_DEFAULT)
MAX_BYTES = _env_int("DELEGATION_WATERMARK_MAX_BYTES", MAX_BYTES_DEFAULT)
STATE_DIR = os.environ.get("DELEGATION_WATERMARK_STATE_DIR") or STATE_DIR_DEFAULT


def _resolve_log_path(cwd):
    """Override, else <project-root>/logs/delegation-watermark.jsonl.

    CLAUDE_PROJECT_DIR is set by Claude Code for hook commands; anchoring on the
    payload cwd instead scatters stray logs/ dirs into whatever subdirectory an
    agent happened to be in. With no override, no CLAUDE_PROJECT_DIR, and no
    payload cwd, return None — skip logging rather than anchor on the process
    cwd, which is exactly the scattering this function exists to avoid.
    """
    override = os.environ.get("DELEGATION_WATERMARK_LOG_PATH")
    if override:
        return override
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    if not base:
        return None
    return os.path.join(base, "logs", LOG_FILENAME_DEFAULT)


# ---------------------------------------------------------------------------
# Best-effort IO (never raises into the caller)
# ---------------------------------------------------------------------------

def _log(log_path, record):
    if not log_path:
        return
    try:
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        pass


def _emit(obj):
    """Print the hook's one JSON object without letting a closed stdout turn
    into a nonzero exit: flush inside the guard, and on a broken pipe point
    fd 1 at devnull so the interpreter's shutdown flush has nothing to do."""
    try:
        print(json.dumps(obj))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
        except Exception:
            pass


def _state_path(session_id):
    return os.path.join(STATE_DIR, f"{session_id}.json")


def _load_state(session_id):
    try:
        with open(_state_path(session_id), encoding="utf-8") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _save_state(session_id, state):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_state_path(session_id), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass


def _scan(path):
    """Walk the whole transcript; return (streak, dispatches, delegable_total).

    streak          — delegable calls made after the LAST dispatch
    dispatches      — dispatches made this session
    delegable_total — delegable calls made this session

    Subagent turns (`isSidechain`) are skipped: a worker's own tool calls are
    delegated labor, not retained labor.
    """
    streak = 0
    dispatches = 0
    delegable_total = 0

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if TOOL_USE_MARKER not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "assistant" or rec.get("isSidechain"):
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                if name in DISPATCH_TOOLS:
                    dispatches += 1
                    streak = 0           # a dispatch resets the streak
                elif name in DELEGABLE_TOOLS:
                    delegable_total += 1
                    streak += 1

    return streak, dispatches, delegable_total


def _format_message(streak, dispatches, ratio):
    ratio_line = (
        f"Session-performed delegable calls per dispatch so far: ~{ratio:.0f}:1."
        if ratio is not None
        else "No delegation has happened in this session yet."
    )
    return (
        f"[atelier] Delegation watermark: {streak} delegable tool calls "
        f"(reads, greps, edits, shell) in an unbroken run with no delegation. {ratio_line}\n\n"
        "For calibration: delegating sessions' solo runs mostly stayed under ~25, and their "
        "longer stretches (36-69) were grounding or closing work done by hand; sessions that "
        "delegated nothing at all ran 80-103. Past ~25 on a job sized as flat fan-out, "
        "manager-driven, or phased crews, the session is executing rather than running the "
        "strategy layer. Pause and re-size:\n"
        "- Is there a work-list left? Hand the remainder to workers rather than continuing "
        "by hand.\n"
        "- Is the recon still unfinished? Dispatch scouts and read their report instead of "
        "the tree.\n"
        "- Are these small fixes discovered along the way? Collect them on a punch list and "
        "give the list to one agent.\n"
        "- If this work genuinely belongs to the session (decomposition, definition of done, "
        "judging conflicting reports, final gate runs, user-facing synthesis), say so in one "
        "line and carry on — that is the strategy layer's floor, and this nudge is answered by "
        "naming it.\n\n"
        "The delegation skill has the full floor-and-ceiling list."
    )


def main():
    log_path = None
    payload = None
    try:
        payload = json.loads(sys.stdin.read())

        # Never nudge a subagent: a worker delegating is not the behavior we want.
        if payload.get("agent_id"):
            sys.exit(0)

        session_id = payload.get("session_id", "unknown")
        transcript_path = payload.get("transcript_path")
        log_path = _resolve_log_path(payload.get("cwd"))

        if not transcript_path or not os.path.isfile(transcript_path):
            _log(log_path, {
                "session_id": session_id, "fired": False,
                "error": "transcript_path missing or not a file",
            })
            sys.exit(0)

        size = os.path.getsize(transcript_path)
        if size > MAX_BYTES:
            _log(log_path, {
                "session_id": session_id, "fired": False,
                "error": f"transcript {size} bytes exceeds MAX_BYTES {MAX_BYTES}",
            })
            sys.exit(0)

        streak, dispatches, delegable_total = _scan(transcript_path)
        ratio = (delegable_total / dispatches) if dispatches else None

        state = _load_state(session_id)
        try:
            last_fire_at = int(state.get("last_fire_at_streak", 0) or 0)
        except (TypeError, ValueError):
            last_fire_at = 0

        fired = False
        if streak < SOFT:
            # Below the line, or a dispatch just reset it: clear the anti-nag mark.
            if last_fire_at:
                _save_state(session_id, {"last_fire_at_streak": 0})
        elif last_fire_at == 0 or streak - last_fire_at >= REFIRE_EVERY:
            fired = True
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": _format_message(streak, dispatches, ratio),
                },
                "systemMessage": (
                    f"atelier: {streak} tool calls since the last delegation"
                    + (f" (~{ratio:.0f}:1 overall)" if ratio is not None else " (none yet)")
                    + " — re-size or name the floor item."
                ),
            }
            _emit(out)
            _save_state(session_id, {"last_fire_at_streak": streak})

        _log(log_path, {
            "session_id": session_id,
            "tool_name": payload.get("tool_name"),
            "streak": streak,
            "dispatches": dispatches,
            "delegable_total": delegable_total,
            "ratio": round(ratio, 2) if ratio is not None else None,
            "fired": fired,
        })
        sys.exit(0)

    except Exception as e:
        try:
            if not isinstance(payload, dict):
                payload = {}
            _log(log_path or _resolve_log_path(payload.get("cwd")), {
                "session_id": payload.get("session_id"), "fired": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            })
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
