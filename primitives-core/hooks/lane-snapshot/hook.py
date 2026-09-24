#!/usr/bin/env python3
"""
lane-snapshot — SessionStart hook.

Starts the snapshot daemon (`snapshot_lanes.py`, beside this file) for the
project this session opened in, once per repo rather than once per session: a
pidfile lock keyed to the repo's git common dir means the second, third and
tenth concurrent session — from any linked worktree, under either harness — all
share the first one's daemon.

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
import codex_lifecycle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_lanes  # noqa: E402  (shares the pidfile key and lock with the daemon)

LOG_STREAM = "lane-snapshot"
LOG_PATH_ENV = "LANE_SNAPSHOT_LOG_PATH"
DAEMON_NAME = "snapshot_lanes.py"
DAEMON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DAEMON_NAME)
# Two git calls run sequentially inside a hook whose declared budget is 10s
# (config.json/hooks.json), so their sum has to fit under it.
GIT_TIMEOUT = 4


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


def _already_running(key):
    """True when a daemon holds this repo's pidfile lock. Probing takes the
    lock for an instant; a daemon starting in that instant exits, and the one
    this hook then spawns takes over."""
    fd = snapshot_lanes.try_lock(snapshot_lanes.pidfile_path(key))
    if fd is None:
        return True
    os.close(fd)
    return False


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

        payload = codex_lifecycle.prepare(payload)
        if payload is None:
            return

        cwd = payload.get("cwd") or os.getcwd()
        root = _repo_root(cwd)
        common = snapshot_lanes.common_dir(root, GIT_TIMEOUT) if root else None
        # Every checkout of a repo shares one daemon, rooted at the main
        # checkout; a bare repo's worktrees keep one each (snapshot_lanes.repo_key).
        if (common and os.path.basename(common) == ".git"
                and not os.environ.get("LANE_SNAPSHOT_ROOT")):
            root = os.path.dirname(common)
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
        if not common:
            log(dict(record, launched=False, reason="not a git worktree"))
            sys.exit(0)
        if not os.path.isfile(DAEMON_PATH):
            log(dict(record, launched=False, reason="daemon missing at " + DAEMON_PATH))
            sys.exit(0)
        if _already_running(snapshot_lanes.repo_key(root, common)):
            log(dict(record, launched=False, reason="daemon already running for this repo"))
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
