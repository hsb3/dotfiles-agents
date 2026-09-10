#!/usr/bin/env python3
"""
subagent-telemetry — SubagentStop + Stop hook.

Appends one JSONL row per delegation (agent_id, agent_type, model,
ctx_tokens, started_at, duration_ms) to a local ledger so the plugin's own
tier usage AND per-agent wall clock can be measured offline (by a sibling
analysis script, e.g. delegation_stats.py) — data that is not otherwise
derivable from the parent transcript alone, since a subagent's type, model,
token usage and start time live only in the SUBAGENT's own sidecar +
transcript. It also appends a distinctly-shaped `stall` row when a delegation
this session started has still not settled past a threshold.

Purely observational: never blocks, never injects context, never prints
anything (telemetry is silent).

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

On-disk layout this hook reads (verified against real files under
~/.claude/projects, 2026-08):

  <projects>/<slug>/<session_id>.jsonl                            parent transcript
  <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
  <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

Sidecar keys observed: agentType (always), description, toolUseId,
spawnDepth, model (only when the dispatch overrode the model), parentAgentId,
worktreePath, worktreeBranch, name, isFork. There is NO token/usage data on
the sidecar, so ctx_tokens comes from the subagent's own transcript tail.

Contract (SubagentStop) — measured stdin fields: session_id, transcript_path,
cwd, hook_event_name, agent_id, agent_type, permission_mode.
  - `transcript_path` is the PARENT session's transcript, not the subagent's
    (observed: two sibling delegations reported byte-identical usage). Reading
    model/ctx_tokens off it describes the strategist, not the delegation — so
    it is used only to locate the sibling `subagents/` directory.
  - A prospective row is DROPPED unless a matching sidecar exists and yields
    an agent_type. SubagentStop also fires for agents that never get a
    `subagents/` entry; writing those inflated the ledger ~10x.
  - The sidecar is looked up in the payload's own `subagents/` dir first and,
    only on a miss, in sibling session dirs under the same slug (see
    `sidecar_dir` in `_lib/pending.py`, which owns the record layout this hook
    and `live-worker-git-guard` both read). A `/clear` mid-delegation re-homes
    the running agent's transcript under a NEW session id and leaves its
    sidecar behind under the OLD one — measured: one live agent, two session
    dirs, one sidecar. Without the fallback the delegation with the longest
    wall clock records nothing.
  - Then the stall scan runs.

Contract (Stop) — measured stdin fields: session_id, transcript_path, cwd,
hook_event_name, stop_hook_active. There is NO agent_id, which is how the
path is chosen: `hook_event_name == "Stop"`, or an absent/unusable agent_id,
means scan only. `stop_hook_active` needs no guard here — the hook emits no
decision and the scan is idempotent within a tail window.

Both paths: stdout NOTHING, ever (telemetry must not surface to the
user/agent); exit 0 always; fail-open on any internal error (missing or
unreadable sidecar/transcript/ledger, malformed stdin) by writing no row.

Start time (`started_at`, `duration_ms`), sourced by measurement over 11 real
delegations:
  - primary: the FIRST line of the subagent's own transcript that carries a
    non-empty `timestamp`, read from a bounded 64 KB head. It lands
    +0.04..+0.06s after true dispatch. Walking forward rather than taking
    line 0 is required: 4 of 44 real transcripts open with a
    `type: "fork-context-ref"` line that has no timestamp.
  - fallback: the sidecar's mtime, which tracked true dispatch to +0.1s in 9
    of 11 cases but blew out to +409s and +664s in the other two — which is
    exactly why it is the fallback and not the primary.
  - `duration_ms` is `now - started_at` at hook run time, so it is comparable
    with the envelope's own `ts`. Both keys are null when the start time is
    unknown; the row is still written, because losing a delegation record over
    a missing timestamp would be the bigger regression.
  - when a re-home has split the delegation across two dirs, the start stamp
    is read from the SIDECAR's half, which holds the true beginning. Session
    B's transcript is only the resumed tail, so sourcing it would restart the
    clock at the `/clear` and undercount `duration_ms` by everything before
    it. The consequence, taken deliberately: `duration_ms` for a re-homed
    delegation spans the clear, which is the honest wall clock. The usage tail
    is read the other way round — from the payload's own half, the live one
    carrying the delegation's final context.

Stall rule (the started/settled/pending sets themselves live in
`_lib/pending.py`; the threshold and the row shape are this hook's): the
STARTED universe is the `agent-*.meta.json` sidecars in the
session's `subagents/` dir — deliberately the same predicate that gates a
delegation row, so a phantom SubagentStop can never enter it. That universe is
the CURRENT dir only, and the asymmetry with the sidecar fallback above is
deliberate: widening it across siblings would sweep in every historical session
under the slug, whose stop rows aged out of the ledger tail long ago, and report
all of them stalled at every Stop. The SETTLED set comes from a bounded 256 KB
tail of the ledger: agent_ids on delegation rows, plus every agent_id inside the
`pending` list of a `stall` row (the dedup), plus whatever just stopped — all
matched by agent_id ALONE, regardless of session, because after a re-home the
stop row lands under a session id the orphaned sidecar's dir never sees.
Whatever is left and has been pending at least STALL_SECONDS produces ONE
`stall` row.
Edge cost of the 256 KB bound (~800 rows), stated rather than hidden: a
delegation whose stop row has aged out of the window looks un-stopped, so a
still-present sidecar past the threshold is named pending once more before
the new stall row re-suppresses it.

Row classification for readers: a row with NEITHER an `event` key NOR an
`error` key is a delegation row. Stall rows carry `event`; the opt-in
SUBAGENT_TELEMETRY_DEBUG rows carry `error` and no `event`, so `event` alone
does not separate them. That is exact for every row written before stall rows
existed; such rows simply also lack `started_at`/`duration_ms`, which is
honest — their start time was never recorded.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
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
import codex_lifecycle
import codex_usage
from pending import (  # noqa: E402  (same — `_lib` must be on the path first)
    AGENT_FILE_PREFIX,
    SIBLING_PROBE_LIMIT,  # noqa: F401  (re-export: the probe knob is read here)
    SIDECAR_SUFFIX,
    STALL_EVENT,
    TAIL_BYTES,
    TRANSCRIPT_SUFFIX,
    agent_key as _agent_key,
    env_int as _env_int,
    pending_keys as _pending_keys,
    read_sidecar as _read_sidecar,
    read_tail as _read_tail,
    sidecar_dir as _sidecar_dir,
    sidecar_path as _sidecar_path,
    subagents_dir as _subagents_dir,
)

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

# 64 KB is enough to reach the first timestamped line of a subagent transcript:
# the largest first-line end offset over 44 real transcripts was 16,558 bytes.
HEAD_BYTES = 64 * 1024
# A delegation still pending this long after it started is reported as stalled.
# 15 minutes: longer than any healthy delegation observed, short enough that a
# wedged worker surfaces inside one working session.
STALL_SECONDS_DEFAULT = 900
# Stream name is the stem this ledger already had (`delegation.jsonl`), not the
# hook name: the rows are the delegation record, and keeping the stem keeps old
# and new rows queryable as one series. Bound here as a literal rather than
# imported from `_lib/pending.py` (which reads the same ledger) because a
# stream name belongs to the hook that claims it — see the agentlog gate. The
# two are pinned equal by tests/test_live_worker_git_guard.py.
LOG_STREAM = "delegation"
LOG_PATH_ENV = "SUBAGENT_TELEMETRY_LOG_PATH"
USAGE_STREAM = "codex-usage"

STALL_SECONDS = _env_int("SUBAGENT_TELEMETRY_STALL_SECONDS", STALL_SECONDS_DEFAULT)


def _debug_enabled():
    """Diagnostics are opt-in: an unconditional error row would inflate a
    ledger whose row count is the thing being measured."""
    return os.environ.get("SUBAGENT_TELEMETRY_DEBUG", "").strip().lower() not in (
        "", "0", "false", "no",
    )


# ---------------------------------------------------------------------------
# Locating the delegation's own records — `_lib/pending.py` owns this half
# (`_subagents_dir`, `_agent_key`, `_sidecar_dir`, `_read_sidecar`, plus the
# started/settled/pending sets below), because `live-worker-git-guard` decides
# whether the tree is shared with a live worker from the SAME records and the
# two answers must not be able to disagree.
# ---------------------------------------------------------------------------

def _clean_str(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


# ---------------------------------------------------------------------------
# Transcript parsing — same tail-read approach as context-watermark/hook.py,
# extended to also pull the model off the same assistant message.
# ---------------------------------------------------------------------------

def _read_head(path, head_bytes):
    """Read only the first `head_bytes` of the file. Returns a str whose last
    line may be truncated; the caller parses per line and discards what fails."""
    with open(path, "rb") as f:
        data = f.read(head_bytes)
    return data.decode("utf-8", errors="replace")


def _find_last_assistant_model_and_usage(tail_text):
    """Scan tail lines (newest last) for the last assistant message that has
    a .message.usage block. Returns (model, usage) — either may be None.

    Transcript lines are JSONL; each line is a standalone JSON object. We
    walk from the end so the first usable line we find is the most recent.
    """
    lines = [ln for ln in tail_text.split("\n") if ln.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") != "assistant":
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if isinstance(usage, dict):
            model = message.get("model")
            return model, usage
    return None, None


def _context_tokens_from_usage(usage):
    """ctx = input_tokens + cache_creation_input_tokens + cache_read_input_tokens.

    Any missing field is treated as 0 (defensive: same assumption as
    context-watermark/hook.py — the three fields are not guaranteed present).
    """
    def _num(x):
        return x if isinstance(x, (int, float)) else 0

    return (
        _num(usage.get("input_tokens"))
        + _num(usage.get("cache_creation_input_tokens"))
        + _num(usage.get("cache_read_input_tokens"))
    )


def _read_model_and_ctx_tokens(transcript_path):
    """Best-effort: returns (model, ctx_tokens), either possibly None. Never
    raises — any failure (missing file, unreadable, malformed, no usage
    found) yields (None, None)."""
    try:
        if not transcript_path or not os.path.isfile(transcript_path):
            return None, None
        tail_text = _read_tail(transcript_path, TAIL_BYTES)
        model, usage = _find_last_assistant_model_and_usage(tail_text)
        if usage is None:
            return model, None
        return model, _context_tokens_from_usage(usage)
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Wall clock — when the delegation started, and how long it ran
# ---------------------------------------------------------------------------

def _iso_ms(moment):
    """`2026-08-20T15:37:08.666Z` — the exact shape agentlog stamps `ts` with,
    so `ts` and `started_at` are directly comparable as strings."""
    return (
        moment.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _parse_iso(text):
    """A tz-aware datetime from an ISO-8601 string, or None. Defensive: a
    transcript stamp is other software's output, so anything unparseable
    (wrong type, wrong shape, no digits) degrades to an unknown start time
    rather than an exception."""
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _first_transcript_timestamp(path):
    """Normalised start stamp from the transcript HEAD, or None.

    Walks lines from the FIRST forward rather than taking line 0: 4 of 44 real
    transcripts open with a `type: "fork-context-ref"` line carrying no
    `timestamp`. The first line that yields one wins — measured at +0.04..+0.06s
    after true dispatch, including in the two cases where sidecar mtime blew out.
    """
    for line in _read_head(path, HEAD_BYTES).split("\n"):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        moment = _parse_iso(obj.get("timestamp"))
        if moment is not None:
            return _iso_ms(moment)
    return None


def _started_at(subagents_dir, key):
    """When this delegation began, as an ISO-8601 UTC ms string, or None.

    Primary source is the subagent's own transcript. Fallback is the sidecar's
    mtime, and only a fallback: over 11 real delegations it tracked true
    dispatch to +0.1s in 9 but blew out to +409s and +664s in the other two.
    """
    base = os.path.join(subagents_dir, AGENT_FILE_PREFIX + key)
    try:
        transcript = base + TRANSCRIPT_SUFFIX
        if os.path.isfile(transcript):
            stamp = _first_transcript_timestamp(transcript)
            if stamp is not None:
                return stamp
    except Exception:
        pass
    try:
        return _iso_ms(datetime.fromtimestamp(
            os.path.getmtime(base + SIDECAR_SUFFIX), timezone.utc))
    except Exception:
        return None


def _elapsed_ms(started_at, now):
    """Whole milliseconds from `started_at` to `now`, or None if unknown."""
    moment = _parse_iso(started_at)
    if moment is None:
        return None
    return int((now - moment).total_seconds() * 1000)


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------

def _build_row(payload):
    """The ledger row for this SubagentStop, or None if it is not a delegation
    we can describe (in which case nothing is written at all).

    Every field is sourced from the delegation's own records: agent_type and
    any model override from its sidecar, model/ctx_tokens from its own
    transcript. The parent transcript contributes only the directory to look in.
    """
    key = _agent_key(payload.get("agent_id"))
    if key is None:
        return None

    subagents_dir = _subagents_dir(payload.get("transcript_path"))
    if subagents_dir is None:
        return None

    # Usually subagents_dir itself; a sibling session dir when a `/clear`
    # re-homed this delegation away from its sidecar.
    sidecar_dir = _sidecar_dir(subagents_dir, key)
    if sidecar_dir is None:
        return None

    meta = _read_sidecar(_sidecar_path(sidecar_dir, key))
    if meta is None:
        return None

    agent_type = _clean_str(meta.get("agentType")) or _clean_str(payload.get("agent_type"))
    if agent_type is None:
        # A row with no agent type is the defect this hook exists to fix.
        return None

    # When the two halves are split, they answer different questions. The
    # USAGE tail is read from the payload's own half, which is the live one
    # carrying the delegation's final context. The START stamp is read from
    # the sidecar's half, which holds the true beginning (see `_started_at`).
    # In the ordinary un-split case both are the same directory.
    transcript = os.path.join(
        subagents_dir, AGENT_FILE_PREFIX + key + TRANSCRIPT_SUFFIX)
    if not os.path.isfile(transcript):
        transcript = os.path.join(
            sidecar_dir, AGENT_FILE_PREFIX + key + TRANSCRIPT_SUFFIX)
    transcript_model, ctx_tokens = _read_model_and_ctx_tokens(transcript)
    # A sidecar `model` is the dispatch-time override — the delegation decision
    # itself — so it outranks whatever the transcript happens to name.
    model = _clean_str(meta.get("model")) or transcript_model

    # An unknown start time yields nulls, never a dropped row: losing the whole
    # delegation record over a missing timestamp would be the bigger regression.
    started_at = _started_at(sidecar_dir, key)

    return {
        "session_id": payload.get("session_id", "unknown"),
        "agent_id": key,
        "agent_type": agent_type,
        "model": model,
        "ctx_tokens": ctx_tokens,
        "started_at": started_at,
        "duration_ms": _elapsed_ms(started_at, datetime.now(timezone.utc)),
    }


# ---------------------------------------------------------------------------
# Stall detection — a delegation that started and never settled
# ---------------------------------------------------------------------------

def _stall_scan(payload, just_stopped_id):
    """Append AT MOST ONE stall row for delegations still pending past the
    threshold. Runs at the tail of both event paths.

    Wholly fail-open: any error anywhere writes no stall row, and because the
    scan runs after the delegation row is appended it can never cost one.
    """
    try:
        subagents_dir = _subagents_dir(payload.get("transcript_path"))
        if subagents_dir is None:
            return
        session_id = payload.get("session_id", "unknown")
        now = datetime.now(timezone.utc)
        pending = []
        for key in _pending_keys(subagents_dir, [just_stopped_id]):
            started_at = _started_at(subagents_dir, key)
            pending_ms = _elapsed_ms(started_at, now)
            if pending_ms is None or pending_ms < STALL_SECONDS * 1000:
                continue
            meta = _read_sidecar(_sidecar_path(subagents_dir, key)) or {}
            pending.append({
                "agent_id": key,
                "agent_type": _clean_str(meta.get("agentType")),
                "started_at": started_at,
                "pending_ms": pending_ms,
            })
        if not pending:
            return
        pending.sort(key=lambda entry: entry["agent_id"])
        agentlog.append(
            LOG_STREAM,
            {"event": STALL_EVENT, "session_id": session_id, "pending": pending},
            agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV,
        )
    except Exception:
        pass


def _is_stop_event(payload):
    """True for the session-level `Stop` payload, decided from the payload
    rather than trusted: a measured `Stop` carries session_id, transcript_path,
    cwd, hook_event_name and stop_hook_active — and no agent_id."""
    return (
        payload.get("hook_event_name") == "Stop"
        or _agent_key(payload.get("agent_id")) is None
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _codex_stop(payload):
    import codex_workers
    agent_id = payload.get("agent_id")
    if agent_id:
        record = codex_workers.lookup(payload)
        if record is None:
            raise ValueError("stopped worker has no registry record")
        row = {key: record.get(key) for key in
               ("session_id", "agent_id", "agent_type", "parent_agent_id", "worktree", "branch")}
        try:
            row.update(codex_lifecycle.measure(record.get("transcript_path")))
        except codex_lifecycle.PendingMeasurement:
            row.update(ctx_tokens=None, model=None, pending=True)
        except (OSError, ValueError) as exc:
            row.update(ctx_tokens=None, model=None, error=str(exc))
            codex_lifecycle.diagnostic(exc)
        row["duration_ms"] = _elapsed_ms(row.get("started_at"), datetime.now(timezone.utc))
        usage_payload = dict(payload, **record)
        usage = codex_usage.observe(record.get("transcript_path"), usage_payload, "child")
        agentlog.append_once(USAGE_STREAM, usage, usage["observation_id"],
                             agentlog.resolve_project(payload.get("cwd")), version=2)
        agentlog.append(LOG_STREAM, row, agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)
        codex_workers.set_status(payload, "stopped")
    elif payload.get("transcript_path"):
        usage = codex_usage.observe(payload["transcript_path"], payload, "root")
        agentlog.append_once(USAGE_STREAM, usage, usage["observation_id"],
                             agentlog.resolve_project(payload.get("cwd")), version=2)
    pending = []
    now = datetime.now(timezone.utc)
    for record in codex_workers.records(payload):
        if record.get("status") != "running":
            continue
        started = _first_transcript_timestamp(record.get("transcript_path"))
        elapsed = _elapsed_ms(started, now)
        if elapsed is not None and elapsed >= STALL_SECONDS * 1000:
            pending.append({"agent_id": record["agent_id"], "agent_type": record["agent_type"],
                            "started_at": started, "pending_ms": elapsed})
    if pending:
        agentlog.append(LOG_STREAM, {"event": STALL_EVENT,
            "session_id": payload.get("session_id"), "pending": pending},
            agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if isinstance(payload, dict):
            payload = codex_lifecycle.prepare(payload)
            if payload is None:
                return
        if not isinstance(payload, dict):
            sys.exit(0)

        if codex_lifecycle.enabled():
            _codex_stop(payload)
            return

        just_stopped_id = None
        if not _is_stop_event(payload):
            just_stopped_id = _agent_key(payload.get("agent_id"))
            row = _build_row(payload)
            if row is not None:
                agentlog.append(
                    LOG_STREAM, row,
                    agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV,
                )

        _stall_scan(payload, just_stopped_id)

        # Telemetry is silent: no stdout, ever. A `Stop` payload may carry
        # stop_hook_active — there is nothing to guard against, because this
        # hook emits no decision and the scan is idempotent within a window.
        sys.exit(0)

    except SystemExit:
        raise
    except Exception as e:
        if codex_lifecycle.enabled():
            codex_lifecycle.diagnostic(e)
        # Fail-open: never break the subagent-stop flow on our own error, and
        # never leave a partial row behind. Diagnostics only under an explicit
        # opt-in, so the ledger's row count stays equal to the delegation count.
        if _debug_enabled():
            try:
                agentlog.append(LOG_STREAM, {
                    "error": "{0}: {1}".format(type(e).__name__, e),
                    "traceback": traceback.format_exc(limit=3),
                }, agentlog.resolve_project(), LOG_PATH_ENV)
            except Exception:
                pass
        sys.exit(0)


if __name__ == "__main__":
    main()
