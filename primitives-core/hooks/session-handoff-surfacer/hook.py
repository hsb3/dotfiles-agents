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

Per-project override: a `handoff:` key in `.claude/atelier.local.md` names
the project's handoff file, taking full precedence over the standard
candidate search below (found or not — an override that names a file that
does not yet exist means "no handoff", not "fall back to the trio"). Absent,
unparseable, or out-of-project-root overrides leave the standard search
untouched. The activation-file parser here is intentionally a duplicate of
config-custody/worker-context's, not an import: each hook directory is
copied and symlinked on its own (ADR 0017), so a cross-hook import would
break the moment one hook is installed without the other.

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

# Same discovery precedence as handoff-freshness-guard/hook.py. Used only
# when no valid `handoff:` override is active (see _find_handoff).
CANDIDATE_PATHS = [
    "_meta/HANDOFF.md",
    "HANDOFF.md",
    ".claude/HANDOFF.md",
]

# Sources that count as a genuine cold start.
SURFACE_SOURCES = {"startup", "clear"}

# ---------------------------------------------------------------------------
# Per-project override (.claude/atelier.local.md `handoff:` key)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
HANDOFF_KEY = "handoff"

# A frontmatter block is a few dozen lines; anything larger is not an
# activation file and reading it into a hook that runs on every session
# start is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024


def _resolve_project_dir(cwd):
    """CLAUDE_PROJECT_DIR env anchor first, else the resolved payload cwd —
    same anchor config-custody/worker-context use to locate
    .claude/atelier.local.md, and the same one this hook's own log path
    already prefers (see _resolve_log_path)."""
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    try:
        return os.path.abspath(base)
    except Exception:
        return cwd


def _resolve_activation_path(project_dir):
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return override
    return os.path.join(project_dir, ACTIVATION_RELPATH)


def _unquote(value):
    """Strip surrounding quotes and any trailing YAML comment.

    Quote handling comes first: `handoff: "docs/HANDOFF.md"  # note` must
    yield `docs/HANDOFF.md`, while a quoted path is allowed to contain a `#`.
    """
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        close = value.find(quote, 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at].rstrip()
    return value


def _parse_handoff_override(text):
    """Return the `handoff:` key's value from a YAML frontmatter block, or
    None if absent/blank/unparseable.

    Deliberately narrow (mirrors worker-context's `enforce`-only parser):
    understands one scalar key, on an unindented top-level line, and
    ignores everything else. Anything it cannot make sense of — no fences,
    no closing fence — returns None, so a malformed activation file behaves
    exactly as if the key were absent (fall back to the standard search).
    """
    lines = text.splitlines()

    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip("﻿").strip()
        if not stripped:
            continue
        if stripped == "---":
            start = index + 1
        break  # the first non-blank line must be the opening fence
    if start is None:
        return None

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return None

    value = None
    for line in lines[start:end]:
        if not line.strip() or line[:1].isspace() or line.strip().startswith("#"):
            continue
        item = line.strip()
        colon = item.find(":")
        if colon == -1:
            continue
        if item[:colon].strip().lower() == HANDOFF_KEY:
            value = _unquote(item[colon + 1:])
    return value or None


def _load_handoff_override(project_dir):
    """Read the activation file. Any trouble at all -> None (no override)."""
    path = _resolve_activation_path(project_dir)
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return None
    try:
        return _parse_handoff_override(text)
    except Exception:
        return None


def _resolve_override_path(value, project_dir):
    """Validated absolute path for an override value, confined to
    project_dir, or None when value is blank or escapes the project root.

    An escaping value is treated as if no override were set (same fail-open
    posture as an absent key) — this hook must never read outside its
    project's jurisdiction on an untrusted or misconfigured path.
    """
    if not value:
        return None
    try:
        abs_path = value if os.path.isabs(value) else os.path.join(project_dir, value)
        abs_path = os.path.normpath(abs_path)
        relpath = os.path.relpath(abs_path, project_dir)
    except Exception:
        return None
    if relpath.split(os.sep)[0] == "..":
        return None
    return abs_path


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
    """HANDOFF_SURFACER_LOG_PATH override, else <project-root>/logs/handoff-surfacer.jsonl.

    The project root is CLAUDE_PROJECT_DIR (set by Claude Code for hook
    commands), so the hook is portable across any project that installs the
    atelier plugin, not just this one. The payload cwd is a last resort
    only — anchoring on cwd scatters stray logs/ dirs into whatever
    subdirectory an agent happens to be running in.
    """
    override = os.environ.get("HANDOFF_SURFACER_LOG_PATH")
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
# Handoff discovery + head excerpt
# ---------------------------------------------------------------------------

def _find_handoff(cwd):
    """Return (path, relpath) for the active handoff file, else (None, None).

    A valid, in-project-root `handoff:` override in .claude/atelier.local.md
    is authoritative — found or not, it is the only location checked, and
    the standard candidate search below never runs. Absent, unparseable, or
    out-of-root overrides fall back unchanged to the documented precedence
    order.
    """
    project_dir = _resolve_project_dir(cwd)
    override_path = _resolve_override_path(_load_handoff_override(project_dir), project_dir)
    if override_path is not None:
        if os.path.isfile(override_path):
            relpath = os.path.relpath(override_path, project_dir).replace(os.sep, "/")
            return override_path, relpath
        return None, None

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
            "systemMessage": f"atelier: surfaced project handoff ({relpath}).",
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
                _resolve_log_path(None),
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
