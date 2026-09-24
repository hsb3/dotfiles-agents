#!/usr/bin/env python3
"""
worktree-isolation — PreToolUse hook.

Makes filesystem isolation a project property instead of a per-dispatch
courtesy: when a project opts in, an Agent call that would put a WRITING worker
in the orchestrator's own checkout is rewritten to carry
`isolation: "worktree"`, so the worker gets its own git worktree.

Motivation: `builder` and `manager` edit files, and by default a subagent
inherits the parent session's working directory. Two writers in one wave — or
one writer alongside a strategist who is mid-edit — share an index and a working
tree, and the resulting cross-contamination is invisible until integration. The
delegation skill has always ASKED for isolation on write-waves; a request in
prose is honoured only when the dispatching session remembers it. Stated here,
it holds for every dispatch.

Why not the whole roster: a git worktree is a clean checkout of a ref, so
UNCOMMITTED and untracked files in the parent checkout do not exist inside it.
A `scout` sent to inventory the working diff, or a `reviewer` sent to re-derive
a claim from files the session has not committed yet, would silently read a
different tree and report on nothing. Read-only roles therefore stay in the
parent checkout, which is also where they are cheapest. `fork` is excluded for
a second reason: it inherits the conversation, so its premise is continuity with
the caller.

Activated by the selected project `atelier.local.md`: `isolate: writers` arms the
built-in writer set, `isolate:` as a list arms exactly the named agent types.
Anything else stays silent.

No state file, and no writes into the project. The one thing it does record
is its own decisions, to the shared `worktree-isolation` stream (see
`_lib/agentlog.py`): a hook that silently rewrites a dispatch is otherwise
invisible to anyone asking why a worker landed in a different checkout.

The ledger starts at activation, not before. Once a project has armed the
hook, every Agent dispatch it sees produces exactly one row — `isolated: true`
for a rewrite, `isolated: false` with a `reason` for one it leaves alone. A
project that has not armed it writes no decision rows, which is the same rule
config-custody follows: an un-adopted hook must stay silent rather than open
a ledger nobody asked for. The cheap pre-activation exits (wrong tool, an
isolation already set, a `cwd` already present) are likewise unlogged — they
are reached before the activation file is read.

The one exception is the error path, which logs regardless of activation. It
has to: it is reached when the hook could not get far enough to know whether
the project armed it, and a hook crashing on every dispatch while staying
silent is precisely the outage this ledger exists to make visible.

Fails open on every error path — a hook that cannot decide must let the
dispatch through unchanged, never block it.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide
Behaviour verified by live probe against Claude Code 2.1.220: a PreToolUse hook
matching tool_name `Agent` receives the dispatch and `updatedInput` is honoured
(the subagent landed in `.claude/worktrees/agent-<id>`).

Contract (PreToolUse, matcher `Agent`):
  - stdin JSON fields consumed: cwd, tool_name, tool_input (subagent_type,
    isolation, cwd).
  - stdout JSON (exit 0), on a rewrite only:
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "updatedInput": {...tool_input, isolation: worktree}},
       "systemMessage": "..."}
    Every other path prints nothing.
  - exit 0 always. This hook never emits a permissionDecision: forcing a
    worktree is a correction, not a refusal.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

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
import codex_workers  # noqa: E402
import agentlog  # noqa: E402  (path must be primed before this import)
import atelier_local  # noqa: E402

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------


# A frontmatter block is a few dozen lines; anything larger is not an activation
# file and reading it into a hook that runs on every dispatch is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024

TOOL_NAME = "Agent"
LOG_STREAM = "worktree-isolation"
LOG_PATH_ENV = "WORKTREE_ISOLATION_LOG_PATH"
WORKTREE = "worktree"

OFF = "off"
WRITERS = "writers"

# The built-in writer set, armed by `isolate: writers`. These are the roles whose
# briefs hand them Edit/Write: isolating them is the point of the hook.
DEFAULT_WRITERS = ("builder", "manager", "general-purpose")

# Never rewritten, even when named explicitly in an `isolate:` list. The
# read-only roles need the live working tree (see the module docstring), and a
# fork's premise is that it continues the caller's context.
NEVER_ISOLATE = frozenset({
    "scout",
    "reviewer",
    "explore",
    "plan",
    "fork",
})

# An omitted subagent_type resolves to the general-purpose agent, which carries
# the full tool set — so absence is treated as a writer, not as unknown.
DEFAULT_AGENT_TYPE = "general-purpose"

NOTICE_TEMPLATE = (
    "atelier worktree-isolation: '{agent_type}' dispatched with isolation:worktree "
    "(isolate: {mode} in the selected atelier.local.md). It gets its own checkout, so "
    "uncommitted work in this tree is NOT visible to it."
)

# Appended when the DISPATCHER is itself standing in a linked worktree. Nesting
# is the intended outcome, not a misconfiguration: two concurrent writers
# sharing one index is the hazard this hook exists to prevent, and the
# dispatcher being one level down does not make it safe. What nesting actually
# costs is integration ergonomics, so the dispatcher is handed the integrate
# step here — at dispatch — instead of meeting a pile of stray branches at the
# end of the wave.
#
# Two separate commands, read then run, rather than one shell pipeline: the
# reader's shell is zsh, which does not word-split an unquoted expansion, so a
# `picks=$(...)` one-liner passes every SHA as ONE bad revision. See the README
# for why the range form `HEAD..<branch>` cannot be repeated either.
NESTED_CLAUSE = (
    " You are standing in a linked worktree yourself, so this one is NESTED under it "
    "on its own branch — intended, not a misconfiguration. Its checkout is a separate "
    "tree from yours: brief its owned files as paths relative to its own checkout, not "
    "absolute paths into yours, and do not plan on it sharing your worktree under a "
    "disjoint file map — that is not available under isolate: writers. To integrate "
    "when it reports: `git worktree list` for its path and branch, then `git cherry HEAD "
    "<branch>` and READ it — `+` lines are commits you have not picked yet, `-` "
    "lines are already in — then `git cherry-pick <the + SHAs>` if there are any. "
    "Repeat that pair each round; it never re-applies. Before cleanup, confirm the worker "
    "is complete and no longer live; inspect tracked, untracked, and ignored files; prove every "
    "commit merged, patch-equivalent, superseded, or preserved on a reviewed remote branch; and "
    "preserve uncommitted, untracked, and ignored work plus durable evidence. Only then "
    "`git worktree remove <path> && git branch -D <branch>` "
    "to clean up."
)


def _resolve_project_dir(payload_cwd):
    """Env anchor first, else the payload cwd, else None (hook goes inert).

    CLAUDE_PROJECT_DIR is set by Claude Code for hook commands. With neither it
    nor a payload cwd there is nothing to anchor the activation file or the git
    check on, so the hook declines to guess from the process cwd.
    """
    base = os.environ.get("CLAUDE_PROJECT_DIR") or payload_cwd
    if not base or not isinstance(base, str):
        return None
    try:
        return os.path.abspath(base)
    except Exception:
        return None


_resolve_activation_path = atelier_local.activation_path


def _in_linked_worktree(path):
    """True when `path` sits inside a LINKED worktree rather than a main checkout.

    `--git-dir` and `--git-common-dir` name the same directory in a main
    checkout and differ (`<common>/worktrees/<name>` vs `<common>`) inside a
    linked one, so comparing them answers the question from anywhere in the
    tree. The common dir's literal value cannot: it is `.git` only at a main
    checkout's root and a relative `../../.git` from any subdirectory of the
    same checkout, so a string test would call an ordinary subdirectory a
    worktree. Both sides are realpath'd because git returns one of them already
    resolved — an unresolved compare mismatches wherever the path runs through
    a symlink, and a mismatch reads as "linked".

    Anything it cannot answer is False: no git binary, not a repository, or a
    bare repo or submodule whose common dir is not `<root>/.git`.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--git-dir", "--git-common-dir"],
            env=codex_workers.clean_git_env() if codex_workers.is_codex({}) else None,
            capture_output=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    lines = [ln.strip() for ln in
             proc.stdout.decode("utf-8", "replace").splitlines() if ln.strip()]
    if len(lines) != 2:
        return False
    git_dir, common = (os.path.realpath(os.path.join(path, ln)) for ln in lines)
    if os.path.basename(common) != ".git":
        return False
    return git_dir != common


