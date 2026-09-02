"""pending — which delegations this session started and has not seen settle.

Extracted from `subagent-telemetry/hook.py`, which computes exactly this set to
decide whether a delegation has stalled. `live-worker-git-guard` needs the same
set to decide whether the working tree is shared with a live worker, and the
answer must be the same one in both places: two readers of the same on-disk
records that disagree about who is live is worse than either reader alone.

The records, as Claude Code writes them (verified against real files under
~/.claude/projects, 2026-08):

    <projects>/<slug>/<session_id>.jsonl                            parent transcript
    <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
    <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

STARTED is the `agent-*.meta.json` sidecars in the session's own `subagents/`
directory. SETTLED is the agent_ids a bounded tail of the delegation ledger
already accounts for. PENDING is the difference.

Sidecar keys observed: agentType (always), description, toolUseId, spawnDepth,
model (only when the dispatch overrode the model), parentAgentId, worktreePath,
worktreeBranch, name, isFork.

Stdlib-only, Python 3.9 compatible. A missing or malformed record yields the
empty answer rather than raising. An unreadable LEDGER is the one exception:
`settled_ids` lets that error propagate, because an empty settled set and an
unknowable one are different facts — the first says nothing has stopped, the
second says the caller cannot tell, and a caller that acts on the difference
(the git guard, which would otherwise deny on an unknowable set) needs to see
it. Every caller therefore wraps its call in its own fail-open handler.
"""

import json
import os

import agentlog

SUBAGENTS_DIRNAME = "subagents"
AGENT_FILE_PREFIX = "agent-"
SIDECAR_SUFFIX = ".meta.json"
TRANSCRIPT_SUFFIX = ".jsonl"

# The ledger subagent-telemetry writes and everything else reads. The stream
# name is the stem that ledger already had (`delegation.jsonl`), not a hook
# name: the rows are the delegation record, and keeping the stem keeps old and
# new rows queryable as one series.
LEDGER_STREAM = "delegation"
LEDGER_PATH_ENV = "SUBAGENT_TELEMETRY_LOG_PATH"
STALL_EVENT = "stall"

TAIL_BYTES_DEFAULT = 256 * 1024  # 256 KB — same window as context-watermark
# How many sibling session directories a sidecar miss may probe (see
# `sidecar_dir`). A `/clear` re-homes a live delegation into a NEW session dir
# adjacent in time to the old one, so the sidecar's dir is among the newest
# siblings — while a slug can accumulate hundreds of session dirs in total.
# Twelve covers the re-home with room for the interleaved sessions of a busy
# day; past it the lookup misses exactly as it did before, silently.
SIBLING_PROBE_LIMIT = 12


def env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


TAIL_BYTES = env_int("SUBAGENT_TELEMETRY_TAIL_BYTES", TAIL_BYTES_DEFAULT)


