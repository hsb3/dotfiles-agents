#!/usr/bin/env python3
"""
plugin-feedback-session — SessionStart hook.

Tells the primary session that a defect it notices in an installed plugin is
reportable, and points at the reporter that files it to a fixed template. Without
this, the knowledge that reports are welcome lives in a CLAUDE.md a session can
forget to read — and a plugin cannot ship anything into a consumer's CLAUDE.md at
all, which is the whole reason this arrives as injected context instead.

The primary session may file EITHER kind: a bug or a feature request. The tier split
is the companion hook's business (plugin-feedback-worker, SubagentStart), which tells
a dispatched worker it may file a bug but must draft a feature request instead.

Only cold starts inject ("startup"/"clear"), matching session-handoff-surfacer: on a
resume or a compact the session already carries its context, and re-nudging is pure
noise on exactly the sessions that are already long.

Stateless: no ledger, no state file, writes nothing anywhere. Fails open on every
error path.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SessionStart):
  - stdin JSON fields consumed: `source` ("startup"|"resume"|"clear"|"compact").
  - stdout JSON (exit 0), when active:
      {"hookSpecificOutput": {"hookEventName": "SessionStart",
                              "additionalContext": "..."}}
    Otherwise nothing is printed.
  - exit 0 always.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and must
stay compatible with Python 3.9.
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DISABLE_ENV = "PLUGIN_FEEDBACK_DISABLED"

# Sources that count as a genuine cold start.
SURFACE_SOURCES = {"startup", "clear"}

# The reporter ships beside this hook. Both hooks in the plugin resolve the same
# path with the same few lines rather than importing across hook dirs: each hook
# directory is copied and symlinked on its own, so a cross-hook import would break
# the moment one is installed without the other.
REPORTER_DIR = "plugin-feedback-session"
REPORTER_FILE = "report_issue.py"
REPORTER_FALLBACK = "${CLAUDE_PLUGIN_ROOT}/hooks/" + REPORTER_DIR + "/" + REPORTER_FILE

REMINDER = (
    "plugin-feedback: a defect you hit in any installed plugin is reportable from this "
    "session, and you may file either kind — a bug (observed behavior contradicts the "
    "plugin's own stated contract) or a feature request (a why tied to a limitation you "
    "actually hit, never a nice-to-have). File it with `python3 {reporter} --help`, which "
    "fixes the template and the label; do not free-hand a `gh issue create`."
)


def _reporter_path():
    """Absolute path to the reporter, or the plugin-relative pointer if it is absent.

    CLAUDE_PLUGIN_ROOT is set by Claude Code for hook commands; the sibling-derived
    path covers a hook run directly (tests, a manual invocation) where it is not.
    """
    candidates = []
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root and isinstance(root, str):
        candidates.append(os.path.join(root, "hooks", REPORTER_DIR, REPORTER_FILE))
    here = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(os.path.dirname(here), REPORTER_DIR, REPORTER_FILE))
    for candidate in candidates:
        try:
            if os.path.isfile(candidate):
                return candidate
        except Exception:
            continue
    return REPORTER_FALLBACK


def _emit(obj):
    """Print the hook's one JSON object without letting a closed stdout turn into a
    nonzero exit: flush inside the guard, and on a broken pipe point fd 1 at devnull
    so the interpreter's shutdown flush has nothing to do."""
    try:
        print(json.dumps(obj))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
        except Exception:
            pass


def main():
    try:
        if os.environ.get(DISABLE_ENV):
            sys.exit(0)

        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        if payload.get("source") not in SURFACE_SOURCES:
            sys.exit(0)

        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": REMINDER.format(reporter=_reporter_path()),
            },
        })
        sys.exit(0)

    except Exception:
        # Fail open and silent: a session that was never told reports are welcome is
        # the normal case this degrades to, and a broken nudge must never keep a
        # session from starting.
        sys.exit(0)


if __name__ == "__main__":
    main()
