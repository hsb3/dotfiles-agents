#!/usr/bin/env python3
"""
config-custody — PreToolUse hook.

Makes a project's ownership map machine-readable: files listed as `protected:`
in `.claude/atelier.local.md` are read-only to SUBAGENTS. The main session is
never restricted — the orchestrator owns the gate and may edit it freely.

Motivation (the source lab's finding F2, the gate is orchestrator property): a
worker that can edit the config defining its own acceptance can always make its
brief pass, and prose alone cannot stop that. Doctrine in an agent file is a
request; a PreToolUse deny is the same rule stated where the tool call happens.
The deny text is written to be read by the worker that hits it: it names the
escalation (stop and report) rather than just refusing.

Purely a guardrail: it fails open on every error path, never edits anything, and
writes nothing outside its configured ledger path.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreToolUse):
  - stdin JSON fields consumed: session_id, cwd, tool_name, tool_input
    (file_path / notebook_path), agent_id and agent_type (present ONLY when the
    hook fires inside a subagent — absence means main session, which is always
    allowed).
  - stdout JSON (exit 0), on a deny only:
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": "..."}}
    Every other path prints nothing.
  - exit 0 always. An exception must never emit a deny.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import fnmatch
import json
import os
import sys
import traceback

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
LOG_STREAM = "config-custody"
LOG_PATH_ENV = "ATELIER_CUSTODY_LOG_PATH"

# A frontmatter block is a few dozen lines; anything larger is not an activation
# file and reading it into a hook that runs on every edit is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024

OFF = "off"
ADVISORY = "advisory"
STRICT = "strict"
ACTIVE_MODES = (ADVISORY, STRICT)

DENY_REASON_TEMPLATE = (
    "atelier config-custody: '{path}' matches protected pattern '{pattern}' in "
    ".claude/atelier.local.md — this file defines acceptance and is read-only to "
    "subagents. If the gate it defines is unsatisfiable, stop and report that in your "
    "handoff note; if your brief explicitly grants you ownership of this file, report "
    "the conflict — the orchestrating session can lift the pattern for this wave or "
    "make the edit itself. Do not route around this via shell."
)


def _resolve_project_dir(payload_cwd):
    """Env anchor first, else the payload cwd, else None.

    CLAUDE_PROJECT_DIR is set by Claude Code for hook commands. With neither it
    nor a payload cwd there is no jurisdiction to enforce and no safe place to
    write a ledger, so the hook goes inert rather than guessing from the process
    cwd.
    """
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
# ---------------------------------------------------------------------------

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


def _unquote(value):
    """Strip surrounding quotes and any trailing YAML comment.

    Quote handling comes first: `enforce: "strict"  # armed` must yield `strict`,
    while a quoted pattern is allowed to contain a `#`.
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


def _split_inline_list(raw):
    """`["a", "b"]` / `[a, b]` -> ["a", "b"]. Commas inside quotes are respected."""
    inner = raw.strip()[1:-1]
    items = []
    buf = []
    quote = None
    for ch in inner:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch == ",":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return [item for item in items if item]