def _is_git_repo(project_dir):
    """Walk up looking for a `.git` entry.

    Forcing isolation outside a git repository is not a no-op: Claude Code
    raises `Cannot create agent worktree: not in a git repository`, which would
    turn this hook from a guardrail into a hard failure on every dispatch. The
    check is a filesystem walk rather than a `git` subprocess so it stays fast
    and dependency-free; `.git` may be a directory (normal clone) or a file (a
    worktree or submodule), so both count.
    """
    if not project_dir:
        return False
    try:
        current = project_dir
        while True:
            if os.path.exists(os.path.join(current, ".git")):
                return True
            parent = os.path.dirname(current)
            if parent == current:
                return False
            current = parent
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Activation file — sourced here, parsed by `_lib/atelier_local.py`
# ---------------------------------------------------------------------------

def _isolation(text):
    """(mode, agent_types) from an activation file's frontmatter.

    `isolate` carries both forms on one key, mirroring how `protected` is
    written next to it:

        isolate: writers        -> (WRITERS, DEFAULT_WRITERS)
        isolate: [builder, x]   -> (WRITERS, ("builder", "x"))
        isolate:                -> (WRITERS, ("builder", "x"))
          - builder
          - x

    Anything else — an unknown scalar, an empty list, a mapping where a list
    belongs — returns (OFF, ()), so a malformed activation file leaves
    dispatches untouched instead of half-arming. A list names its own set, so an
    empty one is an empty intent rather than a request for the built-ins.
    """
    value = atelier_local.parse_key(text, "isolate")
    if isinstance(value, list):
        return (WRITERS, tuple(value)) if value else (OFF, ())
    if isinstance(value, str) and value.lower() == WRITERS:
        return WRITERS, DEFAULT_WRITERS
    return OFF, ()


