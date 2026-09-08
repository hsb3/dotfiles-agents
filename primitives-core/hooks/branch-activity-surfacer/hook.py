#!/usr/bin/env python3
"""
branch-activity-surfacer — SessionStart hook.

Warns a starting session that this branch has moved, or that another session's
process is still alive on it, and names what changed rather than that someone
was here.

Two signals, deliberately keyed differently:
  - moved: the tip differs from the tip the last recorded start saw — from ANY
    session, including this one's own earlier row. The question is "has the
    branch moved since anyone last looked", so filtering by session would miss
    the case where the peer restarts and records the new tip first.
  - peer: another session's owning process is still alive and started inside
    the TTL. Identity is the owning `claude` process, NOT session_id: `/clear`
    mints a new session_id in the same process, so a session_id key reports the
    operator to themselves.

The record is a local ledger written through the shared append path. Nothing is
pushed and nothing is fetched: a marker branch would need network and push
rights at every session start, and would only report the sessions that
remembered to write to it.

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
import time
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

# `fork` is a real production source; leaving it out made a forked session
# invisible to the next one.
SURFACE_SOURCES = {"startup", "clear", "resume", "fork"}

PEER_TTL_SECONDS_DEFAULT = 3600
MAX_BYTES_DEFAULT = 1048576
LOG_COMMITS_DEFAULT = 5
PEERS_NAMED = 3

# The whole budget must stay under the hook's own timeout (20s), or a merely
# slow git gets the process killed before it writes its row.
GIT_TIMEOUT = 3
GH_TIMEOUT = 4
PS_TIMEOUT = 1
PS_DEADLINE = 1.5
PS_MAX_HOPS = 8

#: A git call that could not run at all (no binary, timeout), as distinct from
#: one that ran and answered "no" — the ledger's skip reasons must not conflate
#: a broken environment with a detached HEAD.
UNAVAILABLE = object()


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Session identity: the owning `claude` process
# ---------------------------------------------------------------------------

def _ps_parent(pid):
    """(ppid, comm) for `pid`, or None when ps cannot answer."""
    try:
        proc = subprocess.run(
            ["ps", "-o", "ppid=,comm=", "-p", str(pid)],
            capture_output=True, timeout=PS_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    line = proc.stdout.decode("utf-8", "replace").strip()
    if not line:
        return None
    parts = line.split(None, 1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), parts[1].strip()
    except ValueError:
        return None


def _owner_pid():
    """The pid of the `claude` process this hook is running under, or a
    fallback, or None.

    This is the session's real identity: `/clear` mints a new session_id
    without a new process, so session_id over-reports peers and under-reports
    the same operator.
    """
    override = os.environ.get("BRANCH_ACTIVITY_OWNER_PID")
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    try:
        deadline = time.monotonic() + PS_DEADLINE
        pid = os.getpid()
        for _ in range(PS_MAX_HOPS):
            if time.monotonic() > deadline:
                break
            answer = _ps_parent(pid)
            if answer is None:
                break
            ppid, comm = answer
            if os.path.basename(comm.split()[0] if comm.split() else comm) == "claude":
                return pid
            if ppid <= 1:
                break
            pid = ppid
        return os.getppid()
    except Exception:
        return None


def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except Exception:
        return True  # PermissionError and friends mean it exists
    return True


# ---------------------------------------------------------------------------
# git facts
# ---------------------------------------------------------------------------

def _git(cwd, args, timeout=GIT_TIMEOUT):
    """stdout of a git call, None when it ran and failed, UNAVAILABLE when it
    could not run at all."""
    try:
        proc = subprocess.run(
            ["git", "-C", cwd] + args, capture_output=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return UNAVAILABLE
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace").strip()


def _repo_key(cwd):
    """Absolute, symlink-resolved shared git dir.

    `--git-common-dir` rather than the toplevel: a linked worktree and its main
    checkout share one git dir, so they share one key and a session in either
    sees the other's rows.
    """
    common = _git(cwd, ["rev-parse", "--git-common-dir"])
    if common is UNAVAILABLE or not common:
        return common or None
    if not os.path.isabs(common):
        common = os.path.join(cwd, common)
    return os.path.realpath(common)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

def _parse_ts(value):
    """agentlog's ISO-8601 Zulu stamp as an aware datetime, or None.

    A zone-less stamp returns None rather than a naive datetime: subtracting one
    raises, and fail-open would then swallow this session's own row — one bad
    line would disable the hook for that branch permanently.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return None if parsed.tzinfo is None else parsed


