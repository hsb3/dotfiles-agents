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

Activated by `<project>/.claude/atelier.local.md`: `enforce: advisory` or
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
import sys

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")

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
    " (2) Never run mutating git (commit, push, rebase, reset, checkout, stash, tag) — "
    "the orchestrating session owns repo state. (3) If your brief lacks an explicit "
    "owned-file list or independently checkable acceptance criteria, stop and report "
    "the gap before doing the work. (4) Verify by running commands and paste actual "
    "output; a criterion you could not verify is reported as unverified, never "
    "assumed. (5) Leave no scratch files; stop and report rather than improvising."
)


def _covenant(mode):
    if mode == STRICT:
        return COVENANT_HEAD + COVENANT_STRICT_CLAUSE + COVENANT_TAIL
    return COVENANT_HEAD + COVENANT_TAIL


def _resolve_project_dir(payload_cwd):
    """Env anchor first, else the payload cwd, else None (hook goes inert)."""
    base = os.environ.get("CLAUDE_PROJECT_DIR") or payload_cwd
    if not base or not isinstance(base, str):
        return None
    try:
        return os.path.abspath(base)
    except Exception:
        return None


def _resolve_activation_path(project_dir):
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return override
    if not project_dir:
        return None
    return os.path.join(project_dir, ACTIVATION_RELPATH)


# ---------------------------------------------------------------------------
# Activation file (tolerant hand parser — stdlib only, no PyYAML)
#
# Duplicated from config-custody by design: each hook directory is copied and
# symlinked on its own, so a shared module would be a cross-hook import path
# that breaks the moment one of them is installed without the other.
# ---------------------------------------------------------------------------

def _unquote(value):
    """Strip surrounding quotes and any trailing YAML comment.

    Quote handling comes first: `enforce: "strict"  # armed` must yield `strict`.
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


def _parse_frontmatter(text):
    """Return the `enforce` mode from a YAML frontmatter block.

    Anything unparseable — no fences, no closing fence, an unknown value —
    returns "off". This hook does not need the `protected:` list; only
    config-custody acts on individual patterns.
    """
    lines = text.splitlines()

    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip("\ufeff").strip()
        if not stripped:
            continue
        if stripped == "---":
            start = index + 1
        break  # the first non-blank line must be the opening fence
    if start is None:
        return OFF

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return OFF

    mode = OFF
    for line in lines[start:end]:
        if not line.strip() or line[:1].isspace() or line.strip().startswith("#"):
            continue
        item = line.strip()
        colon = item.find(":")
        if colon == -1:
            continue
        if item[:colon].strip().lower() == "enforce":
            candidate = _unquote(item[colon + 1:]).lower()
            mode = candidate if candidate in ACTIVE_MODES else OFF
    return mode


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
        return _parse_frontmatter(text)
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

        mode = _load_mode(_resolve_project_dir(payload.get("cwd")))
        if mode not in ACTIVE_MODES:
            sys.exit(0)

        _emit({
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": _covenant(mode),
            },
        })
        sys.exit(0)

    except Exception:
        # Fail open and silent: a worker briefed by its dispatcher is the normal
        # case, and a broken injection must never keep a subagent from starting.
        sys.exit(0)


if __name__ == "__main__":
    main()