def _load_activation(project_dir):
    """Read the activation file. Any trouble at all -> (OFF, ())."""
    path = _resolve_activation_path(project_dir)
    if not path:
        return OFF, ()
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return OFF, ()
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return OFF, ()
    try:
        return _isolation(text)
    except Exception:
        return OFF, ()


# ---------------------------------------------------------------------------
# Agent-type matching
# ---------------------------------------------------------------------------

def _normalize(agent_type):
    """`atelier:builder` -> `builder`; case-folded.

    A plugin-namespaced dispatch names the same role as its bare form, and the
    activation file should not have to know which marketplace an agent shipped
    from.
    """
    if not isinstance(agent_type, str):
        return ""
    return agent_type.strip().rsplit(":", 1)[-1].strip().lower()


def _should_isolate(agent_type, armed_types):
    normalized = _normalize(agent_type)
    if not normalized or normalized in NEVER_ISOLATE:
        return False
    return any(_normalize(candidate) == normalized for candidate in armed_types)


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


def _codex(payload):
    if not payload.get("agent_id"):
        return
    try:
        package = os.environ.get('ATELIER_ROLE_PLUGIN_ROOT')
        if package:
            import codex_roles
            role = payload.get('agent_type')
            if role not in codex_roles.role_names(package):
                return
            allowed = codex_roles.role_tools(role, package)
            tool = payload.get('tool_name')
            if (tool in codex_workers.CONTROL_TOOLS and 'Agent' not in allowed
                    or tool == 'apply_patch' and not allowed.intersection({'Edit', 'Write'})):
                _emit(codex_workers.deny('Tool is outside the canonical role authority: ' + str(tool)))
            return
        if not codex_workers.active(payload):
            return
        if payload.get("hook_event_name") == "SubagentStart":
            record = codex_workers.ensure_worker(payload)
            if record["worktree"]:
                _emit({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                       "additionalContext": "Atelier worker checkout: " + record["worktree"]
                       + ". Relative shell and patch operations route here; native cwd metadata is inherited."}})
        elif payload.get("hook_event_name") == "PreToolUse":
            updated = codex_workers.route_tool(payload)
            if updated != payload.get("tool_input"):
                _emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                       "permissionDecision": "allow", "updatedInput": updated}})
    except Exception as exc:
        if payload.get("hook_event_name") == "PreToolUse":
            _emit(codex_workers.deny(exc))
        else:
            _emit({"hookSpecificOutput": {"hookEventName": "SubagentStart",
                   "additionalContext": "Atelier worker registration failed; tools will be denied: " + str(exc)}})


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        if codex_workers.is_codex(payload):
            _codex(payload)
            return

        if payload.get("tool_name") != TOOL_NAME:
            sys.exit(0)

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)

        # An explicit isolation already answers the question — including
        # `remote`, which this hook must not downgrade.
        if tool_input.get("isolation"):
            sys.exit(0)

        # `cwd` is documented as mutually exclusive with isolation:"worktree";
        # adding one beside the other would fail schema validation and drop the
        # rewrite anyway.
        if tool_input.get("cwd"):
            sys.exit(0)

        project_dir = _resolve_project_dir(payload.get("cwd"))
        if not project_dir:
            sys.exit(0)

        mode, armed_types = _load_activation(project_dir)
        if mode == OFF:
            sys.exit(0)

        # Armed from here on, so every remaining path is one ledger row.
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(payload.get("cwd")),
        )
        agent_type = tool_input.get("subagent_type") or DEFAULT_AGENT_TYPE
        row = {
            "session_id": payload.get("session_id"),
            "agent_type": agent_type,
            "mode": mode,
        }

        if not _should_isolate(agent_type, armed_types):
            log(dict(row, isolated=False, reason="agent type not armed"))
            sys.exit(0)

        # Checked last: the walk is the most expensive step, and every cheaper
        # inert path above has already returned.
        if not _is_git_repo(project_dir):
            log(dict(row, isolated=False, reason="project dir is not a git repo"))
            sys.exit(0)

        updated = dict(tool_input)
        updated["isolation"] = WORKTREE

        # Asked only here, on the one path that actually rewrites: it is a git
        # subprocess, and every inert exit above has already returned.
        nested = _in_linked_worktree(project_dir)
        notice = NOTICE_TEMPLATE.format(agent_type=agent_type, mode=mode)
        if nested:
            notice += NESTED_CLAUSE

        _emit({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated,
            },
            # Announced rather than silent: the rewrite moves the worker to a
            # checkout where the session's uncommitted work does not exist, and
            # a surprised reader should be able to trace that to this hook.
            "systemMessage": notice,
        })
        log(dict(row, isolated=True, reason=None, nested=nested))
        sys.exit(0)

    except Exception as e:
        # Fail open: an un-isolated worker is the pre-hook status quo and merely
        # risky, while a hook that crashes loudly on every dispatch is an
        # outage. Nothing here is worth blocking a delegation over. Silent to
        # the caller, but not to the ledger — a rewrite that should have
        # happened and did not is exactly what someone will come looking for.
        try:
            agentlog.append(LOG_STREAM, {
                "isolated": False,
                "reason": "error",
                "error": "{0}: {1}".format(type(e).__name__, e),
                "traceback": traceback.format_exc(limit=3),
            }, agentlog.resolve_project(), LOG_PATH_ENV)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
