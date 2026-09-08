#!/usr/bin/env python3
"""
live-worker-git-guard — PreToolUse hook.

Denies a MUTATING git command while this session still has delegations it
started and has not seen settle. The working tree is shared with them: a commit
captures their half-applied edits as if they were finished work, and a
pull/checkout/stash/reset takes their uncommitted files off disk underneath a
process that has no idea it happened.

Both halves were observed, neither needed bad judgement. A root session polling
for a green suite committed a tree a builder had temporarily sabotaged. A
routine post-merge `git checkout dev && git pull --ff-only` autostashed five
uncommitted files out of the tree while a manager was live — `Created autostash`
/ `Applied autostash.` reads identically whether or not it raced, so the loss
window leaves no artifact to check afterwards. Prose already told both sessions
to wait; what was missing was anything that noticed.

Read-only git is never touched — `status`, `diff`, `log`, `show`, `branch`,
`rev-list`, `rev-parse`, `ls-files`, `fetch` are how a session orients, and a
guard that made orientation expensive would be turned off.

Scoped to ONE working tree. The pending set is keyed on the session's
transcript, which says nothing about where a command points, and a session can
hold workers in its own tree while a call runs in a checkout of a different
repo entirely — those workers are unreachable from there. So the tree targeted
(`git rev-parse --show-toplevel` from its cwd, moved by any `-C`) is compared
against the tree the session's non-isolated workers occupy (the same
resolution from CLAUDE_PROJECT_DIR, which Claude Code sets on the hook process
to the session's main checkout). Different trees, no block. `--show-toplevel`
rather than `--git-common-dir` because the hazard is a shared WORKING TREE: a
sibling linked worktree of the same repository has its own index and its own
files, and a commit or push there takes nothing off disk in this one.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreToolUse):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, tool_name,
    tool_input.command, and agent_id (present ONLY when the call comes from
    inside a subagent). `transcript_path` is used only to locate the
    `subagents/` directory; `cwd` is where the git call runs.
  - env consumed: CLAUDE_PROJECT_DIR (the session's main checkout, for the
    tree comparison), plus the two ledger path overrides below.
  - stdout JSON (exit 0), on a deny only:
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": "..."}}
    and on an override only:
      {"systemMessage": "..."}
    An override deliberately emits NO permissionDecision: "allow" would
    short-circuit every other permission check, and this hook's opinion is only
    about live workers.
  - exit 0 always. An exception must never emit a deny.

Fail-open on every error path — no transcript_path, no `subagents/` dir,
unreadable ledger, malformed stdin — because a hook that cannot decide must not
block. The consequence, stated rather than hidden: a session whose records the
hook cannot read is unguarded exactly as it was before this hook existed. Two
deliberate exceptions, both fail-CLOSED, because each is a record that exists
and cannot be read rather than a record that is absent: a sidecar that will not
parse still counts its agent as live (its `worktreePath` is unreadable), and a
tree comparison that does not resolve — no git binary, a cwd outside any
repository, an unset CLAUDE_PROJECT_DIR — decides as the guard did before it
could compare trees at all.

Anything that aims the command away from the payload's cwd by a rule this does
not reimplement is an unresolved comparison rather than a guess, and so counts
the workers: the `--git-dir`/`--work-tree` flags, the same relocation spelled
`GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`, and a `cd`/`pushd`/`popd` before
the git word.

Tokenizer ceiling, stated as a rule rather than a list, because a list of ways
to hide a word invites the belief that it is complete: the `git` word and the
`cd` are read only in COMMAND POSITION of the single command string the hook is
handed, so whatever displaces them is not seen. A wrapper that execs the real
command (`env`, `command`, `nice`, `time` and their equivalents) does; so do
`bash -c "..."`, a `$( )` substitution, a token glued to a separator
(`ls&&git commit`), and heredoc body text. A `GIT_*` variable exported by an
EARLIER Bash call is the same ceiling in another place — it is not among this
command's tokens at all. None of these is the sanctioned bypass; the override
is, and it leaves a row. Seeing through them means interpreting the command
line rather than tokenizing it, with its own over-denial surface.

The pending set is `_lib/pending.py`, shared with `subagent-telemetry` so the
two cannot disagree about who is live. Agents holding their own checkout
(`worktreePath` on the sidecar) are excluded: they do not share this tree.
Everything else counts, read-only scouts included — a `checkout` or `pull`
changes the tree a scout is reading mid-read.

The guard is NOT main-session-only: a manager holding live builders is the same
hazard as a root session holding them, and the deny text fits it unchanged. A
delegating agent is excluded from its own pending set, and an agent that holds
its own worktree is exempt entirely — it is not looking at this tree.

Not covered: a destructive root-session WRITE (back up a file, break it,
restore it) to a file a live worker owns. That needs an ownership registry
mapping briefs to paths, which does not exist; worktree isolation solves it by
construction.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import json
import os
import shlex
import subprocess
import sys

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)
import pending  # noqa: E402  (same)

LOG_STREAM = "live-worker-git-guard"
LOG_PATH_ENV = "LIVE_WORKER_GIT_GUARD_LOG_PATH"

OVERRIDE_VAR = "ATELIER_GIT_GUARD_OVERRIDE"
OVERRIDE_TRUTHY = ("1", "true", "yes", "on")

# Verbs that write the index, the working tree, or a ref. `fetch` is absent on
# purpose: it moves no tracked file. `branch` is absent because the shape a
# session actually runs (`git branch`, `git branch --show-current`) is a read,
# and `branch -D` deletes a ref without touching the tree the workers hold.
MUTATING_VERBS = frozenset((
    "commit", "push", "merge", "pull", "rebase", "checkout", "switch", "stash",
    "reset", "cherry-pick", "revert", "clean", "restore", "am", "apply",
))

# git's own global options, the ones that take a SEPARATE value token. Without
# this set `git -C /repo commit` reads `/repo` as the subcommand and the call
# goes unguarded.
GLOBAL_FLAGS_WITH_VALUE = frozenset((
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "--config-env", "--attr-source", "--super-prefix",
))

# ...and the two of those that move the working tree itself, in either
# spelling. They make the targeted tree unknowable rather than wrong.
TREE_AIMING_FLAGS = ("--git-dir", "--work-tree")

# The same relocation spelled as environment, which git honours identically.
TREE_AIMING_VARS = frozenset(("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"))

# Builtins that move the cwd, which makes the payload's cwd stale for any git
# call later in the same command line.
CWD_MOVING_BUILTINS = frozenset(("cd", "pushd", "popd"))

# Per `git rev-parse` call. At most two run, and only once a mutating verb is
# already in hand, so the worst case sits well inside the hook's 10s budget.
GIT_TIMEOUT = 3

# A token ENDING in one of these is a shell separator, so the next token starts
# a fresh command: `a && git commit`, `a; git commit`, `a | git commit`.
SEPARATOR_TAILS = ("&", "|", ";", "(", ")", "{", "}")

# Read-only forms of verbs that otherwise write: `git stash list` is how a
# session orients, `git apply --check` touches nothing. Keyed by verb; a call
# whose first non-option argument (stash) or any option (apply) is listed here
# is a read and never fires.
READ_FORMS = {
    "stash": frozenset(("list", "show")),
    "apply": frozenset(("--check", "--stat", "--numstat", "--summary")),
}

MAX_NAMED_AGENTS = 4


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


# ---------------------------------------------------------------------------
# Reading the command
# ---------------------------------------------------------------------------

def _tokens(command):
    """Shell tokens for a Bash command string.

    shlex first, and its quote handling is the point rather than an accident:
    `echo "remember to git commit"` collapses to two tokens, the second of
    which is not `git`, so a mention of a git command inside a string can never
    be read as a call. An unbalanced quote makes shlex raise; the whitespace
    split is the fallback, which is coarser but never worse than nothing.
    """
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _is_assignment(token):
    """`NAME=value` — an env prefix, which does not end the command position."""
    name, sep, _value = token.partition("=")
    if not sep or not name:
        return False
    return name.replace("_", "").isalnum() and not name[0].isdigit()


def _first_mutating_verb(tokens):
    """(verb, index of the `git` token) for the first mutating git call, else
    (None, None).

    A `git` token only counts in COMMAND position — first, after a shell
    separator, or after an env assignment — so `man git commit` and
    `which git` are not git calls. `/usr/bin/git` counts: it is the same
    program, and matching the bare word only would make the guard one absolute
    path away from off. After it, git's own global options are skipped
    (including the value of a `-C`-style flag) and the first bare token is the
    subcommand.
    """
    command_position = True
    for index, token in enumerate(tokens):
        if command_position and os.path.basename(token) == "git":
            verb, verb_at = _subcommand(tokens, index + 1)
            if verb in MUTATING_VERBS and not _is_read_form(verb, tokens, verb_at + 1):
                return verb, index
        command_position = (
            token.endswith(SEPARATOR_TAILS) or _is_assignment(token)
        )
    return None, None


def _subcommand(tokens, start):
    """(subcommand, its index) at or after `start`, skipping global options;
    (None, None) when the command ends first."""
    i = start
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("-"):
            return token, i
        if token in GLOBAL_FLAGS_WITH_VALUE:
            i += 2  # the flag and its separate value
            continue
        i += 1
    return None, None


def _is_read_form(verb, tokens, start):
    """True when this call of a mutating verb is one of its read-only forms
    (READ_FORMS), judged on the arguments up to the next shell separator."""
    forms = READ_FORMS.get(verb)
    if not forms:
        return False
    args = []
    for token in tokens[start:]:
        args.append(token)
        if token.endswith(SEPARATOR_TAILS):
            break
    if verb == "stash":
        first = next((a for a in args if not a.startswith("-")), None)
        return first in forms
    return any(a in forms for a in args)


def _override_before(tokens, limit):
    """True when an `ATELIER_GIT_GUARD_OVERRIDE=1` assignment precedes the git
    word AS ITS ENV PREFIX — the contiguous run of assignments right before
    it. Position matters: the same string as an argument (a commit message,
    say) is not an override, and neither is a prefix on an earlier command in
    the same line (`OVERRIDE=1 echo hi && git commit`)."""
    i = limit - 1
    while i >= 0 and _is_assignment(tokens[i]):
        name, _sep, value = tokens[i].partition("=")
        if name == OVERRIDE_VAR and value.strip().lower() in OVERRIDE_TRUTHY:
            return True
        i -= 1
    return False


# ---------------------------------------------------------------------------
# Which tree the command targets
# ---------------------------------------------------------------------------

def _repo_root(directory):
    """Realpath'd working-tree root containing `directory`, or None when that
    does not resolve.

    realpath because the two sides of the comparison arrive by different
    routes — a payload cwd and an env var — and on macOS the same tree reached
    through a symlink (`/var` for `/private/var`) is spelled two ways.
    """
    if not isinstance(directory, str) or not directory:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            capture_output=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.decode("utf-8", "replace").strip()
    if not root:
        return None
    try:
        return os.path.realpath(root)
    except OSError:
        return None


def _target_directory(tokens, git_at, cwd):
    """The directory this git call resolves paths against, or None when
    something in the line aims it somewhere this hook does not compute.

    Anything BEFORE the git word that invalidates the payload's cwd — a cwd
    -moving builtin in command position, a tree-aiming environment assignment
    anywhere in the line, since a bare one carries to the rest of it — is
    unresolvable rather than wrong. After it, `-C` is cumulative and each value
    is taken relative to the one before it, which is exactly `os.path.join`;
    git accepts only the separate-value spelling, so there is no `-C/repo`
    form to handle.
    """
    if not isinstance(cwd, str) or not cwd:
        return None
    command_position = True
    for token in tokens[:git_at]:
        if command_position and os.path.basename(token) in CWD_MOVING_BUILTINS:
            return None
        if _is_assignment(token) and token.partition("=")[0] in TREE_AIMING_VARS:
            return None
        command_position = (
            token.endswith(SEPARATOR_TAILS) or _is_assignment(token)
        )
    directory = cwd
    index = git_at + 1
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("-"):
            break
        if any(token == flag or token.startswith(flag + "=")
               for flag in TREE_AIMING_FLAGS):
            return None
        if token == "-C":
            if index + 1 >= len(tokens):
                return None
            directory = os.path.join(directory, tokens[index + 1])
            index += 2
            continue
        if token in GLOBAL_FLAGS_WITH_VALUE:
            index += 2
            continue
        index += 1
    return directory


def _shares_session_tree(tokens, git_at, cwd):
    """True when the command targets the working tree the session's workers
    occupy — and when that cannot be decided, which counts as sharing."""
    target = _repo_root(_target_directory(tokens, git_at, cwd))
    if target is None:
        return True
    session = _repo_root(os.environ.get("CLAUDE_PROJECT_DIR"))
    return session is None or target == session


# ---------------------------------------------------------------------------
# Who is live
# ---------------------------------------------------------------------------

def _is_isolated(directory, key):
    """True when this agent holds its own checkout (`worktreePath` on its
    sidecar), so nothing done in THIS tree can reach it — and nothing it does
    reaches this tree either."""
    home = pending.sidecar_dir(directory, key) or directory
    meta = pending.read_sidecar(pending.sidecar_path(home, key)) or {}
    return bool(meta.get("worktreePath"))


def _live_workers(transcript_path, caller):
    """Pending delegations that SHARE this working tree.

    `caller` is the agent making the call, when the call comes from inside a
    subagent rather than the main session (a manager running `git commit` while
    its builders are live is the same hazard, and the deny text fits it). It is
    excluded twice over: an agent is never live from its own point of view, and
    an agent working in its own worktree is looking at a different tree, so
    this tree's occupants are not its problem.

    Raises rather than swallowing a ledger read failure: `main` fails open on
    it, and an unknowable settled set must not be silently rendered as "nothing
    has settled", which would deny on every agent this session ever started.
    """
    directory = pending.subagents_dir(transcript_path)
    if directory is None:
        return []
    if caller and _is_isolated(directory, caller):
        return []
    workers = []
    for key in pending.pending_keys(directory):
        if key == caller:
            continue
        meta = pending.read_sidecar(pending.sidecar_path(directory, key)) or {}
        if meta.get("worktreePath"):
            # Its own checkout: this tree's state is none of its business.
            continue
        workers.append({
            "agent_id": key,
            "agent_type": meta.get("agentType") or "agent",
            "description": meta.get("description") or "no description",
        })
    return workers


def _describe(workers):
    lines = [
        "  - {0} {1} ({2})".format(w["agent_type"], w["agent_id"], w["description"])
        for w in workers[:MAX_NAMED_AGENTS]
    ]
    if len(workers) > MAX_NAMED_AGENTS:
        lines.append("  - ...and {0} more".format(len(workers) - MAX_NAMED_AGENTS))
    return "\n".join(lines)


def _deny_reason(verb, workers):
    return (
        "atelier live-worker-git-guard: `git {verb}` is blocked — this session has "
        "{count} delegation(s) still running:\n\n{who}\n\n"
        "They are working in THIS tree, not their own checkout. A commit captures "
        "their half-applied edits as finished work; a pull, checkout, switch, stash, "
        "reset or restore takes their uncommitted files off disk (or autostashes and "
        "re-applies them) while they are mid-write, and the loss looks identical to "
        "success afterwards.\n\n"
        "Wait for their completion notifications, then re-run this command. Do NOT "
        "`git stash` by hand to get around it — hand-stashing reopens the exact window "
        "this closes, and the work lands in a stash entry the agent will never look "
        "for. If the change is genuinely unrelated to what they hold, re-run with the "
        "override prefix and say why in your next message:\n\n"
        "    {var}=1 git {verb} ...\n"
    ).format(verb=verb, count=len(workers), who=_describe(workers), var=OVERRIDE_VAR)


def _override_message(verb, workers):
    return (
        "atelier live-worker-git-guard: {var}=1 — `git {verb}` allowed with "
        "{count} live delegation(s) sharing this tree:\n{who}\n"
        "Their uncommitted work is at risk for the duration of this command."
    ).format(var=OVERRIDE_VAR, verb=verb, count=len(workers),
             who=_describe(workers))


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)
        if payload.get("tool_name") != "Bash":
            sys.exit(0)

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)
        command = tool_input.get("command")
        if not command or not isinstance(command, str):
            sys.exit(0)

        tokens = _tokens(command)
        verb, git_at = _first_mutating_verb(tokens)
        if verb is None:
            sys.exit(0)

        overridden = _override_before(tokens, git_at)
        workers = _live_workers(
            payload.get("transcript_path"),
            pending.agent_key(payload.get("agent_id")),
        )
        if workers and not _shares_session_tree(
                tokens, git_at, payload.get("cwd")):
            workers = []
        if not workers and not overridden:
            sys.exit(0)

        if workers and overridden:
            _emit({"systemMessage": _override_message(verb, workers)})
        elif workers:
            _emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": _deny_reason(verb, workers),
                },
            })

        # A row per decision that reached the session, plus one for an override
        # used where nothing was going to block: an override that leaves no
        # trace is exactly the silence this stream exists to end. An empty
        # `pending` is what separates the two. Still never one row per Bash
        # call — both early exits above run first.
        agentlog.append(LOG_STREAM, {
            "session_id": payload.get("session_id"),
            "decision": "override" if overridden else "deny",
            "verb": verb,
            "pending": [w["agent_id"] for w in workers],
        }, agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)
        sys.exit(0)

    except SystemExit:
        raise
    except Exception:
        # Fail-open, and silently: a guard that cannot read its own records has
        # no grounds to block, and an error message on stdout would be parsed
        # as a hook decision.
        sys.exit(0)


if __name__ == "__main__":
    main()
