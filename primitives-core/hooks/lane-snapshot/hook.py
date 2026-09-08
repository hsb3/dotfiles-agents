#!/usr/bin/env python3
"""
lane-snapshot — SessionStart hook.

Starts the snapshot daemon (`snapshot_lanes.py`, beside this file) for the
project this session opened in, once per repo rather than once per session: a
`pgrep` guard keyed to the resolved repo root means the second, third and tenth
concurrent session all share the first one's daemon.

Why a daemon at all: workers run in linked worktrees under read-only git, so
their output is uncommitted until hand-over, and a crash or a mistaken
`worktree remove` takes it with them. The daemon commits each lane's working
tree to `refs/lane-snapshots/<name>` on an interval.

    Recover: git show refs/lane-snapshots/<name>:<path>

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SessionStart):
  - stdin JSON fields consumed: session_id, cwd, source.
  - stdout: nothing. This hook injects no context — a background daemon has
    nothing to tell the model, and the ledger is where its evidence belongs.
  - exit 0 ALWAYS, on every path including a failed launch, and it never waits
    on the daemon. Session start is not allowed to get slower because of this.

The daemon is spawned in its own session (`start_new_session=True`) with its
streams at devnull, so it outlives the hook process and never inherits the
harness's pipes — a daemon holding stdout open is a hung session start.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import re
import subprocess
import sys
import traceback

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

LOG_STREAM = "lane-snapshot"
LOG_PATH_ENV = "LANE_SNAPSHOT_LOG_PATH"
DAEMON_NAME = "snapshot_lanes.py"
DAEMON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DAEMON_NAME)
# Both run sequentially inside a hook whose declared budget is 10s
# (config.json/hooks.json), so their sum has to fit under it.
GIT_TIMEOUT = 4
PGREP_TIMEOUT = 4


def _repo_root(cwd):
    """The repo this session opened in.

    $LANE_SNAPSHOT_ROOT wins outright (the override an operator sets when the
    tree to protect is not the tree the session sits in). Otherwise the payload
    cwd is resolved with `git rev-parse --show-toplevel`, which is what makes
    the daemon's argv root correct for an installed plugin, whose own files
    live in the plugin cache and not in this repo at all. None when nothing
    resolves — the hook then does nothing, rather than guessing a tree.
    """
    override = os.environ.get("LANE_SNAPSHOT_ROOT")
    if override:
        return os.path.abspath(override)
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or "").strip()
    return out if proc.returncode == 0 and out else None


def _pattern(root):
    """The pgrep pattern: the daemon's filename, the root, and a boundary.

    All three matter. The filename alone would match another repo's daemon and
    report a false "already running", leaving that repo unprotected — and so
    would an unterminated root, because `pgrep -f` matches a SUBSTRING: without
    the boundary a live daemon for `/x/repo-second` makes `/x/repo` read as
    protected while nothing is watching it. Two ordinarily named siblings are
    enough; `agent-a1` and `agent-a15` is this repo's own worktree scheme.
    """
    literal = "{0} {1}".format(DAEMON_NAME, root.rstrip("/"))
    escaped = re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", literal)
    # The root is the daemon's last argument, so end-of-string is the usual
    # case; `/` and a space keep a trailing slash or a future extra arg a match.
    return escaped + r"($|[/ ])"


def _already_running(root):
    """True when a daemon for this root is live. On a machine with no `pgrep`
    this returns False: launching a possible second daemon is the cheap failure
    (duplicate snapshot commits, same content), not launching any is the
    expensive one."""
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "--", _pattern(root)],
            capture_output=True, text=True, timeout=PGREP_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _launch(root):
    """Detach the daemon and return immediately. Never waits."""
    devnull = open(os.devnull, "wb")  # noqa: SIM115 (handed to the child, then closed)
    try:
        proc = subprocess.Popen(
            [sys.executable, DAEMON_PATH, root],
            stdin=subprocess.DEVNULL, stdout=devnull, stderr=devnull,
            start_new_session=True, close_fds=True,
        )
    finally:
        devnull.close()
    return proc.pid


def main():
    payload = {}
    try:
        try:
            payload = json.loads(sys.stdin.read()) or {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        cwd = payload.get("cwd") or os.getcwd()
        root = _repo_root(cwd)
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(cwd),
        )
        record = {
            "event": "hook",
            "session_id": payload.get("session_id"),
            "source": payload.get("source"),
            "root": root,
        }

        if not root:
            log(dict(record, launched=False, reason="no repo root resolved"))
            sys.exit(0)
        if not os.path.isfile(DAEMON_PATH):
            log(dict(record, launched=False, reason="daemon missing at " + DAEMON_PATH))
            sys.exit(0)
        if _already_running(root):
            log(dict(record, launched=False, reason="daemon already running for this root"))
            sys.exit(0)

        try:
            pid = _launch(root)
        except Exception as exc:
            log(dict(record, launched=False,
                     reason="launch failed: {0}: {1}".format(type(exc).__name__, exc)))
            sys.exit(0)
        log(dict(record, launched=True, pid=pid))
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as exc:
        # Fail-open: never break session start on our own error.
        try:
            agentlog.append(LOG_STREAM, {
                "event": "hook", "launched": False,
                "error": "{0}: {1}".format(type(exc).__name__, exc),
                "traceback": traceback.format_exc(limit=3),
            }, agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
