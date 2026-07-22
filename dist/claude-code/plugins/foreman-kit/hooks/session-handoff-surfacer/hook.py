#!/usr/bin/env python3
"""
session-handoff-surfacer — SessionStart hook.

On a genuinely COLD start (source "startup" or "clear"), discovers the
project's handoff file and injects a pointer plus a capped head excerpt so a
fresh session picks up prior work without re-deriving it. This is the
"consume" edge of the handoff loop; handoff-freshness-guard is the "produce"
edge (it nags before compaction if the handoff wasn't refreshed).

Silent no-op on "resume"/"compact" (context is already present — surfacing
would be pure noise) and when no handoff file exists.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SessionStart):
  - stdin JSON fields consumed: session_id, transcript_path, cwd,
    hook_event_name, source ("startup"|"resume"|"clear"|"compact"),
    optionally model, agent_type, session_title.
  - stdout JSON (ONLY when surfacing):
    {"hookSpecificOutput": {"hookEventName": "SessionStart",
                             "additionalContext": "..."}}
    NOTE: SessionStart nests additionalContext under hookSpecificOutput —
    this is DIFFERENT from UserPromptSubmit's top-level additionalContext
    (see context-watermark/hook.py), which is why this hook does not reuse
    that shape.
  - exit 0 always; fail-open on any internal error (no stdout, just a
    best-effort log line).

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import sys
import time
import traceback

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

HEAD_LINES_DEFAULT = 15
LOG_FILENAME_DEFAULT = "handoff-surfacer.jsonl"

# Same discovery precedence as handoff-freshness-guard/hook.py.
CANDIDATE_PATHS = [
    "_meta/HANDOFF.md",
    "HANDOFF.md",
    ".claude/HANDOFF.md",
]

# Sources that count as a genuine cold start.
SURFACE_SOURCES = {"startup", "clear"}


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


HEAD_LINES = _env_int("HANDOFF_SURFACER_HEAD_LINES", HEAD_LINES_DEFAULT)


def _resolve_log_path(cwd):
    """HANDOFF_SURFACER_LOG_PATH override, else <cwd>/logs/handoff-surfacer.jsonl.

    Kept cwd-relative (not a hardcoded machine path) so the hook is portable
    across any project that installs the foreman-kit plugin, not just this
    one — matching scripts/log_dispatch.py's override convention.
    """
    override = os.environ.get("HANDOFF_SURFACER_LOG_PATH")
    if override:
        return override
    base = cwd or os.getcwd()
    return os.path.join(base, "logs", LOG_FILENAME_DEFAULT)


# ---------------------------------------------------------------------------
# Logging (best-effort; must never raise into the caller)
# ---------------------------------------------------------------------------

def _log(log_path, record):
    try:
        d = os.path.dirname(log_path)
        if d:
            os.makedirs(d, exist_ok=True)
        record.setdefault("ts", time.time())
        with open(log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Handoff discovery + head excerpt
# ---------------------------------------------------------------------------

def _find_handoff(cwd):
    """Return (path, relpath) for the first candidate that exists under cwd,
    else (None, None). Checked in the documented precedence order."""
    for rel in CANDIDATE_PATHS:
        path = os.path.join(cwd, rel)
        if os.path.isfile(path):
            return path, rel
    return None, None


def _read_head_lines(path, n):
    """Read the first n lines of a text file (best-effort; short reads are
    fine, this is a capped excerpt, not the full file)."""
    lines = []
    with open(path, "r", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def _format_message(relpath, head_text):
    return (
        f"A project handoff exists at {relpath} — read it before starting. "
        f"First lines:\n{head_text}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)

        session_id = payload.get("session_id", "unknown")
        cwd = payload.get("cwd") or os.getcwd()
        source = payload.get("source", "unknown")

        log_path = _resolve_log_path(cwd)

        path, relpath = _find_handoff(cwd)

        if source not in SURFACE_SOURCES:
            _log(log_path, {
                "session_id": session_id,
                "source": source,
                "handoff_path": relpath,
                "surfaced": False,
                "reason": "source not eligible for surfacing",
            })
            sys.exit(0)

        if path is None:
            _log(log_path, {
                "session_id": session_id,
                "source": source,
                "handoff_path": None,
                "surfaced": False,
                "reason": "no handoff file found",
            })
            sys.exit(0)

        head_text = _read_head_lines(path, HEAD_LINES)
        message = _format_message(relpath, head_text)

        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": message,
            },
            # Visible to the USER in the TUI — evidence the hook fired
            # (additionalContext is only ever seen by the model).
            "systemMessage": f"foreman-kit: surfaced project handoff ({relpath}).",
        }
        print(json.dumps(out))

        _log(log_path, {
            "session_id": session_id,
            "source": source,
            "handoff_path": relpath,
            "surfaced": True,
        })

        sys.exit(0)

    except Exception as e:
        # Fail-open: never break session start on our own error.
        try:
            _log(
                os.environ.get("HANDOFF_SURFACER_LOG_PATH")
                or os.path.join(os.getcwd(), "logs", LOG_FILENAME_DEFAULT),
                {
                    "session_id": None,
                    "source": None,
                    "surfaced": False,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(limit=3),
                },
            )
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
