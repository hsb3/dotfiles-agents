"""Ingest the agent-harness run-log corpus into four PocketBase collections.

Loads `harness/results.jsonl` (the ledger, one row per trial) plus the raw per-trial
logs under `harness/runs/*.log` into `runs`, `run_events`, `tool_calls`, and
`artifacts`. Claude logs are stream-json (one event per line, separate
assistant/tool_use + user/tool_result events); opencode logs are JSONL with a single
fused `tool_use` event carrying call+result. Both normalize to the shared event model
in `harness/docs/runlog-data-shape.md` (the design of record).

The loader is standalone (never imports from `harness/`): it re-derives the 7-field
resume key (`campaign|harness|model|candidate|case|config|trial`) locally.

    python3 load_harness_runs.py --parse-only          # offline: counts + warnings, no DB
    python3 load_harness_runs.py --dry-run              # full plan vs live DB, writes nothing
    python3 load_harness_runs.py                        # ingest
    python3 load_harness_runs.py --campaign "" --candidate mermaid   # EDB-26 scoped pass

`--campaign` / `--candidate` scope BOTH the ledger rows considered AND the DB rows
diffed (EDB-26): nothing outside scope is read, diffed, or restamped. `--campaign ""`
scopes to the empty (legacy) label; omitting the flag applies no campaign filter.

Key Functions:
    parse_ledger(): read + scope the ledger into rows keyed by the 7-field composite.
    link_logs(): claim explicit `log_path` rows first, then prefix-match the rest to
        unclaimed log files (earliest timestamp on ambiguity; warn on 0 / >=2 matches).
    parse_claude_log() / parse_opencode_log(): raw log -> (era, session_id, events,
        tool_calls, blobs, rollup); drop thinking_tokens noise, dedup mirrors, excise
        base64 images + oversized writes to content-addressed artifacts.
    build_run_row(): ledger fields verbatim + log-derived era/session/provenance/rollup.
    plan(): scoped diff (create/update/unchanged per collection) against the live DB.

Limitations:
    - The live idempotency gate (a second ingest reporting 0 create / 0 update) can only
      be exercised against a running server; `--parse-only` is the offline verification.
    - `run_events.artifact` / `tool_calls.artifact` are single relations; an event that
      carried multiple artifacts (none in the current corpus) links only the first, with
      the full set recoverable from the `{"$artifact": <sha>}` markers in the payload.
    - Existing artifacts are matched (and never updated) by their unique `sha256`.
"""

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime

from pb import PB, esc

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_RESULTS = "harness/results.jsonl"
DEFAULT_RUNS_DIR = "harness/runs"

ARTIFACT_TEXT_THRESHOLD = 5000
TEXT_MAX = 5000
THINKING_SUBTYPE = "thinking_tokens"
LEGACY_TOOL_MAX = 5

KEY_FIELDS = ("campaign", "harness", "model", "candidate", "case", "config", "trial")
LEDGER_FIELDS = (
    "campaign", "harness", "model", "candidate", "case", "config", "trial", "kind",
    "grader_model", "passed", "skill_used", "exit_code", "num_turns", "cost_usd",
    "duration_ms", "input_tokens", "output_tokens", "cache_creation_tokens",
    "cache_read_tokens", "error", "workspace", "checks", "grades", "tool_names", "ts",
    "cli_version", "preconditions", "plugin_errors",
)
ROLLUP_FIELDS = (
    "cost_usd", "duration_ms", "input_tokens", "output_tokens", "cache_read_tokens",
    "cache_creation_tokens",
)
MEASUREMENT_FIELDS = (
    "passed", "skill_used", "exit_code", "num_turns", "cost_usd", "duration_ms",
    "input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens",
)
RESOURCE_METRICS = MEASUREMENT_FIELDS[3:]
PROVENANCE_KEYS = (
    "tools", "plugins", "slash_commands", "apiKeySource", "permissionMode",
    "capabilities", "memory_paths",
)

CLAUDE_ROLE = {"assistant": "assistant", "user": "tool_result", "system": "system",
               "result": "result"}
OC_ROLE = {"tool_use": "tool_call", "text": "assistant", "step_start": "system",
           "step_finish": "system"}
CLAUDE_WRITE_KEYS = (("content", "write_content"), ("new_string", "edit_diff"))
OC_WRITE_KEYS = (("content", "write_content"), ("newString", "edit_diff"))

CONTENT_DEDUP = {"$deduped": "content"}
DIFF_DEDUP = {"$deduped": "diff"}

RUN_JSON = {"checks", "grades", "tool_names", "model_usage", "provenance", "measurement"}
RUN_EVENT_FIELDS = (
    "seq", "ts", "vendor", "role", "event_type", "tool_name", "tool_call_id", "status",
    "is_error", "input_tokens", "output_tokens", "cache_read_tokens",
    "cache_write_tokens", "cost_usd", "wallclock_ms", "text", "payload",
)
EVENT_JSON = {"payload"}
TOOL_CALL_FIELDS = (
    "tool_call_id", "tool_name", "input", "output", "status", "is_error",
    "wallclock_ms", "started_ts",
)
TOOLCALL_JSON = {"input", "output"}


@dataclass
class Scope:
    campaign: str | None = None
    candidate: str | None = None


@dataclass
class Artifact:
    kind: str
    mime: str
    data: bytes
    sha256: str
    byte_size: int


