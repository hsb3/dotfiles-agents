#!/usr/bin/env python3
"""
branch-activity-surfacer — SessionStart hook.

Warns a starting session that another session has been working the same branch,
and names what changed rather than that someone was here.

Two signals, both derived locally:
  - moved: the branch tip differs from the tip the last recorded session start
    saw. Read from git, so a move made on another machine or by a merge on
    GitHub also counts, once this checkout has the commits.
  - peer: another session_id recorded a start on this repo+branch inside the
    TTL, so it may still be live.

The record is a local ledger keyed by repo + branch + tip + session id, written
through the shared append path. Nothing is pushed and nothing is fetched: a
marker branch would need network and push rights at every session start, and
would only work for sessions that remembered to write to it.

Contract (SessionStart):
  - stdin JSON fields consumed: session_id, cwd, source, hook_event_name,
    optionally agent_type.
  - stdout JSON, ONLY when a signal fires:
    {"hookSpecificOutput": {"hookEventName": "SessionStart",
                            "additionalContext": "..."},
     "systemMessage": "atelier: ..."}
  - exit 0 always; fail-open on any internal error (no stdout, one log row).

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

LOG_STREAM = "branch-activity"
LOG_PATH_ENV = "BRANCH_ACTIVITY_LOG_PATH"

SURFACE_SOURCES = {"startup", "clear", "resume"}

PEER_TTL_SECONDS_DEFAULT = 3600
MAX_BYTES_DEFAULT = 1048576
LOG_COMMITS_DEFAULT = 5

GIT_TIMEOUT = 5
GH_TIMEOUT = 4


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# git facts
# ---------------------------------------------------------------------------

def _git(cwd, args, timeout=GIT_TIMEOUT):
    """stdout of a git call, or None on any failure — including no git binary."""
    try:
        proc = subprocess.run(
            ["git", "-C", cwd] + args, capture_output=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace").strip()


def _repo_key(cwd):
    """Absolute, symlink-resolved shared git dir, or None outside a repository.

    `--git-common-dir` rather than the toplevel: a linked worktree and its main
    checkout share one git dir, so they share one key and a session in either
    sees the other's rows.
    """
    common = _git(cwd, ["rev-parse", "--git-common-dir"])
    if not common:
        return None
    if not os.path.isabs(common):
        common = os.path.join(cwd, common)
    return os.path.realpath(common)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

def _parse_ts(value):
    """agentlog's ISO-8601 Zulu stamp as an aware datetime, or None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_rows(path, max_bytes, repo, branch):
    """Session rows for this repo+branch from the ledger's tail, oldest first.

    Only the tail is read: the ledger grows without bound and a session start
    must not slow down with it. The first line after a seek is a partial line
    and is dropped.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()
            data = handle.read()
    except OSError:
        return []

    rows = []
    for line in data.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict) or row.get("event") != "session":
            continue
        if row.get("repo") != repo or row.get("branch") != branch:
            continue
        if not isinstance(row.get("head"), str) or not isinstance(row.get("ts"), str):
            continue
        if not isinstance(row.get("session_id"), str):
            continue
        rows.append(row)
    return rows


def _latest_other_session(rows, session_id):
    """The most recent row from a session that is not this one, or None."""
    others = [row for row in rows if row["session_id"] != session_id]
    if not others:
        return None
    return max(others, key=lambda row: row["ts"])


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def _commits_between(cwd, old, new, limit):
    """`<old>..<new>` as `<short> <author> <subject>` lines, or None when the
    range is not resolvable here (a rewritten or not-yet-fetched prior tip)."""
    out = _git(cwd, [
        "log", "--format=%h %an %s", "-n", str(limit), "{0}..{1}".format(old, new),
    ])
    if out is None:
        return None
    return [line for line in out.splitlines() if line.strip()]


def _merged_pr(cwd, head):
    """`#<n> "<title>" by <login>` for a merged PR containing `head`, or None.

    Entirely best-effort: the whole clause is dropped when `gh` is absent,
    disabled, slow, or offline. This is the one network-touching path in the
    hook and it may never make session start hang or noisy.
    """
    if os.environ.get("BRANCH_ACTIVITY_GH") == "0" or shutil.which("gh") is None:
        return None
    try:
        proc = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--search", head,
             "--json", "number,title,author", "--limit", "1"],
            cwd=cwd, capture_output=True, timeout=GH_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        items = json.loads(proc.stdout.decode("utf-8", "replace") or "[]")
    except ValueError:
        return None
    if not isinstance(items, list) or not items:
        return None
    item = items[0]
    if not isinstance(item, dict) or "number" not in item:
        return None
    author = (item.get("author") or {}).get("login") or "an unknown author"
    return '#{0} "{1}" by {2}'.format(item["number"], item.get("title", ""), author)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

def _format(branch, head, prior, moved, peer, commits, pr, age_seconds):
    """(additionalContext, systemMessage) for the signals that fired."""
    lines = []
    summary = []

    if moved:
        lines.append(
            "Another session left branch {0} at a different commit than it is on now. "
            "Tip: {1} -> {2}.".format(branch, prior["head"][:8], head)
        )
        if commits:
            lines.append("Commits added since:")
            lines.extend("  - " + line for line in commits)
        elif commits is None:
            lines.append(
                "  (that earlier commit is not in this checkout, so the range "
                "cannot be listed — fetch before assuming a clean base.)"
            )
        if pr:
            lines.append("Merged PR carrying this tip: {0}.".format(pr))
        summary.append(
            "this branch changed since the last session here ({0} -> {1})".format(
                prior["head"][:8], head[:8],
            )
        )

    if peer:
        minutes = max(0, int(age_seconds // 60))
        lines.append(
            "Session {0} started {1} minute(s) ago in {2} and may still be live on "
            "branch {3} — coordinate before committing.".format(
                prior["session_id"], minutes, prior.get("cwd") or "an unknown cwd", branch,
            )
        )
        summary.append("a session started {0}m ago is on it".format(minutes))

    return "\n".join(lines), "atelier: " + "; ".join(summary) + "."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    payload = json.loads(sys.stdin.read())

    session_id = payload.get("session_id") or "unknown"
    cwd = payload.get("cwd") or os.getcwd()
    source = payload.get("source") or "unknown"
    agent_type = payload.get("agent_type")

    log = agentlog.make_logger(
        LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(cwd),
    )

    def skip(reason):
        log({
            "event": "skip", "session_id": session_id, "source": source,
            "surfaced": False, "reason": reason,
        })
        sys.exit(0)

    if source not in SURFACE_SOURCES:
        skip("source not eligible")
    if agent_type and agent_type != "main":
        skip("subagent session")

    repo = _repo_key(cwd)
    if repo is None:
        skip("not a git repository")
    branch = _git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not branch or branch == "HEAD":
        skip("detached HEAD")
    head = _git(cwd, ["rev-parse", "HEAD"])
    if not head:
        skip("no commits")

    ledger = agentlog.stream_path(LOG_STREAM, LOG_PATH_ENV)
    rows = _read_rows(
        ledger, _env_int("BRANCH_ACTIVITY_MAX_BYTES", MAX_BYTES_DEFAULT), repo, branch,
    )
    prior = _latest_other_session(rows, session_id)

    signals = []
    age_seconds = None
    if prior is not None:
        if prior["head"] != head:
            signals.append("moved")
        prior_ts = _parse_ts(prior["ts"])
        if prior_ts is not None:
            age_seconds = (datetime.now(timezone.utc) - prior_ts).total_seconds()
            ttl = _env_int("BRANCH_ACTIVITY_PEER_TTL_SECONDS", PEER_TTL_SECONDS_DEFAULT)
            if abs(age_seconds) < ttl:
                signals.append("peer")

    if signals:
        moved = "moved" in signals
        commits = pr = None
        if moved:
            commits = _commits_between(
                cwd, prior["head"], head,
                _env_int("BRANCH_ACTIVITY_LOG_COMMITS", LOG_COMMITS_DEFAULT),
            )
            pr = _merged_pr(cwd, head)
        context, system = _format(
            branch, head, prior, moved, "peer" in signals, commits, pr, age_seconds or 0,
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
            # Visible to the USER in the TUI — additionalContext reaches only
            # the model.
            "systemMessage": system,
        }))

    # Last, so this session's own row can never be the prior row it read.
    log({
        "event": "session", "repo": repo, "branch": branch, "head": head,
        "session_id": session_id, "source": source, "cwd": cwd,
        "surfaced": bool(signals), "signals": signals,
    })
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail-open: never break session start
        try:
            agentlog.append(
                LOG_STREAM,
                {
                    "event": "error", "surfaced": False,
                    "error": "{0}: {1}".format(type(exc).__name__, exc),
                    "traceback": traceback.format_exc(limit=3),
                },
                agentlog.resolve_project(),
                LOG_PATH_ENV,
            )
        except Exception:
            pass
        sys.exit(0)
