#!/usr/bin/env python3
"""Subagent quiet-time attribution — which tool call each long gap was spent inside.

The delegation ledger says only that a subagent was quiet; the transcript says why.
A gap's cause is the last `tool_use` block preceding it: an agent goes silent because
it made a blocking call, and that call is on disk with its arguments. This script
replays every subagent transcript, attributes each gap >= threshold to that preceding
call, and separates the recoverable kind of dead time (a self-commanded `sleep` that
cannot end early) from the unrecoverable kind (a child's genuine work) and from the
genuinely unattributed remainder.

Read-only, stdlib-only, deterministic: stable ordering, no clocks, no random, no
network. Nothing is written anywhere.

On-disk layout it walks (same layout the subagent-telemetry hook reads):

    <root>/<slug>/<session_id>/subagents/agent-<id>.jsonl

Transcript shape, verified 2026-09-02 against 4,555 real transcripts under
~/.claude/projects (400-transcript census: 20,807 `assistant`, 12,388 `user`, 1,152
`attachment`, 23 `fork-context-ref` events; 0 unparseable lines):

  * one JSON object per line; every event carries a `timestamp` (`...Z`, ms precision)
    EXCEPT `fork-context-ref` lines, which carry none and are skipped.
  * tool calls appear exactly as assumed:
    {"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash",
     "input":{"command":"..."}}, ...]}}
    with 11,935 `tool_use` blocks against 11,935 `tool_result` blocks in the census.
  * observed tool names: Bash, Read, Edit, Write, Grep, Glob, Agent, WebFetch,
    WebSearch, ToolSearch, SendMessage, Skill, Monitor, TaskStop (and one lowercase
    `bash`, which is treated as `Bash`).

Bucketing:

  * cause = the tool name of the last `tool_use` block in the last assistant event at
    or before the gap's start, or `none` when no tool_use precedes it (model latency,
    or a gap before the first call — reported as "unexplained", never rounded away).
  * `Agent` gaps are a child's genuine work and stay in their own bucket.
  * a gap is `in_call` when it starts AT the assistant event that issued the call (the
    call had not returned yet) and post-call otherwise. Both land in the same cause
    bucket, per the rule above, but the distinction is load-bearing and measured: on the
    real corpus most `Bash` gap time is POST-call — e.g. a 7,220s gap charged to
    `git diff` began after that diff's tool_result, so it is model/queue/idle latency,
    not the tool. Read the plain `Bash`/`Read`/`Edit` rows as an upper bound on tool
    cost and the in-call column as the part that was demonstrably inside the call.
  * `Bash` splits three ways: plain `Bash`, `Bash:sleep-poll` and
    `Bash:sleep-unconditional`. A command is a sleep bucket when a `sleep` call is
    reachable in it; it is a poll when the sleep sits in a loop that can terminate
    early, and unconditional otherwise. "Can terminate early" is read per loop kind: a
    `for` head is only an iteration range, so its body must carry an exit signal
    (`break`, `&&`, `||`, `if`, `[ `, `test `, `grep -q`); a `while`/`until` head IS
    that loop's exit test, and in this corpus it is usually a bare command
    (`until grep -qE ... ; do`, `until ! pgrep -qf ...; do`) carrying none of those
    tokens, so any non-degenerate head counts and only `while true` / `while :` does
    not. A bare top-level `sleep N` has no exit test at all and is unconditional. When
    a command mixes both, poll wins: that understates the unconditional share, which is
    the safe direction for a number quoted as waste.
  * commanded seconds are arithmetic from the command string, never observed elapsed
    time: `sleep N` = N; `for i in $(seq 1 K); do ... sleep N; done` = K*N (also
    `seq K` and `{1..K}`). Any shape whose count or duration is not literal (`sleep
    $D`, `for i in 1 2 3`, a `while`/`until` loop with no literal trip count) makes the
    whole command's commanded total unknown — reported as `null`/`-`, never as 0.

Ceilings taken deliberately (regex shell reading, not a shell parser): nested
`do ... done` loops parse as one loop; a `sleep` inside a here-doc or a quoted string
counts as a call; a literal `"done"` string inside a loop body ends that body early.
All are rare in the corpus and all fail toward poll/unknown rather than toward an
inflated waste number.

Usage:
    python3 scripts/agent_gaps.py [--root ~/.claude/projects] [--threshold 60]
                                  [--top N] [--json]
Exit code is 0 whatever it finds — this is a measurement, not a gate.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

DEFAULT_ROOT = os.path.join("~", ".claude", "projects")
NONE_CAUSE = "none"
SLEEP_BUCKETS = ("Bash:sleep-poll", "Bash:sleep-unconditional")
EXCERPT = 100

# Shell-word boundaries: `\b` is not one. `/tmp/wave2/impl-done` and `run-sleep.sh` both
# satisfy `\b`, and a stray `done` match truncates a loop body to nothing — measured on the
# corpus, that mislabelled real polls as unconditional waits.
WL, WR = r"(?<![\w./-])", r"(?![\w./-])"
SLEEP_CALL = re.compile(WL + "sleep" + WR)
SLEEP_LITERAL = re.compile(WL + r"sleep\s+(\d+(?:\.\d+)?)" + WR)
LOOP = re.compile(
    WL + "(for|while|until)" + WR + r"(?P<head>.*?)" + WL + "do" + WR + r"(?P<body>.*?)" + WL + "done" + WR,
    re.DOTALL,
)
TRIP_COUNT = re.compile(r"\bseq\s+1\s+(\d+)\b|\bseq\s+(\d+)\b|\{1\.\.(\d+)\}")
EXIT_TEST = re.compile(r"\bbreak\b|&&|\|\||\bif\b|\[\s|\btest\s|\bgrep\s+-q\b")


def parse_ts(value):
    """Epoch seconds from a transcript timestamp, or None if absent/unparseable."""
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _trip_count(head):
    m = TRIP_COUNT.search(head)
    if not m:
        return None
    return int(next(g for g in m.groups() if g is not None))


def _literal_total(fragment):
    """(seconds, ok) for the sleeps in `fragment`; ok is False if any is non-literal."""
    calls = len(SLEEP_CALL.findall(fragment))
    literals = [float(x) for x in SLEEP_LITERAL.findall(fragment)]
    return sum(literals), len(literals) == calls


def _terminates_early(keyword, head, body):
    """Can this loop stop before its trip count runs out?

    A `for` head is only an iteration range, so the exit test has to be in the body.
    A `while`/`until` head IS the exit test — and in the corpus it is usually a bare
    command (`until grep -qE ... ; do`, `until ! pgrep -qf ...; do`) with none of the
    bracket/if tokens, so anything but the degenerate infinite forms counts.
    """
    if keyword == "for":
        return bool(EXIT_TEST.search(body))
    condition = head.strip().strip(";").strip()
    return condition not in ("", "true", ":", "1") or bool(EXIT_TEST.search(body))


def bash_bucket(command):
    """(bucket, commanded_seconds_or_None) for a Bash command string."""
    if not command or not SLEEP_CALL.search(command):
        return "Bash", None

    total = 0.0
    known = True
    poll = False
    unconditional = False
    spans = []

    for m in LOOP.finditer(command):
        spans.append(m.span())
        head, body = m.group("head"), m.group("body")
        if not SLEEP_CALL.search(body):
            continue
        trips = _trip_count(head)
        seconds, ok = _literal_total(body)
        if trips is None or not ok:
            known = False
        else:
            total += trips * seconds
        if _terminates_early(m.group(1), head, body):
            poll = True
        else:
            unconditional = True

    outside = command
    for start, end in reversed(spans):
        outside = outside[:start] + outside[end:]
    if SLEEP_CALL.search(outside):
        seconds, ok = _literal_total(outside)
        if ok:
            total += seconds
        else:
            known = False
        unconditional = True

    if poll:
        return "Bash:sleep-poll", (total if known else None)
    if unconditional:
        return "Bash:sleep-unconditional", (total if known else None)
    return "Bash", None


def _tool_uses(event):
    """The tool_use blocks of an assistant event, in order."""
    if event.get("type") != "assistant":
        return []
    message = event.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]


def read_transcript(path):
    """([(epoch, tool_use_or_None)], event_count, unparseable_lines) in file order."""
    events = []
    count = 0
    bad = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return [], 0, 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if not isinstance(event, dict):
            bad += 1
            continue
        count += 1
        stamp = parse_ts(event.get("timestamp"))
        if stamp is None:
            continue
        blocks = _tool_uses(event)
        events.append((stamp, blocks[-1] if blocks else None))
    return events, count, bad


def _cause(tool_use):
    if tool_use is None:
        return NONE_CAUSE, None, None
    name = tool_use.get("name") or NONE_CAUSE
    if name == "bash":
        name = "Bash"
    if name != "Bash":
        return name, None, None
    inp = tool_use.get("input")
    command = inp.get("command") if isinstance(inp, dict) else None
    if not isinstance(command, str):
        command = None
    bucket, commanded = bash_bucket(command)
    return bucket, commanded, command


def find_transcripts(root):
    """Every `<slug>/<session>/subagents/agent-*.jsonl` under root, sorted."""
    found = []
    if not os.path.isdir(root):
        return found
    for slug in sorted(os.listdir(root)):
        slug_dir = os.path.join(root, slug)
        if not os.path.isdir(slug_dir):
            continue
        for session in sorted(os.listdir(slug_dir)):
            sub = os.path.join(slug_dir, session, "subagents")
            if not os.path.isdir(sub):
                continue
            for name in sorted(os.listdir(sub)):
                if name.startswith("agent-") and name.endswith(".jsonl"):
                    found.append(os.path.join(sub, name))
    return found


def scan(root, threshold, top=0):
    """Walk root and return the whole report as a plain dict (JSON-ready)."""
    root = os.path.abspath(os.path.expanduser(root))
    transcripts = 0
    total_events = 0
    unparseable = 0
    elapsed = 0.0
    gaps = []

    for path in find_transcripts(root):
        events, count, bad = read_transcript(path)
        transcripts += 1
        total_events += count
        unparseable += bad
        if len(events) < 2:
            continue
        elapsed += events[-1][0] - events[0][0]
        last_use = None
        for i in range(len(events) - 1):
            if events[i][1] is not None:
                last_use = events[i][1]
            delta = events[i + 1][0] - events[i][0]
            if delta < threshold:
                continue
            cause, commanded, command = _cause(last_use)
            gaps.append({
                "path": path,
                "seconds": round(delta, 3),
                "cause": cause,
                "in_call": events[i][1] is not None,
                "commanded_seconds": commanded,
                "command": command[:EXCERPT] if command else None,
            })

    gap_seconds = sum(g["seconds"] for g in gaps)
    by_cause = {}
    for gap in gaps:
        b = by_cause.setdefault(gap["cause"], {
            "cause": gap["cause"], "count": 0, "seconds": 0.0, "in_call_seconds": 0.0,
            "commanded_seconds": 0.0, "commanded_unknown": 0,
        })
        b["count"] += 1
        b["seconds"] += gap["seconds"]
        if gap["in_call"]:
            b["in_call_seconds"] += gap["seconds"]
        if gap["cause"] in SLEEP_BUCKETS:
            if gap["commanded_seconds"] is None:
                b["commanded_unknown"] += 1
            else:
                b["commanded_seconds"] += gap["commanded_seconds"]

    buckets = []
    for b in sorted(by_cause.values(), key=lambda x: (-x["seconds"], x["cause"])):
        entry = {
            "cause": b["cause"],
            "count": b["count"],
            "seconds": round(b["seconds"], 3),
            "in_call_seconds": round(b["in_call_seconds"], 3),
            "share_of_gaps": _share(b["seconds"], gap_seconds),
            "share_of_elapsed": _share(b["seconds"], elapsed),
        }
        if b["cause"] in SLEEP_BUCKETS:
            entry["commanded_seconds"] = round(b["commanded_seconds"], 3)
            entry["commanded_unknown"] = b["commanded_unknown"]
        buckets.append(entry)

    unknown = by_cause.get(NONE_CAUSE)
    in_call = sum(g["seconds"] for g in gaps if g["in_call"])
    report = {
        "root": root,
        "threshold_seconds": threshold,
        "transcripts": transcripts,
        "events": total_events,
        "unparseable_lines": unparseable,
        "elapsed_seconds": round(elapsed, 3),
        "gap_count": len(gaps),
        "gap_seconds": round(gap_seconds, 3),
        "gap_share_of_elapsed": _share(gap_seconds, elapsed),
        "in_call_seconds": round(in_call, 3),
        "post_call_seconds": round(gap_seconds - in_call, 3),
        "in_call_share_of_gaps": _share(in_call, gap_seconds),
        "buckets": buckets,
        "unexplained": {
            "cause": NONE_CAUSE,
            "count": unknown["count"] if unknown else 0,
            "seconds": round(unknown["seconds"], 3) if unknown else 0.0,
            "share_of_gaps": _share(unknown["seconds"] if unknown else 0.0, gap_seconds),
            "share_of_elapsed": _share(unknown["seconds"] if unknown else 0.0, elapsed),
        },
    }
    if top:
        report["top"] = sorted(gaps, key=lambda g: (-g["seconds"], g["path"]))[:top]
    return report


def _share(part, whole):
    return round(part / whole, 6) if whole else 0.0


def _pct(value):
    return "%5.1f%%" % (value * 100.0)


def render_text(report):
    lines = []
    lines.append("agent-gaps · root %s" % report["root"])
    lines.append(
        "%d transcripts · %d events · %d unparseable lines · threshold %gs"
        % (report["transcripts"], report["events"], report["unparseable_lines"],
           report["threshold_seconds"])
    )
    lines.append(
        "in-agent elapsed %.1fs (%.1fh) · gaps >= %gs: %d totalling %.1fs (%.1fh) = %s of elapsed"
        % (report["elapsed_seconds"], report["elapsed_seconds"] / 3600.0,
           report["threshold_seconds"], report["gap_count"], report["gap_seconds"],
           report["gap_seconds"] / 3600.0, _pct(report["gap_share_of_elapsed"]).strip())
    )
    lines.append("")
    lines.append("%-26s %7s %12s %8s %9s %12s %14s" % (
        "cause", "count", "seconds", "%gaps", "%elapsed", "in-call s", "commanded"))
    for b in report["buckets"]:
        commanded = "-"
        if "commanded_seconds" in b:
            commanded = "%.0f" % b["commanded_seconds"]
            if b["commanded_unknown"]:
                commanded += " (+%d ?)" % b["commanded_unknown"]
        lines.append("%-26s %7d %12.1f %8s %9s %12.1f %14s" % (
            b["cause"], b["count"], b["seconds"],
            _pct(b["share_of_gaps"]), _pct(b["share_of_elapsed"]),
            b["in_call_seconds"], commanded,
        ))
    u = report["unexplained"]
    lines.append("")
    lines.append(
        "in-call vs post-call: %.1fs (%s of gap time) elapsed with the call still outstanding; "
        "%.1fs (%s) after the last call returned — the latter is model/queue latency, charged to "
        "the preceding tool only because the attribution rule has nothing else to charge it to."
        % (report["in_call_seconds"], _pct(report["in_call_share_of_gaps"]).strip(),
           report["post_call_seconds"], _pct(1.0 - report["in_call_share_of_gaps"]).strip())
    )
    lines.append(
        "unexplained (no preceding tool_use): %d gaps, %.1fs = %s of gap time, %s of elapsed"
        % (u["count"], u["seconds"], _pct(u["share_of_gaps"]).strip(), _pct(u["share_of_elapsed"]).strip())
    )
    attributed = report["gap_seconds"] - u["seconds"]
    lines.append(
        "attributed to a tool call: %.1fs = %s of gap time"
        % (attributed, _pct(_share(attributed, report["gap_seconds"])).strip())
    )
    if report.get("top"):
        lines.append("")
        lines.append("longest %d gaps" % len(report["top"]))
        for g in report["top"]:
            lines.append("  %10.1fs  %-26s %s" % (g["seconds"], g["cause"], g["path"]))
            if g["command"]:
                lines.append("              %s" % g["command"].replace("\n", "\\n"))
    return "\n".join(lines) + "\n"


def main(argv=None, out=None):
    parser = argparse.ArgumentParser(
        prog="agent_gaps.py", description="Attribute long quiet periods in subagent transcripts to the tool call that caused them.",
    )
    parser.add_argument("--root", default=DEFAULT_ROOT, help="projects dir (default: %s)" % DEFAULT_ROOT)
    parser.add_argument("--threshold", type=float, default=60.0, help="gap size in seconds (default: 60)")
    parser.add_argument("--top", type=int, default=0, metavar="N", help="also list the N longest gaps")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit the whole report as one JSON object")
    args = parser.parse_args(argv)

    out = out or sys.stdout
    report = scan(args.root, args.threshold, top=max(0, args.top))
    if args.as_json:
        out.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        out.write(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