@dataclass
class ParsedLog:
    era: str | None
    session_id: str
    events: list[dict]
    tool_calls: list[dict]
    blobs: list[Artifact]
    rollup: dict
    model_usage: object = None
    provenance: object = None
    log_sha256: str | None = None


@dataclass
class Aggregate:
    runs: dict[str, dict]
    events: list[tuple[str, dict]]
    tool_calls: list[tuple[str, dict]]
    artifacts: dict[str, tuple[Artifact, str]]  # sha -> (artifact, first-seen run key)
    era_counts: dict[str, int] = field(default_factory=dict)


# --- ledger + linkage ------------------------------------------------------------------

def run_key(row: dict) -> str:
    """Re-derive the harness resume key locally (campaign defaults to '')."""
    parts = []
    for f in KEY_FIELDS:
        parts.append(str(row.get("campaign", "")) if f == "campaign" else str(row.get(f)))
    return "|".join(parts)


def _in_scope(row: dict, scope: Scope) -> bool:
    if scope.campaign is not None and row.get("campaign", "") != scope.campaign:
        return False
    if scope.candidate is not None and row.get("candidate") != scope.candidate:
        return False
    return True


def parse_ledger(path: str, scope: Scope) -> dict[str, dict]:
    """Read the JSONL ledger into rows keyed by the 7-field composite, scoped."""
    rows: dict[str, dict] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if _in_scope(row, scope):
                rows[run_key(row)] = row
    return rows


def _log_prefix(row: dict) -> str:
    return (f"{row['harness']}-{row['candidate']}-{row['case']}-{row['config']}"
            f"-{row['trial']}-")


def link_logs(rows: dict[str, dict], runs_dir: str) -> tuple[dict[str, str | None], list[str]]:
    """Map each row to a log file. Explicit `log_path` claims are honored FIRST so
    post-era logs are off the table before legacy rows prefix-match the remainder."""
    warnings: list[str] = []
    on_disk = {fn for fn in _listdir(runs_dir) if fn.endswith(".log")}
    unclaimed = set(on_disk)
    links: dict[str, str | None] = {}
    for key, row in rows.items():
        lp = row.get("log_path")
        if lp:
            links[key] = lp
            unclaimed.discard(os.path.basename(lp))
    for key, row in rows.items():
        if key in links:
            continue
        prefix = _log_prefix(row)
        cands = sorted(fn for fn in unclaimed if fn.startswith(prefix))
        if not cands:
            links[key] = None
            warnings.append(f"no log matches prefix {prefix!r} (run ingested with empty log fields)")
            continue
        chosen = cands[0]  # YYYYMMDD-HHMMSS suffix sorts chronologically -> earliest
        if len(cands) > 1:
            warnings.append(f"ambiguous link for {prefix!r}: {len(cands)} candidates, picked earliest {chosen!r}")
        links[key] = os.path.join(runs_dir, chosen)
        unclaimed.discard(chosen)
    return links, warnings


def _listdir(runs_dir: str) -> list[str]:
    try:
        return os.listdir(runs_dir)
    except OSError:
        return []


def _repo_rel(path: str) -> str:
    try:
        return os.path.relpath(os.path.abspath(path), REPO)
    except ValueError:
        return path


# --- shared parse helpers --------------------------------------------------------------

def _raw_lines(text: str) -> list[dict | None]:
    out: list[dict | None] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            out.append(None)
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append(None)
    return out


def _trunc(value: object) -> str | None:
    return value[:TEXT_MAX] if isinstance(value, str) and value else None


def _iso_ms(ts: object) -> int | None:
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(dt.timestamp() * 1000)


def _base_row(seq: int, vendor: str, role: str, event_type: str, payload: dict,
              shas: list[str]) -> dict:
    return {
        "seq": seq, "ts": None, "vendor": vendor, "role": role,
        "event_type": event_type, "tool_name": None, "tool_call_id": None,
        "status": None, "is_error": None, "input_tokens": None, "output_tokens": None,
        "cache_read_tokens": None, "cache_write_tokens": None, "cost_usd": None,
        "wallclock_ms": None, "text": None, "payload": payload,
        "_artifact_shas": list(shas),
    }


def _record_image(b64: str, mime: str | None, blobs: list[Artifact]) -> str | None:
    try:
        data = base64.b64decode(b64)
    except (ValueError, binascii.Error):
        return None
    sha = hashlib.sha256(data).hexdigest()
    blobs.append(Artifact("screenshot", mime or "image/png", data, sha, len(data)))
    return sha


def _record_datauri(url: str, blobs: list[Artifact]) -> str | None:
    if "," not in url:
        return None
    header, b64 = url.split(",", 1)
    mime = header[5:].split(";", 1)[0] or "image/png"
    return _record_image(b64, mime, blobs)


def _record_text(content: str, kind: str, blobs: list[Artifact]) -> str:
    data = content.encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    blobs.append(Artifact(kind, "text/plain", data, sha, len(data)))
    return sha


def _externalize_write(inp: object, keys: tuple, blobs: list[Artifact]) -> list[str]:
    """Excise write/edit content over the text threshold to a text artifact."""
    shas: list[str] = []
    if not isinstance(inp, dict):
        return shas
    for key, kind in keys:
        v = inp.get(key)
        if isinstance(v, str) and len(v) > ARTIFACT_TEXT_THRESHOLD:
            sha = _record_text(v, kind, blobs)
            inp[key] = {"$artifact": sha}
            shas.append(sha)
    return shas


