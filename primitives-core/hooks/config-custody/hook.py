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
import subprocess
import sys
import traceback

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)
import atelier_local  # noqa: E402

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
# `git show HEAD:<path>` takes a repo-relative path with forward slashes.
ACTIVATION_GIT_PATH = ".claude/atelier.local.md"
LOG_STREAM = "config-custody"
LOG_PATH_ENV = "ATELIER_CUSTODY_LOG_PATH"

# A frontmatter block is a few dozen lines; anything larger is not an activation
# file and reading it into a hook that runs on every edit is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024

# Both git reads can run on one call, so the pair has to fit inside the hook
# timeout `config.json` declares (10s) with room for interpreter startup.
GIT_TIMEOUT = 3

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


def _main_checkout(path):
    """A linked worktree resolves to its main checkout; anything else returns
    `path` unchanged.

    `git rev-parse --git-common-dir` names the shared git dir: a bare `.git`
    from a main checkout's root, a path ending in `/.git` from anywhere inside
    a linked worktree. Every other answer — no git binary, not a repository, a
    bare repo or a submodule whose common dir is not `<root>/.git` — is treated
    as "not a linked worktree", so a machine without git behaves exactly as it
    did before.

    Duplicated across the atelier hooks by design: each hook dir is copied and
    symlinked on its own, so a shared module would be a cross-hook import that
    breaks the moment one of them is installed without the other.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--git-common-dir"],
            capture_output=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return path
    if proc.returncode != 0:
        return path
    common = proc.stdout.decode("utf-8", "replace").strip()
    if not common or common == ".git":
        return path  # a main checkout's own root
    if not os.path.isabs(common):
        common = os.path.join(path, common)
    common = os.path.abspath(common)
    if os.path.basename(common) != ".git":
        return path
    return os.path.dirname(common)


def _resolve_activation_path(project_dir):
    """The activation file this hook reads.

    ATELIER_ACTIVATION_FILE wins outright — an explicit override is never
    re-resolved. Otherwise it is the project dir's own copy, falling back to
    the main checkout's copy when no file sits at the direct path and the
    project dir is a linked worktree: custody follows the checkout that armed
    it, so a worker handed its own worktree is not un-governed just because a
    gitignored config did not travel. The fallback is lazy — it costs a `git`
    subprocess only on the miss, and an activation file that IS present in the
    worktree (a tracked one, at its committed version) still wins.
    """
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return override
    if not project_dir:
        return None
    path = os.path.join(project_dir, ACTIVATION_RELPATH)
    if os.path.isfile(path):
        return path
    main_dir = _main_checkout(project_dir)
    if main_dir == project_dir:
        return path
    return os.path.join(main_dir, ACTIVATION_RELPATH)


# ---------------------------------------------------------------------------
# Activation file — sourced here, parsed by `_lib/atelier_local.py`
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


def _policy(text):
    """(mode, patterns) from an activation file's frontmatter.

    Deliberately narrow: one scalar key (`enforce`) and one sequence key
    (`protected`). Anything it cannot make sense of — no fences, an unknown
    `enforce` value, a `protected` that is not a sequence — leaves ("off", []),
    so a malformed activation file disables enforcement instead of half-enforcing
    it.
    """
    enforce = atelier_local.parse_key(text, "enforce")
    mode = enforce.lower() if isinstance(enforce, str) else OFF
    patterns = atelier_local.parse_key(text, "protected")
    return (mode if mode in ACTIVE_MODES else OFF,
            patterns if isinstance(patterns, list) else [])


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
        return _policy(text)
    except Exception:
        return OFF, []


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------

def _worktree_root(abs_path, project_dir):
    """Innermost linked-worktree root containing `abs_path`, or None.

    A linked worktree's `.git` is a FILE pointing at the shared git dir, where
    an ordinary checkout's is a directory — the same distinction `_is_git_repo`
    relies on elsewhere. Walking up from the edited file to the first such file
    finds the tree that file actually lives in, innermost first, which is the
    right answer when worktrees are nested.

    The walk stops AT `project_dir`, inclusive, so a worktree outside the
    project can never become a jurisdiction while the common case of the project
    dir being the worktree itself is still found. Whatever the `.git` file points
    at is trusted: this is a guardrail, not a sandbox.
    """
    prefix = project_dir + os.sep
    current = os.path.dirname(abs_path)
    while current == project_dir or current.startswith(prefix):
        if os.path.isfile(os.path.join(current, ".git")):
            return current
        if current == project_dir:
            break
        current = os.path.dirname(current)
    return None


def _committed_activation(worktree_root):
    """The worktree's activation file as committed at HEAD, or None.

    None means "this tree has no committed copy" and every caller must read it
    that way: an untracked file, an unborn HEAD, a missing `git`, and a timeout
    all land here, and all of them have to fall back to the upstream policy
    rather than to bytes the worker can rewrite.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", worktree_root, "show", "HEAD:" + ACTIVATION_GIT_PATH],
            capture_output=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or len(proc.stdout) > ACTIVATION_MAX_BYTES:
        return None
    return proc.stdout.decode("utf-8", "replace")