def read_tail(path, tail_bytes):
    """Read only the last `tail_bytes` of the file. Returns a str (may start
    mid-line; caller splits on newlines and discards the first partial line
    unless it's the only line)."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size > tail_bytes:
            f.seek(size - tail_bytes)
        else:
            f.seek(0)
        data = f.read()
    if size > tail_bytes:
        nl = data.find(b"\n")
        if nl != -1:
            data = data[nl + 1 :]
    return data.decode("utf-8", errors="replace")


def subagents_dir(transcript_path):
    """Candidate `subagents/` directory for a payload's transcript path.

    Two shapes are handled: the parent transcript `<session_id>.jsonl`, whose
    subagents live in the sibling directory `<session_id>/subagents/`; and a
    path that already points inside a `subagents/` directory (a nested
    delegation), in which case that directory is the answer. Returns None when
    no candidate exists on disk.
    """
    if not transcript_path:
        return None
    parent = os.path.dirname(transcript_path)
    if os.path.basename(parent) == SUBAGENTS_DIRNAME and os.path.isdir(parent):
        return parent
    candidate = os.path.join(os.path.splitext(transcript_path)[0], SUBAGENTS_DIRNAME)
    return candidate if os.path.isdir(candidate) else None


def agent_key(agent_id):
    """Bare agent id usable as a filename component, or None.

    Observed payloads carry the id unprefixed ("a31412cbc7cdb39e8") while the
    files carry an "agent-" prefix; a prefixed id is accepted too. basename()
    is what keeps a hostile or malformed id from escaping the subagents dir.
    """
    if not isinstance(agent_id, str):
        return None
    key = os.path.basename(agent_id.strip())
    if key.startswith(AGENT_FILE_PREFIX):
        key = key[len(AGENT_FILE_PREFIX):]
    if not key or key in (".", ".."):
        return None
    return key


def sidecar_path(directory, key):
    return os.path.join(directory, AGENT_FILE_PREFIX + key + SIDECAR_SUFFIX)


def sidecar_dir(directory, key):
    """The `subagents/` directory that actually holds this agent's sidecar, or
    None if no bounded probe finds one.

    Normally it is the payload's own directory. It is NOT after a `/clear`:
    the session is re-homed under a new id mid-delegation, the agent keeps
    running, its transcript follows into `<slug>/<new_session>/subagents/` and
    the sidecar stays behind in the old one (measured: one live agent, two
    session dirs under one slug, exactly one sidecar). Resolving only in the
    payload's directory drops that row — and it is the longest-running
    delegation of the wave, the one most worth measuring.

    `agent_id` is globally unique by design, so it carries the join across
    directories. The probe is deliberately narrow, and this narrowness is the
    whole safety argument: it runs only on a miss, looks only for that ONE
    exact filename, never leaves the slug, and stops after the
    SIBLING_PROBE_LIMIT most recently modified siblings.
    """
    if os.path.isfile(sidecar_path(directory, key)):
        return directory

    session_dir = os.path.dirname(directory)
    candidates = []
    try:
        with os.scandir(os.path.dirname(session_dir)) as entries:
            for entry in entries:
                if entry.path == session_dir or not entry.is_dir():
                    continue
                try:
                    # The session dir's own mtime, one stat from the entry we
                    # already hold. Recency is the right order here because the
                    # two halves of a re-homed delegation are adjacent in time.
                    candidates.append((entry.stat().st_mtime, entry.path))
                except OSError:
                    continue
    except OSError:
        return None

    candidates.sort(reverse=True)
    for _mtime, path in candidates[:SIBLING_PROBE_LIMIT]:
        sibling = os.path.join(path, SUBAGENTS_DIRNAME)
        if os.path.isfile(sidecar_path(sibling, key)):
            return sibling
    return None


def read_sidecar(path):
    """Parsed sidecar dict, or None if absent/unreadable/malformed/not an object."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def started_keys(directory):
    """Every agent this session STARTED, from the sidecar files themselves.

    The sidecar directory is deliberately the started universe. It is the exact
    predicate that gates a delegation row being written, so a phantom
    SubagentStop (an event for an agent that never got a `subagents/` entry)
    can neither produce a stop row nor enter the pending set — one predicate,
    one code path, no join to go wrong.

    THIS DIRECTORY ONLY. Do NOT extend `sidecar_dir`'s sibling probe to here:
    that probe is a single-filename lookup for an agent already known to have
    stopped, whereas widening the started universe would sweep in every
    historical session under the slug — delegations whose stop rows aged out of
    the ledger tail long ago — and report every one of them as pending, at
    every call. The asymmetry is the design, not an oversight; it is pinned by
    test_a_sidecar_only_in_a_sibling_session_is_never_reported_pending.
    """
    keys = []
    try:
        names = os.listdir(directory)
    except OSError:
        return keys
    for name in names:
        if not (name.startswith(AGENT_FILE_PREFIX) and name.endswith(SIDECAR_SUFFIX)):
            continue
        key = name[len(AGENT_FILE_PREFIX):-len(SIDECAR_SUFFIX)]
        if key:
            keys.append(key)
    return keys


def settled_ids(tail_bytes=TAIL_BYTES):
    """agent_ids already accounted for, per the ledger tail — matched by
    agent_id ALONE, regardless of which session recorded them.

    Two kinds of row settle an agent: its delegation row (it stopped), and a
    prior stall row naming it (it was already reported — that is the dedup, so
    a stalled agent is named once per tail window rather than at every
    subsequent settle).

    The session is deliberately NOT part of the match. After a `/clear` the
    stop row lands under the NEW session id while the sidecar stays under the
    OLD one, so a session-filtered settled set can never see the stop and the
    orphaned sidecar is reported pending past every threshold, forever.
    `agent_id` is globally unique by design, which is what makes the id alone a
    sound join; the worst a collision could cost is one missed stall row, never
    a false one.

    Bounded at `tail_bytes` (256 KB, ~800 rows). Edge cost, stated rather than
    hidden: a delegation whose stop row has aged out of that window looks
    un-stopped, so a still-present sidecar is reported pending once more before
    the next stall row re-suppresses it.

    A ledger that exists but cannot be READ raises, deliberately: see the
    module docstring. An absent ledger is not an error — nothing has settled
    because nothing has been recorded yet.
    """
    settled = set()
    path = agentlog.stream_path(LEDGER_STREAM, LEDGER_PATH_ENV)
    if not path or not os.path.isfile(path):
        return settled
    for line in read_tail(path, tail_bytes).split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        if "event" not in obj:
            # D7 reader rule: no `event` key means a delegation row. A debug
            # `error` row also lacks one, but carries no agent_id, so the
            # agent_key guard below drops it without a second predicate.
            key = agent_key(obj.get("agent_id"))
            if key:
                settled.add(key)
        elif obj.get("event") == STALL_EVENT:
            # Any session's stall row settles it — same uniqueness argument.
            for entry in obj.get("pending") or []:
                if isinstance(entry, dict):
                    key = agent_key(entry.get("agent_id"))
                    if key:
                        settled.add(key)
    return settled


def pending_keys(directory, extra_settled=None, tail_bytes=TAIL_BYTES):
    """Sorted agent_ids started in `directory` that the ledger has not settled."""
    settled = settled_ids(tail_bytes)
    if extra_settled:
        settled.update(k for k in extra_settled if k)
    return sorted(key for key in started_keys(directory) if key not in settled)