# --- claude parsing --------------------------------------------------------------------

def parse_claude_log(text: str) -> ParsedLog:
    """Parse claude stream-json: pair tool_use/tool_result by id, drop thinking noise."""
    raw = _raw_lines(text)
    era, session_id, provenance, model_usage = _claude_meta(raw)
    events: list[dict] = []
    blobs: list[Artifact] = []
    calls_list: list[dict] = []
    calls_by_id: dict[str, dict] = {}
    for seq, ev in enumerate(raw):
        if ev is None:
            continue
        etype, sub = ev.get("type"), ev.get("subtype")
        if etype == "system" and sub == THINKING_SUBTYPE:
            continue
        if etype == "assistant":
            cleaned, tool_uses, shas = _clean_claude_assistant(ev, blobs)
            _register_calls(calls_list, calls_by_id, tool_uses)
        elif etype == "user":
            cleaned, results, shas = _clean_claude_user(ev, blobs)
            _join_claude_results(calls_by_id, results, _iso_ms(ev.get("timestamp")))
        else:
            cleaned, shas = copy.deepcopy(ev), []
        events.append(_claude_event_row(cleaned, seq, shas))
    for call in calls_list:
        if call["status"] is None:
            call["status"] = "no_result"
    return ParsedLog(era, session_id, events, calls_list, blobs, {}, model_usage,
                     provenance)


def _claude_meta(raw: list[dict | None]) -> tuple[str, str, object, object]:
    era, session_id, provenance, model_usage = "post", "", None, None
    for ev in raw:
        if ev is None:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            session_id = ev.get("session_id", session_id)
            tools = ev.get("tools", [])
            era = "legacy" if isinstance(tools, list) and len(tools) <= LEGACY_TOOL_MAX else "post"
            provenance = {k: ev.get(k) for k in PROVENANCE_KEYS if k in ev}
        elif ev.get("type") == "result":
            model_usage = ev.get("modelUsage")
            session_id = session_id or ev.get("session_id", "")
    return era, session_id, provenance, model_usage


def _claude_event_row(ev: dict, seq: int, shas: list[str]) -> dict:
    etype, sub = ev.get("type"), ev.get("subtype")
    event_type = f"{etype}/{sub}" if sub else etype
    row = _base_row(seq, "claude", CLAUDE_ROLE.get(etype, "system"), event_type, ev, shas)
    if etype == "assistant":
        _enrich_claude_assistant(row, ev)
    elif etype == "user":
        row["ts"] = _iso_ms(ev.get("timestamp"))
        _enrich_claude_user(row, ev)
    elif etype == "result":
        row["text"] = _trunc(ev.get("result"))
    return row


def _enrich_claude_assistant(row: dict, ev: dict) -> None:
    msg = ev.get("message", {}) if isinstance(ev.get("message"), dict) else {}
    usage = msg.get("usage", {})
    if isinstance(usage, dict):
        row["input_tokens"] = usage.get("input_tokens")
        row["output_tokens"] = usage.get("output_tokens")
        row["cache_read_tokens"] = usage.get("cache_read_input_tokens")
        row["cache_write_tokens"] = usage.get("cache_creation_input_tokens")
    blocks = [b for b in msg.get("content", []) if isinstance(b, dict)]
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    if texts:
        row["text"] = _trunc("".join(texts))
    tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
    if len(tool_uses) == 1:
        row["tool_name"] = tool_uses[0].get("name")
        row["tool_call_id"] = tool_uses[0].get("id")


def _enrich_claude_user(row: dict, ev: dict) -> None:
    msg = ev.get("message", {}) if isinstance(ev.get("message"), dict) else {}
    results = [b for b in msg.get("content", []) if isinstance(b, dict) and b.get("type") == "tool_result"]
    if len(results) == 1:
        row["tool_call_id"] = results[0].get("tool_use_id")
        row["is_error"] = bool(results[0].get("is_error"))


def _clean_claude_assistant(ev: dict, blobs: list[Artifact]) -> tuple[dict, list[dict], list[str]]:
    ev = copy.deepcopy(ev)
    msg = ev.get("message", {}) if isinstance(ev.get("message"), dict) else {}
    tool_uses: list[dict] = []
    shas: list[str] = []
    for b in msg.get("content", []):
        if not isinstance(b, dict) or b.get("type") != "tool_use":
            continue
        inp = b.get("input")
        block_shas = _externalize_write(inp, CLAUDE_WRITE_KEYS, blobs)
        shas += block_shas
        tool_uses.append({"id": b.get("id"), "name": b.get("name"), "input": inp,
                          "shas": block_shas})
    return ev, tool_uses, shas


def _clean_claude_user(ev: dict, blobs: list[Artifact]) -> tuple[dict, dict, list[str]]:
    ev = copy.deepcopy(ev)
    msg = ev.get("message", {}) if isinstance(ev.get("message"), dict) else {}
    canonical: set[str] = set()
    results: dict[str, dict] = {}
    shas: list[str] = []
    for b in msg.get("content", []):
        if not isinstance(b, dict) or b.get("type") != "tool_result":
            continue
        block_shas = _excise_claude_images(b.get("content"), blobs)
        shas += block_shas
        if isinstance(b.get("content"), str):
            canonical.add(b["content"])
        results[b.get("tool_use_id")] = {"output": b.get("content"),
                                         "is_error": bool(b.get("is_error")),
                                         "shas": block_shas}
    tur = ev.get("tool_use_result")
    if isinstance(tur, dict):
        shas += _clean_tool_use_result(tur, canonical, blobs)
    return ev, results, shas