def _load_policy(abs_path, project_dir):
    """(mode, patterns) for the tree the edited file lives in.

    A linked worktree with its own tracked activation file is governed by the
    version committed on its branch: policy inside a worktree belongs to that
    branch, where it is diffable and reviewable, and reading it from disk
    instead would let a worker disarm the gate with one permitted `Edit`. The
    committed copy governs even when it parses to "off" — that is the same
    tolerant-parse rule the direct path already follows.

    Everything else — no worktree, no copy, nothing committed, no git — falls
    back to `project_dir` and its main-checkout lookup. The `isfile` probe keeps
    the subprocess off the path of every tree that has no copy at all.
    """
    if os.environ.get("ATELIER_ACTIVATION_FILE"):
        return _load_activation(project_dir)
    root = _worktree_root(abs_path, project_dir)
    if root and os.path.isfile(os.path.join(root, ACTIVATION_RELPATH)):
        text = _committed_activation(root)
        if text is not None:
            try:
                return _policy(text)
            except Exception:
                return OFF, []
    return _load_activation(project_dir)


def _normalize(raw_path, project_dir):
    """Return (abs_path, relpath) or (None, None) when out of jurisdiction.

    A relative tool path is anchored on the project dir, not on the hook
    process's cwd: the hook runs wherever Claude Code launched it, and resolving
    against that would let the same edit be inside or outside jurisdiction
    depending on an unrelated `cd`. Matching is lexical (normpath, not realpath)
    — a symlink aimed at a protected file is not caught. This is a guardrail on
    honest tool calls, not a sandbox.

    Patterns are relative to the tree the edited file lives in, which is not
    always the project dir. Claude Code sets CLAUDE_PROJECT_DIR on the hook
    process to the MAIN checkout even when the worker was given a linked
    worktree, so relativizing everything against it turns every path an
    isolated worker touches into `.claude/worktrees/agent-<id>/...` — a shape
    no project-relative pattern matches, which silently exempts exactly the
    workers custody is aimed at. Jurisdiction is the worktree; which copy of the
    activation file supplies the patterns is `_load_policy`'s separate question.
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
    try:
        root = _worktree_root(abs_path, project_dir)
        if root is not None:
            relpath = os.path.relpath(abs_path, root)
    except Exception:
        pass  # fail open to the project-relative form
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

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)
        raw_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not raw_path or not isinstance(raw_path, str):
            sys.exit(0)

        abs_path, relpath = _normalize(raw_path, project_dir)
        if relpath is None:
            sys.exit(0)  # outside the project: out of jurisdiction

        # The path is resolved first because the policy that governs the edit is
        # the one belonging to the tree the edited file lives in.
        mode, patterns = _load_policy(abs_path, project_dir)
        if mode not in ACTIVE_MODES or not patterns:
            sys.exit(0)

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
