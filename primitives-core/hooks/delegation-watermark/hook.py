#!/usr/bin/env python3
"""
delegation-watermark — PostToolUse hook.

Counts the delegable tool calls the MAIN session has performed since its last
delegation, and nudges once the streak crosses a watermark. The companion of
context-watermark: that one watches how much context a session is carrying,
this one watches how much labor it is retaining.

Motivation (the source lab's finding F7, the work-list trigger gap): a
strategist that never delegates looks, from the inside, exactly like a
strategist doing careful work. The failure is only visible in aggregate — e.g.
a session that ran 6+ hours with 93 self-performed tool calls and zero
dispatches. A watermark makes the aggregate visible without anyone asking for
it.

Purely observational: never blocks, never edits, fail-open on every error.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PostToolUse):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, tool_name,
    agent_id (present ONLY when the hook fires inside a subagent — the hook
    exits silently in that case; workers are not nudged to delegate).
  - stdout JSON (exit 0):
      {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                              "additionalContext": "..."},
       "systemMessage": "..."}
    additionalContext nests under hookSpecificOutput; systemMessage is
    top-level.
  - exit 0 always.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import re
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

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

SOFT_DEFAULT = 25          # delegable calls since the last dispatch before the first nudge
REFIRE_EVERY_DEFAULT = 15  # further calls before nudging again, while the streak keeps growing
MAX_BYTES_DEFAULT = 64 * 1024 * 1024  # refuse to scan a pathological transcript
STATE_DIR_DEFAULT = "/tmp/delegation-watermark"
LOG_STREAM = "delegation-watermark"
LOG_PATH_ENV = "DELEGATION_WATERMARK_LOG_PATH"

# The whole transcript is scanned, not a tail window: a tail that happens to
# exclude the last dispatch reports an inflated streak and fires on a session
# that IS delegating. Measured on real transcripts, a full scan of a 2 MB
# transcript costs ~4 ms (~25 ms end-to-end including interpreter startup)
# because the cheap substring test below rejects non-tool lines before any
# JSON parsing.
TOOL_USE_MARKER = '"tool_use"'

# Work a cheaper agent could have done. TodoWrite/Skill/AskUserQuestion and the
# like are session bookkeeping, not labor, so they do not count toward a streak.
DELEGABLE_TOOLS = {
    "Read", "Grep", "Glob", "Bash", "Edit", "Write", "MultiEdit", "NotebookEdit",
}
DISPATCH_TOOLS = {"Task", "Agent"}

# The never-delegated floor: work the doctrine assigns to the session itself, so
# it is not retained labor. Detected from the transcript record — the tool name
# and that call's own input — never from the model declaring its phase.
#
# Floor work never RESETS the streak, it only fails to count. A reset would let
# any periodic floor call hide unbounded labor between them (measured: 12 cycles
# of 24 edits + one board touch = 288 uncounted calls, silent forever).
#
# `kata` is a consuming-repo convention, hence the override
# (docs/override-convention.md).
FLOOR_COMMANDS_DEFAULT = "kata,gh,make,git"

# Which subcommands of a floor head are actually coordination or review. The int
# is which non-flag token to read: `gh` is noun-verb (`gh pr view`), so it is the
# second, which is what keeps `gh workflow run` and `gh api graphql` labor. A
# head with no entry here is floor for any subcommand — that is what makes the
# override usable for a tracker other than kata.
FLOOR_SUBCOMMANDS = {
    "git": ({"status", "log", "diff", "show", "fetch", "branch", "worktree",
             "rev-list", "rev-parse", "merge", "push"}, 1),
    "gh": ({"view", "list", "checks", "diff", "status", "watch"}, 2),
    "make": ({"", "ci", "test", "check", "help", "lint"}, 1),
    "kata": ({"list", "show", "ready", "next", "board", "search", "comment",
              "meta", "label", "schedule", "deadline"}, 1),
}
_SEGMENT_SPLIT = re.compile(r"[;&|\n]+")


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_set(name, default):
    """Comma-separated list knob. Unlike `_env_int`, an empty value is
    meaningful: for a list it says "none", not "use the default"."""
    raw = os.environ.get(name)
    if raw is None:
        raw = default
    return {item.strip() for item in raw.split(",") if item.strip()}


SOFT = _env_int("DELEGATION_WATERMARK_SOFT", SOFT_DEFAULT)
REFIRE_EVERY = _env_int("DELEGATION_WATERMARK_REFIRE_EVERY", REFIRE_EVERY_DEFAULT)
MAX_BYTES = _env_int("DELEGATION_WATERMARK_MAX_BYTES", MAX_BYTES_DEFAULT)
STATE_DIR = os.environ.get("DELEGATION_WATERMARK_STATE_DIR") or STATE_DIR_DEFAULT
FLOOR_COMMANDS = _env_set(
    "DELEGATION_WATERMARK_FLOOR_COMMANDS", FLOOR_COMMANDS_DEFAULT
)


def _is_floor_command(command):
    """True only when EVERY segment of the command is coordination/review shell.

    A command that mixes floor and labor (`git status && python3 build.py`, or
    anything with a substitution) counts as labor: the nudge is worth more kept
    honest than kept quiet.
    """
    if not isinstance(command, str) or not command.strip():
        return False
    if "$(" in command or "`" in command:
        return False
    for segment in _SEGMENT_SPLIT.split(command):
        tokens = segment.split()
        if not tokens:
            continue
        if tokens[0] not in FLOOR_COMMANDS:
            return False
        allowed = FLOOR_SUBCOMMANDS.get(tokens[0])
        if allowed and _positional(tokens[1:], allowed[1]) not in allowed[0]:
            return False
    return True


def _positional(tokens, index):
    """The index-th non-flag token, "" when absent.

    `-C`/`-c` take a value, so `git -C <dir> status` and `make -C <dir> ci` read
    their subcommand rather than the directory.
    """
    skip_next = False
    seen = 0
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            skip_next = token in ("-C", "-c")
            continue
        seen += 1
        if seen == index:
            return token
    return ""


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


def _state_path(session_id):
    return os.path.join(STATE_DIR, f"{session_id}.json")


def _load_state(session_id):
    try:
        with open(_state_path(session_id), encoding="utf-8") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except Exception:
        return {}


def _save_state(session_id, state):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_state_path(session_id), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except Exception:
        pass


def _codex_counts(payload):
    """Count actual native tool events; outer exec transcripts hide shell arguments."""
    import fcntl
    tool_id = payload.get("tool_use_id")
    if not isinstance(tool_id, str) or not tool_id:
        raise ValueError("Codex PostToolUse has no native tool_use_id")
    session = payload.get("session_id")
    if not isinstance(session, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", session):
        raise ValueError("Codex PostToolUse has no valid session_id")
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_state_path(session) + ".counts", "a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        text = stream.read()
        state = json.loads(text) if text else {"streak": 0, "dispatches": 0, "total": 0, "seen": []}
        if tool_id not in state["seen"]:
            name = payload.get("tool_name", "").replace(".", "").replace("_", "")
            command = (payload.get("tool_input") or {}).get("command")
            if name in ("spawnagent", "collaborationspawnagent"):
                state["dispatches"] += 1
                state["streak"] = 0
            elif name in ("Bash", "applypatch") and not (name == "Bash" and _is_floor_command(command)):
                state["total"] += 1
                state["streak"] += 1
            state["seen"] = (state["seen"] + [tool_id])[-256:]
            stream.seek(0)
            stream.truncate()
            json.dump(state, stream)
            stream.flush()
        return state["streak"], state["dispatches"], state["total"]


def _scan(path):
    """Walk the whole transcript; return (streak, dispatches, delegable_total).

    streak          — delegable calls made after the LAST dispatch
    dispatches      — dispatches made this session
    delegable_total — delegable calls made this session

    Subagent turns (`isSidechain`) are skipped: a worker's own tool calls are
    delegated labor, not retained labor.
    """
    streak = 0
    dispatches = 0
    delegable_total = 0


    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if TOOL_USE_MARKER not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("type") != "assistant" or rec.get("isSidechain"):
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name")
                if name in DISPATCH_TOOLS:
                    dispatches += 1
                    streak = 0           # a dispatch resets the streak
                elif name in DELEGABLE_TOOLS:
                    tool_input = block.get("input")
                    # `input` is not guaranteed to be a dict; a raised
                    # AttributeError here escapes to main() and abandons the
                    # whole scan, losing every call in the transcript silently.
                    command = (
                        tool_input.get("command")
                        if isinstance(tool_input, dict) else None
                    )
                    if name == "Bash" and _is_floor_command(command):
                        continue         # coordination shell: neither counts nor resets
                    delegable_total += 1
                    streak += 1

    return streak, dispatches, delegable_total


def _format_message(streak, dispatches, ratio):
    ratio_line = (
        f"Session-performed delegable calls per dispatch so far: ~{ratio:.0f}:1."
        if ratio is not None
        else "No delegation has happened in this session yet."
    )
    return (
        f"[atelier] Delegation watermark: {streak} delegable tool calls "
        f"(reads, greps, edits, shell) in an unbroken run with no delegation. {ratio_line}\n\n"
        "For calibration: delegating sessions' solo runs mostly stayed under ~25, and their "
        "longer stretches (36-69) were grounding or closing work done by hand; sessions that "
        "delegated nothing at all ran 80-103. Past ~25 on a job sized as flat fan-out, "
        "manager-driven, or phased crews, the session is executing rather than running the "
        "strategy layer. Pause and re-size:\n"
        "- Is there a work-list left? Hand the remainder to workers rather than continuing "
        "by hand.\n"
        "- Is the recon still unfinished? Dispatch scouts and read their report instead of "
        "the tree.\n"
        "- Are these small fixes discovered along the way? Collect them on a punch list and "
        "give the list to one agent.\n"
        "- If this work genuinely belongs to the session (decomposition, definition of done, "
        "judging conflicting reports, final gate runs, user-facing synthesis), say so in one "
        "line and carry on — that is the strategy layer's floor, and this nudge is answered by "
        "naming it.\n\n"
        "The delegation skill has the full floor-and-ceiling list."
    )


def main():
    payload = None
    try:
        payload = json.loads(sys.stdin.read())
        if isinstance(payload, dict):
            payload = codex_lifecycle.prepare(payload)
            if payload is None:
                return

        # Never nudge a subagent: a worker delegating is not the behavior we want.
        if payload.get("agent_id"):
            sys.exit(0)

        session_id = payload.get("session_id", "unknown")
        transcript_path = payload.get("transcript_path")
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(payload.get("cwd")),
        )

        if not codex_lifecycle.enabled() and (not transcript_path or not os.path.isfile(transcript_path)):
            log({
                "session_id": session_id, "fired": False,
                "error": "transcript_path missing or not a file",
            })
            sys.exit(0)

        size = 0 if codex_lifecycle.enabled() else os.path.getsize(transcript_path)
        if size > MAX_BYTES:
            log({
                "session_id": session_id, "fired": False,
                "error": f"transcript {size} bytes exceeds MAX_BYTES {MAX_BYTES}",
            })
            sys.exit(0)

        streak, dispatches, delegable_total = (
            _codex_counts(payload) if codex_lifecycle.enabled() else _scan(transcript_path))
        ratio = (delegable_total / dispatches) if dispatches else None

        state = _load_state(session_id)
        try:
            last_fire_at = int(state.get("last_fire_at_streak", 0) or 0)
        except (TypeError, ValueError):
            last_fire_at = 0

        fired = False
        if streak < SOFT:
            # Below the line, or a dispatch just reset it: clear the anti-nag mark.
            if last_fire_at:
                _save_state(session_id, {"last_fire_at_streak": 0})
        elif last_fire_at == 0 or streak - last_fire_at >= REFIRE_EVERY:
            fired = True
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": _format_message(streak, dispatches, ratio),
                },
                "systemMessage": (
                    f"atelier: {streak} tool calls since the last delegation"
                    + (f" (~{ratio:.0f}:1 overall)" if ratio is not None else " (none yet)")
                    + " — re-size or name the floor item."
                ),
            }
            _emit(out)
            _save_state(session_id, {"last_fire_at_streak": streak})

        log({
            "session_id": session_id,
            "tool_name": payload.get("tool_name"),
            "streak": streak,
            "dispatches": dispatches,
            "delegable_total": delegable_total,
            "ratio": round(ratio, 2) if ratio is not None else None,
            "fired": fired,
        })
        sys.exit(0)

    except Exception as e:
        if codex_lifecycle.enabled():
            codex_lifecycle.diagnostic(e)
        try:
            if not isinstance(payload, dict):
                payload = {}
            agentlog.append(LOG_STREAM, {
                "session_id": payload.get("session_id"), "fired": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            }, agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