def _excise_claude_images(content: object, blobs: list[Artifact]) -> list[str]:
    shas: list[str] = []
    if not isinstance(content, list):
        return shas
    for cc in content:
        if not isinstance(cc, dict) or cc.get("type") != "image":
            continue
        src = cc.get("source")
        if isinstance(src, dict) and src.get("data"):
            sha = _record_image(src["data"], src.get("media_type"), blobs)
            if sha:
                src["data"] = {"$artifact": sha}
                shas.append(sha)
    return shas


def _clean_tool_use_result(tur: dict, canonical: set[str], blobs: list[Artifact]) -> list[str]:
    """Excise the mirrored base64 image, then replace byte-identical mirror leaves
    (e.g. .stdout duplicating the tool_result content) with a dedup marker."""
    shas: list[str] = []
    fil = tur.get("file")
    if isinstance(fil, dict) and isinstance(fil.get("base64"), str) and fil["base64"]:
        sha = _record_image(fil["base64"], "image/png", blobs)
        if sha:
            fil["base64"] = {"$artifact": sha}
            shas.append(sha)
    _dedup_mirror(tur, canonical)
    return shas


def _dedup_mirror(obj: object, canonical: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str) and v in canonical:
                obj[k] = dict(CONTENT_DEDUP)
            else:
                _dedup_mirror(v, canonical)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str) and v in canonical:
                obj[i] = dict(CONTENT_DEDUP)
            else:
                _dedup_mirror(v, canonical)


def _register_calls(calls_list: list[dict], calls_by_id: dict[str, dict],
                    tool_uses: list[dict]) -> None:
    for tu in tool_uses:
        call = {"tool_call_id": tu["id"], "tool_name": tu["name"], "input": tu["input"],
                "output": None, "status": None, "is_error": None, "wallclock_ms": None,
                "started_ts": None, "_artifact_shas": list(tu["shas"])}
        calls_list.append(call)
        if tu["id"]:
            calls_by_id[tu["id"]] = call


def _join_claude_results(calls_by_id: dict[str, dict], results: dict[str, dict],
                         ts_ms: int | None) -> None:
    for tid, r in results.items():
        call = calls_by_id.get(tid)
        if call is None:
            continue
        call["output"] = r["output"]
        call["is_error"] = r["is_error"]
        call["status"] = "error" if r["is_error"] else "ok"
        call["started_ts"] = ts_ms
        call["_artifact_shas"] += r["shas"]


# --- opencode parsing ------------------------------------------------------------------

def parse_opencode_log(text: str) -> ParsedLog:
    """Parse opencode JSONL: each fused tool_use is one call; sum step_finish rollup."""
    raw = _raw_lines(text)
    session_id = ""
    events: list[dict] = []
    tool_calls: list[dict] = []
    blobs: list[Artifact] = []
    costs: list[float] = []
    token_steps: list[dict] = []
    ts_list: list[int] = []
    for seq, ev in enumerate(raw):
        if ev is None:
            continue
        session_id = session_id or ev.get("sessionID", "")
        etype = ev.get("type")
        ts = ev.get("timestamp")
        if isinstance(ts, int):
            ts_list.append(ts)
        cleaned = copy.deepcopy(ev)
        row = _base_row(seq, "opencode", OC_ROLE.get(etype, "system"), etype, cleaned, [])
        row["ts"] = ts if isinstance(ts, int) else None
        if etype == "tool_use":
            call = _opencode_tool(cleaned, blobs)
            row["_artifact_shas"] = list(call["_artifact_shas"])
            _mirror_call_onto_event(row, call)
            tool_calls.append(call)
        elif etype == "text":
            part = ev.get("part", {})
            row["text"] = _trunc(part.get("text") if isinstance(part, dict) else None)
        elif etype == "step_finish":
            _enrich_step_finish(row, ev, costs, token_steps)
        events.append(row)
    rollup = _opencode_rollup(costs, token_steps, ts_list)
    return ParsedLog("na", session_id, events, tool_calls, blobs, rollup)


def _opencode_tool(ev: dict, blobs: list[Artifact]) -> dict:
    part = ev.get("part", {}) if isinstance(ev.get("part"), dict) else {}
    st = part.get("state", {}) if isinstance(part.get("state"), dict) else {}
    shas: list[str] = []
    _dedup_opencode_diff(st)
    shas += _excise_opencode_images(st, blobs)
    shas += _externalize_write(st.get("input"), OC_WRITE_KEYS, blobs)
    tspan = st.get("time") if isinstance(st.get("time"), dict) else {}
    wall = None
    start, end = tspan.get("start"), tspan.get("end")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        wall = end - start
    status = st.get("status")
    return {"tool_call_id": part.get("callID"), "tool_name": part.get("tool"),
            "input": st.get("input"), "output": st.get("output"), "status": status,
            "is_error": status == "error", "wallclock_ms": wall,
            "started_ts": start if isinstance(start, (int, float)) else None,
            "_artifact_shas": shas}


def _dedup_opencode_diff(st: dict) -> None:
    md = st.get("metadata")
    if not isinstance(md, dict):
        return
    fd = md.get("filediff")
    if isinstance(fd, dict) and isinstance(fd.get("patch"), str) and fd["patch"] == md.get("diff"):
        fd["patch"] = dict(DIFF_DEDUP)