def _read_rows(path, max_bytes, repo, branch):
    """Session rows for this repo+branch from the ledger's tail, in file order.

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
        head = row.get("head")
        if not isinstance(head, str) or len(head) < 7:
            continue
        if not isinstance(row.get("ts"), str):
            continue
        if not isinstance(row.get("session_id"), str):
            continue
        rows.append(row)
    return rows


def _latest(rows):
    """The most recent row by `ts`, which agentlog stamps as ISO-8601 Zulu and
    which therefore sorts lexically in the order it sorts chronologically."""
    return max(rows, key=lambda row: row["ts"]) if rows else None


def _live_peers(rows, session_id, owner_pid, ttl, now):
    """[(row, age_seconds)] for other sessions that may still be running, newest
    first.

    Identity is `owner_pid` when both sides carry one, else `session_id` — rows
    written before the lineage key existed still behave as they did. Liveness is
    only checkable for a row that carries a pid.
    """
    newest = {}
    for row in rows:
        pid = row.get("owner_pid")
        keyed_by_pid = isinstance(pid, int) and owner_pid is not None
        key = ("pid", pid) if keyed_by_pid else ("sid", row["session_id"])
        if key not in newest or row["ts"] > newest[key]["ts"]:
            newest[key] = row

    peers = []
    for (kind, value), row in newest.items():
        if kind == "pid":
            if value == owner_pid:
                continue  # this very process: a /clear or resume, not a peer
            if not _pid_alive(value):
                continue
        elif value == session_id:
            continue
        stamp = _parse_ts(row["ts"])
        if stamp is None:
            continue
        age = (now - stamp).total_seconds()
        if abs(age) >= ttl:
            continue
        peers.append((row, age))
    peers.sort(key=lambda item: item[0]["ts"], reverse=True)
    return peers


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

def _commits_between(cwd, old, new, limit):
    """`<old>..<new>` as `<short> <author> <subject>` lines, or None when the
    range is not resolvable here (a rewritten or not-yet-fetched prior tip)."""
    out = _git(cwd, [
        "log", "--format=%h %an %s", "-n", str(limit), "{0}..{1}".format(old, new),
    ])
    if out is None or out is UNAVAILABLE:
        return None
    return [line for line in out.splitlines() if line.strip()]


def _dropped_count(cwd, old, new):
    """How many commits are on `old` but not on `new` — a rewind or a force
    rebase, the move that most deserves a loud message."""
    out = _git(cwd, ["rev-list", "--count", "{0}..{1}".format(new, old)])
    if out is None or out is UNAVAILABLE:
        return None
    try:
        return int(out)
    except ValueError:
        return None


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

def _format(branch, head, moved_from, peers, commits, dropped, pr):
    """(additionalContext, systemMessage). The two clauses are independent and
    may describe different prior rows.

    The move is stated without attributing agency: the ledger records that a
    start saw a different tip, not who moved it, and the prior row may well be
    this same operator's. The `%an` in each commit line carries the author.
    """
    lines = []
    summary = []

    if moved_from is not None:
        lines.append(
            "Branch {0} moved since the last recorded start here: {1} -> {2}.".format(
                branch, moved_from[:8], head[:8],
            )
        )
        if commits:
            lines.append("Commits added since:")
            lines.extend("  - " + line for line in commits)
        elif commits is None:
            lines.append(
                "  (that earlier commit is not in this checkout, so the range cannot "
                "be listed — fetch before assuming a clean base.)"
            )
        elif dropped:
            lines.append(
                "  ({0} commit(s) recorded then are no longer on this branch — "
                "history was rewritten or reset.)".format(dropped)
            )
        if pr:
            lines.append("Merged PR carrying this tip: {0}.".format(pr))
        summary.append("branch {0} moved ({1} -> {2})".format(
            branch, moved_from[:8], head[:8],
        ))

    if peers:
        lines.append(
            "{0} session(s) on this branch look live:".format(len(peers))
            if len(peers) > 1 else "Another session on this branch looks live:"
        )
        for row, age in peers[:PEERS_NAMED]:
            lines.append("  - {0}, started {1} minute(s) ago in {2}".format(
                row["session_id"], max(0, int(age // 60)),
                row.get("cwd") or "an unknown cwd",
            ))
        if len(peers) > PEERS_NAMED:
            lines.append("  - (+{0} more)".format(len(peers) - PEERS_NAMED))
        lines.append("Coordinate before committing.")
        summary.append("{0} other session(s) look live on it".format(len(peers)))

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
    if repo is UNAVAILABLE:
        skip("git could not be run")
    if repo is None:
        skip("not a git repository")

    branch = _git(cwd, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if branch is UNAVAILABLE:
        skip("git could not be run")
    if not branch:
        skip("detached HEAD")

    head = _git(cwd, ["rev-parse", "HEAD"])
    if head is UNAVAILABLE:
        skip("git could not be run")
    if not head:
        skip("no commits")

    owner_pid = _owner_pid()
    rows = _read_rows(
        agentlog.stream_path(LOG_STREAM, LOG_PATH_ENV),
        _env_int("BRANCH_ACTIVITY_MAX_BYTES", MAX_BYTES_DEFAULT), repo, branch,
    )

    latest = _latest(rows)
    moved_from = latest["head"] if latest is not None and latest["head"] != head else None
    peers = _live_peers(
        rows, session_id, owner_pid,
        _env_int("BRANCH_ACTIVITY_PEER_TTL_SECONDS", PEER_TTL_SECONDS_DEFAULT),
        datetime.now(timezone.utc),
    )

    signals = (["moved"] if moved_from else []) + (["peer"] if peers else [])

    if signals:
        commits = dropped = pr = None
        if moved_from:
            commits = _commits_between(
                cwd, moved_from, head,
                _env_int("BRANCH_ACTIVITY_LOG_COMMITS", LOG_COMMITS_DEFAULT),
            )
            if commits == []:
                dropped = _dropped_count(cwd, moved_from, head)
            pr = _merged_pr(cwd, head)
        context, system = _format(
            branch, head, moved_from, peers, commits, dropped, pr,
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

    # Last, so this session's own row can never be read as a prior start.
    log({
        "event": "session", "repo": repo, "branch": branch, "head": head,
        "session_id": session_id, "owner_pid": owner_pid, "source": source,
        "cwd": cwd, "surfaced": bool(signals), "signals": signals,
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
