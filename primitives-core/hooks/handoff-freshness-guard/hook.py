#!/usr/bin/env python3
"""
handoff-freshness-guard — PreCompact hook.

Before compaction proceeds, checks whether the project's handoff file is
fresh. If stale/missing on a MANUAL /compact, blocks and tells the user to
run /handoff first. On AUTO compaction, never blocks (a blocked auto-compact
near a full context window could wedge the session with no way to recover
context headroom) — instead it logs and emits non-blocking guidance via
`systemMessage`.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreCompact):
  - stdin JSON fields consumed: session_id, cwd, trigger ("manual"|"auto")
  - stdout JSON: {"decision": "block", "reason": "...", "systemMessage": "..."}
    OR {"systemMessage": "..."} (non-blocking) OR nothing (allow silently)
  - exit 0 with decision:"block" blocks compaction (confirmed: PreCompact
    supports top-level decision control, same as exit code 2 but non-fatal
    to the hook process itself).
  - exit 2 is the guaranteed-block path (used defensively as a fallback is
    NOT needed here since decision:"block" on exit 0 is documented and
    sufficient) — we use JSON decision control exclusively so a fail-open
    default is possible without special-casing exit codes.
  - Fail-open: any internal error -> exit 0, no JSON (compaction proceeds).
"""

import json
import os
import sys
import time
import traceback

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

FRESHNESS_MINUTES_DEFAULT = 30
LOG_FILENAME_DEFAULT = "handoff-guard.jsonl"

CANDIDATE_PATHS = [
    "_meta/HANDOFF.md",
    "HANDOFF.md",
    ".claude/HANDOFF.md",
]


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


FRESHNESS_MINUTES = _env_int(
    "HANDOFF_GUARD_FRESHNESS_MINUTES", FRESHNESS_MINUTES_DEFAULT
)


def _resolve_log_path(cwd):
    """HANDOFF_GUARD_LOG_PATH override, else <project-root>/logs/handoff-guard.jsonl.

    The project root is CLAUDE_PROJECT_DIR (set by Claude Code for hook
    commands), matching the surfacer and telemetry hooks' convention, so the
    hook stays portable across any project that installs this plugin. The
    payload cwd is a last resort only — anchoring on cwd scatters stray
    logs/ dirs into whatever subdirectory an agent happens to be running in.
    """
    override = os.environ.get("HANDOFF_GUARD_LOG_PATH")
    if override:
        return override
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
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
# Handoff file discovery
# ---------------------------------------------------------------------------

def _find_handoff(cwd):
    """Return (path, mtime) for the first candidate that exists, else
    (None, None). Checked in the documented precedence order."""
    for rel in CANDIDATE_PATHS:
        path = os.path.join(cwd, rel)
        if os.path.isfile(path):
            try:
                return path, os.path.getmtime(path)
            except OSError:
                continue
    return None, None


def _age_minutes(mtime):
    return (time.time() - mtime) / 60.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)

        session_id = payload.get("session_id", "unknown")
        cwd = payload.get("cwd") or os.getcwd()
        trigger = payload.get("trigger", "unknown")  # "manual" | "auto"
        log_path = _resolve_log_path(cwd)

        path, mtime = _find_handoff(cwd)

        if path is None:
            status = "missing"
            age = None
        else:
            age = _age_minutes(mtime)
            status = "fresh" if age < FRESHNESS_MINUTES else "stale"

        blocked = False
        out = None

        if status == "fresh":
            # Allow silently.
            out = None
        else:
            if trigger == "manual":
                blocked = True
                reason = (
                    "Handoff is stale/missing — run /handoff first, then /compact."
                    if status == "stale"
                    else "No handoff file found (_meta/HANDOFF.md, HANDOFF.md, or "
                    ".claude/HANDOFF.md) — run /handoff first, then /compact."
                )
                out = {
                    "decision": "block",
                    "reason": reason,
                    "systemMessage": reason,
                }
            else:
                # AUTO trigger: never block. A blocked auto-compact near a
                # full context window could wedge the session (no headroom
                # left to run /handoff or anything else). Emit non-blocking
                # guidance instead; PostCompact/next UserPromptSubmit turn
                # can pick up the slack.
                msg = (
                    "Auto-compaction is proceeding with a stale/missing handoff "
                    "file. Run /handoff soon to avoid losing externalized state "
                    "on the next compaction."
                )
                out = {"systemMessage": msg}

        if out is not None:
            print(json.dumps(out))

        _log(log_path, {
            "session_id": session_id,
            "cwd": cwd,
            "trigger": trigger,
            "handoff_path": path,
            "handoff_age_minutes": age,
            "status": status,
            "blocked": blocked,
        })

        sys.exit(0)

    except Exception as e:
        # Fail-open: never block compaction on our own error.
        try:
            _log(_resolve_log_path(None), {
                "session_id": None,
                "trigger": None,
                "status": "error",
                "blocked": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            })
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