def _excise_opencode_images(st: dict, blobs: list[Artifact]) -> list[str]:
    shas: list[str] = []
    for a in st.get("attachments") or []:
        if isinstance(a, dict) and isinstance(a.get("url"), str) and a["url"].startswith("data:"):
            sha = _record_datauri(a["url"], blobs)
            if sha:
                a["url"] = {"$artifact": sha}
                shas.append(sha)
    return shas


def _mirror_call_onto_event(row: dict, call: dict) -> None:
    for f in ("tool_name", "tool_call_id", "status", "is_error", "wallclock_ms"):
        row[f] = call[f]


def _enrich_step_finish(row: dict, ev: dict, costs: list[float],
                        token_steps: list[dict]) -> None:
    part = ev.get("part", {}) if isinstance(ev.get("part"), dict) else {}
    cost = part.get("cost")
    if isinstance(cost, (int, float)):
        costs.append(cost)
        row["cost_usd"] = cost
    toks = part.get("tokens", {})
    if isinstance(toks, dict):
        token_steps.append(toks)
        row["input_tokens"] = toks.get("input")
        row["output_tokens"] = toks.get("output")
        cache = toks.get("cache") if isinstance(toks.get("cache"), dict) else {}
        row["cache_read_tokens"] = cache.get("read")
        row["cache_write_tokens"] = cache.get("write")


def _opencode_rollup(costs: list[float], token_steps: list[dict],
                     ts_list: list[int]) -> dict:
    def _sum(getter) -> int:
        total = 0
        for t in token_steps:
            v = getter(t)
            if isinstance(v, (int, float)):
                total += v
        return total

    def _cache(t: dict, key: str) -> object:
        cache = t.get("cache")
        return cache.get(key) if isinstance(cache, dict) else None

    return {
        "cost_usd": sum(costs) if costs else None,
        "input_tokens": _sum(lambda t: t.get("input")),
        "output_tokens": _sum(lambda t: t.get("output")),
        "cache_read_tokens": _sum(lambda t: _cache(t, "read")),
        "cache_creation_tokens": _sum(lambda t: _cache(t, "write")),
        "duration_ms": (max(ts_list) - min(ts_list)) if ts_list else None,
    }


# --- run rows + aggregation ------------------------------------------------------------