def _parse_frontmatter(text):
    """Return (mode, patterns) from a YAML frontmatter block.

    Deliberately narrow: it understands one scalar key (`enforce`) and one
    sequence key (`protected`), in block or inline form, and ignores everything
    else. Anything it cannot make sense of — no fences, no closing fence, an
    unknown `enforce` value — returns ("off", []), so a malformed activation
    file disables enforcement instead of half-enforcing it.
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
        return OFF, []

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return OFF, []

    mode = OFF
    patterns = []
    in_protected = False
    for line in lines[start:end]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indented = line[:1].isspace()
        item = line.strip()

        if in_protected and item.startswith("- "):
            value = _unquote(item[2:])
            if value:
                patterns.append(value)
            continue
        if in_protected and item == "-":
            continue
        if indented:
            continue  # nested mapping under some other key: not ours

        colon = item.find(":")
        if colon == -1:
            continue
        key = item[:colon].strip().lower()
        raw_value = item[colon + 1:].strip()
        in_protected = False

        if key == "enforce":
            candidate = _unquote(raw_value).lower()
            mode = candidate if candidate in ACTIVE_MODES else OFF
        elif key == "protected":
            if raw_value.startswith("[") and raw_value.endswith("]"):
                patterns.extend(_split_inline_list(raw_value))
            elif not raw_value:
                in_protected = True

    return mode, patterns


def _load_activation(project_dir):
    """Read the activation file. Any trouble at all -> ("off", [])."""
    path = _resolve_activation_path(project_dir)
    if not path:
        return OFF, []
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return OFF, []
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return OFF, []
    try:
        return _parse_frontmatter(text)
    except Exception:
        return OFF, []


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------

def _normalize(raw_path, project_dir):
    """Return (abs_path, relpath) or (None, None) when out of jurisdiction.

    A relative tool path is anchored on the project dir, not on the hook
    process's cwd: the hook runs wherever Claude Code launched it, and resolving
    against that would let the same edit be inside or outside jurisdiction
    depending on an unrelated `cd`. Matching is lexical (normpath, not realpath)
    — a symlink aimed at a protected file is not caught. This is a guardrail on
    honest tool calls, not a sandbox.
    """
    try:
        abs_path = raw_path if os.path.isabs(raw_path) else os.path.join(project_dir, raw_path)
        abs_path = os.path.normpath(abs_path)
        relpath = os.path.relpath(abs_path, project_dir)
    except Exception:
        return None, None
    first = relpath.split(os.sep)[0]
    if first == "..":
        return None, None
    return abs_path, relpath


def _first_match(relpath, abs_path, patterns):
    """First protected pattern matching either form of the path, else None.

    fnmatch, never regex: patterns in the activation file are written by hand as
    globs. Note that fnmatch's `*` crosses `/`, so `configs/*` protects the whole
    subtree, not just its direct children.
    """
    rel_posix = relpath.replace(os.sep, "/")
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            continue
        try:
            if fnmatch.fnmatch(rel_posix, pattern) or fnmatch.fnmatch(abs_path, pattern):
                return pattern
        except Exception:
            continue
    return None


def main():
    log = None
    payload = None
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        # No agent_id means the main session: the orchestrator owns config and is
        # never restricted by this hook.
        if not payload.get("agent_id"):
            sys.exit(0)

        project_dir = _resolve_project_dir(payload.get("cwd"))
        if not project_dir:
            sys.exit(0)

        mode, patterns = _load_activation(project_dir)
        if mode not in ACTIVE_MODES or not patterns:
            sys.exit(0)

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)
        raw_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not raw_path or not isinstance(raw_path, str):
            sys.exit(0)

        abs_path, relpath = _normalize(raw_path, project_dir)
        if relpath is None:
            sys.exit(0)  # outside the project: out of jurisdiction

        pattern = _first_match(relpath, abs_path, patterns)
        if not pattern:
            sys.exit(0)

        log = agentlog.make_logger(LOG_STREAM, LOG_PATH_ENV, project_dir)
        rel_posix = relpath.replace(os.sep, "/")
        denied = mode == STRICT

        if denied:
            _emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": DENY_REASON_TEMPLATE.format(
                        path=rel_posix, pattern=pattern,
                    ),
                },
            })

        # Only matches are logged — one row per would-be or actual denial, never
        # one per edit. In advisory mode a row is a would-be denial: the evidence
        # a project graduates to strict on.
        log({
            "session_id": payload.get("session_id"),
            "agent_type": payload.get("agent_type"),
            "tool_name": payload.get("tool_name"),
            "path": rel_posix,
            "pattern": pattern,
            "mode": mode,
            "denied": denied,
        })
        sys.exit(0)

    except Exception as e:
        try:
            # The logger is bound only after the activation file armed the
            # hook and a pattern matched. A project that never activated custody
            # must stay silent, so pre-activation failures are not logged.
            if log:
                if not isinstance(payload, dict):
                    payload = {}
                log({
                    "session_id": payload.get("session_id"),
                    "denied": False,
                    "error": "{0}: {1}".format(type(e).__name__, e),
                    "traceback": traceback.format_exc(limit=3),
                })
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
