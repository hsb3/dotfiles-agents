#!/usr/bin/env python3
"""
worker-context — SubagentStart hook.

Injects the delegation covenant into every subagent this project starts, so the
rules a worker is judged by arrive with the worker instead of depending on the
orchestrating session remembering to restate them in each brief.

Motivation (the source lab's finding F2, the gate is orchestrator property): the
doctrine that config defining acceptance is read-only lived only in an agent
definition, which a task-specific brief can quietly outrank. Stated at subagent
start, it is project policy rather than one brief's preference. The companion
hook, config-custody, enforces the same rule at the tool layer; this one makes
sure the worker was told before it is stopped.

Activated by the selected project `atelier.local.md`: `enforce: advisory` or
`strict` injects, anything else stays silent. The strict sentence is added only
under `strict`, because promising a tool-layer block that is not armed teaches a
worker to ignore the covenant.

Stateless: no ledger, no state file, writes nothing anywhere. Fails open on every
error path.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SubagentStart):
  - stdin JSON fields documented by the event: session_id, hook_event_name,
    agent_id, agent_type, cwd, permission_mode. Only `cwd` is consumed (to
    anchor the activation file when CLAUDE_PROJECT_DIR is absent).
  - stdout JSON (exit 0), when active:
      {"hookSpecificOutput": {"hookEventName": "SubagentStart",
                              "additionalContext": "..."}}
    Otherwise nothing is printed.
  - exit 0 always.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import json
import os
import subprocess
import sys

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`. That
# relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import atelier_local  # noqa: E402  (path must be primed before this import)

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------


# A frontmatter block is a few dozen lines; anything larger is not an activation
# file.
ACTIVATION_MAX_BYTES = 256 * 1024

OFF = "off"
ADVISORY = "advisory"
STRICT = "strict"
ACTIVE_MODES = (ADVISORY, STRICT)

COVENANT_HEAD = (
    "atelier worker covenant (project-enforced doctrine): (1) Configuration that "
    "defines acceptance — gates, lint, typecheck, coverage thresholds, CI, and tests "
    "you did not write — is read-only unless your brief explicitly grants ownership; "
    "an unsatisfiable gate is an escalation: stop and report, never weaken a check to "
    "pass it."
)
COVENANT_STRICT_CLAUSE = (
    " In this project, protected paths are also blocked at the tool layer; a denied "
    "edit is that escalation, not an obstacle to route around."
)
COVENANT_TAIL = (
    " (2) Work in your own worktree and commit there as you go — that branch is "
    "yours. Never push, merge, or touch any branch, worktree, or repo state outside "
    "it; integration belongs to the orchestrating session. (3) If your brief lacks "
    "an explicit owned-file list or independently checkable acceptance criteria, "
    "stop and report the gap before doing the work. (4) Verify by running commands "
    "and paste actual output; a criterion you could not verify is reported as "
    "unverified, never assumed. (5) Leave no scratch files; stop and report rather "
    "than improvising."
)


def _covenant(mode):
    if mode == STRICT:
        return COVENANT_HEAD + COVENANT_STRICT_CLAUSE + COVENANT_TAIL
    return COVENANT_HEAD + COVENANT_TAIL


def _resolve_project_dir(payload_cwd):
    """Env anchor first, else the payload cwd, else None (hook goes inert)."""
    base = (os.environ.get("CLAUDE_PROJECT_DIR") if os.environ.get("ATELIER_HARNESS") != "codex" else None) or payload_cwd
    if not base or not isinstance(base, str):
        return None
    try:
        return os.path.abspath(base)
    except Exception:
        return None


_resolve_activation_path = atelier_local.activation_path


# ---------------------------------------------------------------------------
# Activation file — sourced here, parsed by `_lib/atelier_local.py`
# ---------------------------------------------------------------------------

# `activation.py check` calls this to read `effort:`, the one key no hook parses.
_unquote = atelier_local.unquote


def _mode(text):
    """The `enforce` mode. Anything but advisory/strict — including a sequence or a
    mapping where a scalar belongs — reads as "off"."""
    value = atelier_local.parse_key(text, "enforce")
    if not isinstance(value, str):
        return OFF
    return value.lower() if value.lower() in ACTIVE_MODES else OFF


def _load_mode(project_dir):
    """Read the activation file. Any trouble at all -> "off"."""
    path = _resolve_activation_path(project_dir)
    if not path:
        return OFF
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return OFF
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return OFF
    try:
        return _mode(text)
    except Exception:
        return OFF


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


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        role_root = os.environ.get("ATELIER_ROLE_PLUGIN_ROOT")
        if os.environ.get("ATELIER_HARNESS") == "codex" and role_root:
            import codex_roles
            if codex_roles.package_id(role_root) != "atelier":
                role = payload.get("agent_type")
                if role in codex_roles.role_names(role_root):
                    _emit({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                           "additionalContext": codex_roles.role_instructions(role, role_root)}})
                return

        context = ""
        if os.environ.get("ATELIER_HARNESS") == "codex":
            import codex_workers
            import codex_roles
            record = codex_workers.ensure_worker(payload)
            if record is None:
                return
            payload = codex_workers.effective_payload(payload)
            role = codex_workers.role_name(payload.get("agent_type"))
            if role in ("builder", "manager", "scout", "reviewer", "code-reviewer"):
                context = codex_roles.role_instructions(role) + "\n\n"
            context += "Owned checkout: " + (record.get("worktree") or record["source"]) + "\n"

        mode = _load_mode(_resolve_project_dir(payload.get("cwd")))
        if mode not in ACTIVE_MODES and not context:
            sys.exit(0)

        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context + (_covenant(mode) if mode in ACTIVE_MODES else ""),
            },
        })
        sys.exit(0)

    except Exception as exc:
        if os.environ.get("ATELIER_HARNESS") == "codex":
            _emit({"continue": False, "stopReason": "atelier worker setup failed: " + str(exc)})
        # Fail open and silent: a worker briefed by its dispatcher is the normal
        # case, and a broken injection must never keep a subagent from starting.
        sys.exit(0)


if __name__ == "__main__":
    main()