def _parse_log_file(row: dict, fspath: str | None) -> ParsedLog | None:
    if not fspath or not os.path.isfile(fspath):
        return None
    with open(fspath, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")
    if row.get("harness") == "opencode":
        parsed = parse_opencode_log(text)
    else:
        parsed = parse_claude_log(text)
    parsed.log_sha256 = hashlib.sha256(raw).hexdigest()
    return parsed


def build_run_row(row: dict, parsed: ParsedLog | None, log_rel: str | None) -> dict:
    """The `runs` body: ledger fields verbatim + log-derived era/session/provenance;
    opencode fills token/cost/duration it lacks from the step rollup (ledger wins)."""
    body = {f: row.get(f) for f in LEDGER_FIELDS}
    body["campaign"] = row.get("campaign", "") or ""
    body["case"] = row.get("case")
    body["log_path"] = log_rel
    if parsed is None:
        body["era"] = "na" if row.get("harness") == "opencode" else None
        body["session_id"] = ""
    else:
        body["era"] = parsed.era
        body["session_id"] = parsed.session_id or ""
        body["model_usage"] = parsed.model_usage
        body["provenance"] = parsed.provenance
        if parsed.era == "na":
            _fill_from_rollup(body, parsed.rollup)
    _validate_metrics(body)
    body["measurement"] = _measurement(row, body, parsed)
    return body


def _fill_from_rollup(body: dict, rollup: dict) -> None:
    for f in ROLLUP_FIELDS:
        if body.get(f) is None and rollup.get(f) is not None:
            body[f] = rollup[f]


def _validate_metrics(body: dict) -> None:
    exit_code = body.get("exit_code")
    if exit_code is not None and type(exit_code) is not int:
        raise ValueError("exit_code must be an integer")
    for field in RESOURCE_METRICS:
        value = body.get(field)
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{field} must be a finite nonnegative int or float")


def _record_sha256(row: dict) -> str:
    source = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _preconditions_valid(value: object) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    strings = ("harness", "cli_version", "model", "campaign", "network_assumption")
    if any(type(value.get(key)) is not str for key in strings):
        return False
    if "grader_model" not in value:
        return False
    if value["grader_model"] is not None and type(value["grader_model"]) is not str:
        return False
    timeout = value.get("timeout")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
        return False
    for key in ("auth_env_present", "self_installs"):
        if not isinstance(value.get(key), list) or any(type(item) is not str for item in value[key]):
            return False
    return True


def _execution(row: dict) -> dict:
    preconditions = row.get("preconditions")
    plugin_errors = row.get("plugin_errors")
    error = row.get("error")
    exit_code = row.get("exit_code")
    execution = {"preconditions": preconditions if isinstance(preconditions, dict) else None,
                 "plugin_errors": plugin_errors}
    if exit_code is not None and exit_code != 0:
        return dict(execution, validity="invalid", reason="producer exit_code was nonzero")
    if isinstance(plugin_errors, list) and plugin_errors:
        return dict(execution, validity="invalid", reason="producer recorded plugin_errors")
    if (row.get("passed") is None and isinstance(error, str)
            and error.startswith("unsupported:")):
        return dict(execution, validity="skipped", reason="explicit unsupported producer row")
    if isinstance(error, str) and error:
        return dict(execution, validity="invalid", reason="producer recorded error")
    if type(row.get("passed")) is not bool:
        return dict(execution, validity="unknown", reason="passed was not an explicit boolean")
    if exit_code != 0:
        return dict(execution, validity="unknown", reason="exit_code was not explicitly zero")
    if not isinstance(plugin_errors, list):
        return dict(execution, validity="unknown", reason="plugin_errors were not recorded")
    if not _preconditions_valid(preconditions):
        return dict(execution, validity="unknown", reason="preconditions were missing or malformed")
    return dict(execution, validity="valid", reason="producer recorded completed run evidence")


def _measurement(row: dict, body: dict, parsed: ParsedLog | None) -> dict:
    available = {field: body.get(field) is not None for field in MEASUREMENT_FIELDS}
    provenance = {}
    for field in MEASUREMENT_FIELDS:
        if row.get(field) is not None:
            provenance[field] = "ledger"
        elif field in ROLLUP_FIELDS and body.get(field) is not None:
            provenance[field] = "log-rollup"
        else:
            provenance[field] = None
    log_sha256 = parsed.log_sha256 if parsed is not None else None
    if log_sha256 is not None:
        log_observation = "observed"
    elif row.get("passed") is None and isinstance(row.get("error"), str) and row["error"].startswith("unsupported:"):
        log_observation = "absent"
    else:
        log_observation = "unobserved-local"
    return {
        "version": 1,
        "source": "harness-ledger",
        "available": available,
        "provenance": provenance,
        "execution": _execution(row),
        "source_identity": {
            "record_sha256": _record_sha256(row),
            "record_canonicalization": "json-sorted-keys-utf8",
            "log_sha256": log_sha256,
            "log_available": log_sha256 is not None,
            "log_observation": log_observation,
            "revision": {"value": None, "available": False},
        },
    }


def build_aggregate(rows: dict[str, dict], links: dict[str, str | None]) -> Aggregate:
    """Parse each linked log and fan out into the four collections; artifacts are
    globally sha-deduped with the first-seen run winning the `run` relation."""
    runs: dict[str, dict] = {}
    events: list[tuple[str, dict]] = []
    tool_calls: list[tuple[str, dict]] = []
    artifacts: dict[str, tuple[Artifact, str]] = {}
    era_counts: dict[str, int] = {"legacy": 0, "post": 0, "na": 0}
    for key, row in rows.items():
        fspath = links.get(key)
        parsed = _parse_log_file(row, fspath)
        log_rel = _repo_rel(fspath) if fspath else row.get("log_path")
        runs[key] = build_run_row(row, parsed, log_rel)
        if parsed is None:
            continue
        era_counts[parsed.era] = era_counts.get(parsed.era, 0) + 1
        events.extend((key, ev) for ev in parsed.events)
        tool_calls.extend((key, c) for c in parsed.tool_calls)
        for art in parsed.blobs:
            artifacts.setdefault(art.sha256, (art, key))
    return Aggregate(runs, events, tool_calls, artifacts, era_counts)


# --- plan + apply ----------------------------------------------------------------------

def _scope_filter(scope: Scope) -> str | None:
    parts = []
    if scope.campaign is not None:
        parts.append(f"campaign='{esc(scope.campaign)}'")
    if scope.candidate is not None:
        parts.append(f"candidate='{esc(scope.candidate)}'")
    return " && ".join(parts) or None


def _nonnull(body: dict) -> dict:
    return {k: v for k, v in body.items() if v is not None}


_JSON_START = set('{["-0123456789tfn')


def _coerce_json(value: object) -> object:
    """Mirror PocketBase's json-field coercion at body-build time.

    PB parses a string it receives for a `json` field only when its UNTRIMMED first
    byte can start a JSON value ('{', '[', '"', '-', digit, or the t/f/n of
    true/false/null) and the whole string then parses; it stores the PARSED value.
    Live-corpus proof of the first-byte rule: '7853\\n' (digit first, trailing
    newline) came back as int 7853, while '     266' (space first) stayed a verbatim
    string. Sending the same form PB stores keeps re-ingest diffs at unchanged
    instead of flagging every JSON-string output forever. Non-strings and unparseable
    strings pass through untouched."""
    if not isinstance(value, str) or not value or value[0] not in _JSON_START:
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def _coerce_body(body: dict, json_fields: set[str]) -> dict:
    return {k: (_coerce_json(v) if k in json_fields else v) for k, v in body.items()}


def _json_norm(value: object) -> object:
    if value is None or value == "":
        return None
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _scalar_norm(value: object) -> object:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def _changed(rec: dict, body: dict, json_fields: set[str]) -> bool:
    for k, v in body.items():
        measurement = body.get("measurement")
        if (k in MEASUREMENT_FIELDS and isinstance(measurement, dict)
                and measurement.get("available", {}).get(k) is False):
            continue
        if k in ("run", "artifact"):
            if str(rec.get(k) or "") != str(v or ""):
                return True
        elif k in json_fields:
            if _json_norm(rec.get(k)) != _json_norm(v):
                return True
        elif _scalar_norm(rec.get(k)) != _scalar_norm(v):
            return True
    return False


def _first_artifact_id(shas: list[str] | None, sha_map: dict[str, str]) -> str | None:
    for sha in shas or []:
        if sha in sha_map:
            return sha_map[sha]
    return None


def _existing_runs(pb: PB, scope: Scope) -> dict[str, dict]:
    return {run_key(r): r for r in pb.list_all("runs", _scope_filter(scope))}


def _apply_runs(pb: PB, runs: dict[str, dict], existing: dict[str, dict],
                dry_run: bool) -> tuple[dict[str, str | None], tuple[int, int, int]]:
    run_id_map: dict[str, str | None] = {}
    created = updated = unchanged = 0
    for key, body in runs.items():
        db_body = _nonnull(_coerce_body(body, RUN_JSON))
        db_body.pop("preconditions", None)
        db_body.pop("plugin_errors", None)
        for field in MEASUREMENT_FIELDS:
            if body.get(field) is None:
                db_body[field] = None
        rec = existing.get(key)
        if rec is not None:
            _preserve_unobserved_log_fields(db_body, rec)
            _preserve_observed_log_identity(db_body, rec)
        if rec is None:
            created += 1
            run_id_map[key] = pb.create("runs", db_body)["id"] if not dry_run else None
        else:
            run_id_map[key] = rec["id"]
            if _changed(rec, db_body, RUN_JSON):
                updated += 1
                if not dry_run:
                    pb.update("runs", rec["id"], db_body)
            else:
                unchanged += 1
    return run_id_map, (created, updated, unchanged)


def _preserve_unobserved_log_fields(body: dict, rec: dict) -> None:
    measurement = body.get("measurement", {})
    current = measurement.get("source_identity", {})
    if current.get("log_observation") != "unobserved-local":
        return
    if rec.get("session_id"):
        body["session_id"] = rec["session_id"]
    if rec.get("era"):
        body["era"] = rec["era"]
    available = measurement.get("available", {})
    provenance = measurement.get("provenance", {})
    previous = rec.get("measurement", {})
    previous_available = previous.get("available", {}) if isinstance(previous, dict) else {}
    previous_provenance = previous.get("provenance", {}) if isinstance(previous, dict) else {}
    for field in MEASUREMENT_FIELDS:
        if available.get(field) is False and rec.get(field) is not None:
            body[field] = rec[field]
            if (previous_available.get(field) is True
                    and previous_provenance.get(field) == "log-rollup"):
                available[field] = True
                provenance[field] = "log-rollup"


def _preserve_observed_log_identity(body: dict, rec: dict) -> None:
    """A logless local checkout cannot disprove already-ingested log evidence."""
    current = body.get("measurement")
    previous = rec.get("measurement")
    if not isinstance(current, dict) or not isinstance(previous, dict):
        return
    current_id = current.get("source_identity")
    previous_id = previous.get("source_identity")
    if (not isinstance(current_id, dict) or not isinstance(previous_id, dict)
            or current_id.get("log_observation") != "unobserved-local"
            or previous_id.get("log_observation") != "observed"
            or not previous_id.get("log_sha256")):
        return
    current_id["log_sha256"] = previous_id["log_sha256"]
    current_id["log_available"] = True
    current_id["log_observation"] = "observed"


def _apply_artifacts(pb: PB, artifacts: dict[str, tuple[Artifact, str]],
                     run_id_map: dict[str, str | None], existing: dict[str, dict],
                     dry_run: bool) -> tuple[dict[str, str], tuple[int, int, int]]:
    sha_map: dict[str, str] = {}
    created = unchanged = 0
    for sha, (art, key) in artifacts.items():
        if sha in existing:
            sha_map[sha] = existing[sha]["id"]
            unchanged += 1
            continue
        created += 1
        run_id = run_id_map.get(key)
        if dry_run or run_id is None:
            continue
        body = {"run": run_id, "kind": art.kind, "mime": art.mime, "sha256": art.sha256,
                "byte_size": art.byte_size}
        if art.kind != "screenshot":
            body["text_ref"] = art.data.decode("utf-8", "replace")[:TEXT_MAX]
        files = {"blob": (_artifact_filename(art), art.data, art.mime)}
        sha_map[sha] = pb.create_multipart("artifacts", body, files)["id"]
    return sha_map, (created, 0, unchanged)


def _artifact_filename(art: Artifact) -> str:
    ext = "png" if art.kind == "screenshot" else "txt"
    return f"{art.sha256[:12]}.{ext}"


def _existing_artifacts_by_sha(pb: PB, shas: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sha in shas:
        rec = pb.find_first("artifacts", f"sha256='{esc(sha)}'")
        if rec:
            out[sha] = rec
    return out


def _child_body(row: dict, run_id: str | None, sha_map: dict[str, str],
                fields: tuple, json_fields: set[str]) -> dict:
    body = _coerce_body({f: row.get(f) for f in fields}, json_fields)
    if run_id is not None:
        body["run"] = run_id
    art = _first_artifact_id(row.get("_artifact_shas"), sha_map)
    if art:
        body["artifact"] = art
    return _nonnull(body)


def _apply_children(pb: PB, coll: str, items: list[tuple[str, dict]],
                    run_id_map: dict[str, str | None], sha_map: dict[str, str],
                    existing_runs: dict[str, dict], nat_key, fields: tuple,
                    json_fields: set[str], dry_run: bool) -> tuple[int, int, int]:
    existing = _existing_children(pb, coll, existing_runs, nat_key)
    created = updated = unchanged = 0
    for key, row in items:
        run_id = run_id_map.get(key)
        body = _child_body(row, run_id, sha_map, fields, json_fields)
        if run_id is None:
            created += 1
            continue
        rec = existing.get(nat_key(run_id, row))
        if rec is None:
            created += 1
            if not dry_run:
                pb.create(coll, body)
        elif _changed(rec, body, json_fields):
            updated += 1
            if not dry_run:
                pb.update(coll, rec["id"], body)
        else:
            unchanged += 1
    return created, updated, unchanged


def _existing_children(pb: PB, coll: str, existing_runs: dict[str, dict],
                       nat_key) -> dict:
    idx: dict = {}
    for rec in existing_runs.values():
        for child in pb.list_all(coll, f"run='{esc(rec['id'])}'"):
            idx[nat_key(rec["id"], child)] = child
    return idx


def _event_key(run_id: str, row: dict):
    return run_id, row.get("seq")


def _toolcall_key(run_id: str, row: dict):
    return run_id, row.get("tool_call_id")


def plan(pb: PB, agg: Aggregate, scope: Scope, dry_run: bool) -> dict[str, tuple]:
    """Diff the aggregate against the scoped live DB, applying unless dry_run.
    Creation order: runs -> artifacts -> run_events -> tool_calls (children need the
    created run ids; events/tool_calls need the sha -> artifact-id map)."""
    existing_runs = _existing_runs(pb, scope)
    run_id_map, run_counts = _apply_runs(pb, agg.runs, existing_runs, dry_run)
    existing_arts = _existing_artifacts_by_sha(pb, list(agg.artifacts))
    sha_map, art_counts = _apply_artifacts(pb, agg.artifacts, run_id_map, existing_arts,
                                           dry_run)
    ev_counts = _apply_children(pb, "run_events", agg.events, run_id_map, sha_map,
                                existing_runs, _event_key, RUN_EVENT_FIELDS, EVENT_JSON,
                                dry_run)
    tc_counts = _apply_children(pb, "tool_calls", agg.tool_calls, run_id_map, sha_map,
                                existing_runs, _toolcall_key, TOOL_CALL_FIELDS,
                                TOOLCALL_JSON, dry_run)
    return {"runs": run_counts, "artifacts": art_counts, "run_events": ev_counts,
            "tool_calls": tc_counts}


# --- CLI -------------------------------------------------------------------------------

def _print_parse_summary(agg: Aggregate, warnings: list[str]) -> None:
    screenshots = sum(1 for a, _ in agg.artifacts.values() if a.kind == "screenshot")
    text_arts = len(agg.artifacts) - screenshots
    referenced = sum(1 for b in agg.runs.values() if b.get("log_path"))
    observed = sum(
        1 for b in agg.runs.values()
        if b.get("measurement", {}).get("source_identity", {}).get("log_observation") == "observed"
    )
    print("[parse-only] planned records (no DB connection):")
    print(f"  runs:        {len(agg.runs)}")
    print(f"  run_events:  {len(agg.events)}")
    print(f"  tool_calls:  {len(agg.tool_calls)}")
    print(f"  artifacts:   {len(agg.artifacts)} post-dedup "
          f"({screenshots} screenshot, {text_arts} text)")
    print(f"  runs with log reference: {referenced}/{len(agg.runs)}")
    print(f"  runs with observed log bytes: {observed}/{len(agg.runs)}")
    print("  era split:   " + ", ".join(f"{k}={v}" for k, v in agg.era_counts.items()))
    if warnings:
        print(f"  warnings ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")
    else:
        print("  warnings:    none")


def _print_plan(counts: dict[str, tuple], dry_run: bool) -> None:
    verb = "[dry-run] plan" if dry_run else "ingested"
    print(f"{verb} (create / update / unchanged):")
    for coll in ("runs", "artifacts", "run_events", "tool_calls"):
        c, u, n = counts[coll]
        print(f"  {coll:11} {c} create / {u} update / {n} unchanged")
    if dry_run:
        print("  no writes made")


def _build_scope(args: argparse.Namespace) -> Scope:
    return Scope(campaign=args.campaign, candidate=args.candidate)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Ingest the agent-harness run-log corpus (ledger + raw logs) into "
                    "the runs/run_events/tool_calls/artifacts PocketBase collections."
    )
    ap.add_argument("--results", default=DEFAULT_RESULTS, help="ledger JSONL path")
    ap.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR, help="raw log directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="full plan against the live DB; write nothing")
    ap.add_argument("--parse-only", action="store_true",
                    help="parse + link + print planned counts and warnings; no DB")
    ap.add_argument("--campaign", default=None,
                    help="scope to a campaign label ('' = the empty/legacy label)")
    ap.add_argument("--candidate", default=None, help="scope to a candidate")
    args = ap.parse_args(argv)

    scope = _build_scope(args)
    try:
        rows = parse_ledger(args.results, scope)
    except OSError as e:
        print(f"cannot read ledger: {e}")
        return 1
    if not rows:
        print("no ledger rows in scope; nothing to do")
        return 0

    links, warnings = link_logs(rows, args.runs_dir)
    agg = build_aggregate(rows, links)

    if args.parse_only:
        _print_parse_summary(agg, warnings)
        return 0

    if warnings:
        print(f"linkage warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    pb = PB()
    counts = plan(pb, agg, scope, args.dry_run)
    _print_plan(counts, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
