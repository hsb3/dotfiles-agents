#!/usr/bin/env python3
"""
plugin-feedback-worker — SubagentStart hook.

Tells every dispatched worker the tier rule for reporting a plugin defect, so the
rule arrives with the worker instead of depending on the dispatching session
restating it in each brief.

The offer is scoped to plugins from this marketplace, because that is where the
reporter files: it resolves its target from the reporting plugin's own manifest, so a
report about a plugin from anywhere else would land in the wrong project's tracker.

The tier rule (ratified doctrine, not this hook's interpretation):
  - a worker MAY file a bug directly. The bar is objective and needs no judgment —
    observed behavior contradicts the plugin's own stated contract;
  - a worker MUST NOT file a feature request. A feature request needs a why tied to a
    real limitation, which is a judgment call its dispatcher is positioned to make, so
    the worker drafts one and hands it up.
The primary session may file either; that is the companion hook's text
(plugin-feedback-session, SessionStart).

Stateless: no ledger, no state file, writes nothing anywhere. Fails open on every
error path.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SubagentStart):
  - stdin JSON fields documented by the event: session_id, hook_event_name, agent_id,
    agent_type, cwd, permission_mode. None are consumed — the reminder is constant.
    SubagentStart carries no `source`, so unlike the session hook there is no
    cold-start gate: every dispatch is a fresh worker that was told nothing.
  - stdout JSON (exit 0), when active:
      {"hookSpecificOutput": {"hookEventName": "SubagentStart",
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

# The reporter ships in the companion hook's directory. Both hooks resolve the same
# path with the same few lines rather than importing across hook dirs: each hook
# directory is copied and symlinked on its own, so a cross-hook import would break
# the moment one is installed without the other. The two ship together in one plugin,
# which is what makes the shared path safe where an import would not be.
REPORTER_DIR = "plugin-feedback-session"
REPORTER_FILE = "report_issue.py"
REPORTER_FALLBACK = "${CLAUDE_PLUGIN_ROOT}/hooks/" + REPORTER_DIR + "/" + REPORTER_FILE

# Scoped to this marketplace on purpose. The reporter resolves its target from the
# REPORTING plugin's manifest, so an offer covering "any installed plugin" would send a
# report about someone else's plugin into this marketplace's tracker.
REMINDER = (
    "plugin-feedback (worker tier): you MAY file a bug directly about a plugin from this "
    "marketplace when its observed behavior contradicts the plugin's own stated contract — "
    "run `python3 {reporter} --help`, which prints the target repo (this marketplace's own) "
    "before filing. You MUST NOT file a feature request: draft one with `--draft` and hand "
    "it to your dispatcher, since the why has to be tied to a real limitation. A plugin from "
    "elsewhere goes to that project's own tracker, not through this reporter."
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

        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": REMINDER.format(reporter=_reporter_path()),
            },
        })
        sys.exit(0)

    except Exception:
        # Fail open and silent: a worker that was never told the tier rule is the
        # normal case this degrades to, and a broken nudge must never keep a subagent
        # from starting.
        sys.exit(0)


if __name__ == "__main__":
    main()
