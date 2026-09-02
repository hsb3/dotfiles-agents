#!/usr/bin/env python3
"""
manager-package-gate — SubagentStop hook.

Refuses to let a `manager` subagent end its turn on a mid-chain progress note.
A manager's turn ends with exactly one of two things: the full proof package,
or a named stop condition. Anything else strands the wave — the completion
notification looks like a finished wave, and the work sits idle until the
strategist notices and resumes it by hand.

Motivation (field report, atelier 0.22.0, 2026-09-02): two `manager` dispatches
in one session each returned "waiting on them" as their final message while the
harness reported no live children. Every builder they were waiting on had
already returned. Resumed with an explicit "no more progress notes", both
completed the full package normally. The doctrine already said this
(`agents/manager.md`, `skills/delegation/references/manager-brief.md`); prose
alone did not hold, so the rule is restated at the point the turn actually ends.

The doctrine prescribes a fixed first line precisely so this check can be
mechanical rather than a judgement about prose quality: `## Proof package` or
`## Stopped: <condition>`. This hook checks the sentinel and nothing else — it
never reads the package's contents, and it never decides whether the evidence is
any good. That stays the strategist's job.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks.md   (Claude Code 2.1.258)

Contract (SubagentStop):
  - stdin JSON fields consumed: agent_type (the dispatched agent, optionally
    plugin-qualified as `atelier:manager`), agent_id, stop_hook_active,
    last_assistant_message (the subagent's final message text).
    `agent_transcript_path` is documented on this event and deliberately NOT
    read: the final message is already on stdin, so opening the transcript would
    buy nothing and add a failure mode.
  - stdout JSON (exit 0), on a nudge only:
      {"decision": "block", "reason": "..."}
    A block keeps the subagent running and hands `reason` to it as its next
    instruction. Every other path prints nothing.
  - `stop_hook_active` is true when the stop already fired once through this
    hook. It is honoured as a hard let-through: one nudge, never a loop. Claude
    Code independently caps at 8 consecutive blocks, but relying on that cap
    would mean burning eight manager turns on a manager that genuinely cannot
    produce the package.
  - exit 0 always. An exception must never emit a block, and must never keep a
    finished subagent alive.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import json
import os
import sys

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

LOG_STREAM = "manager-package-gate"
LOG_PATH_ENV = "MANAGER_PACKAGE_GATE_LOG_PATH"

#: The one agent type this hook has an opinion about. Compared against the LAST
#: segment of `agent_type` so a plugin-qualified `atelier:manager` matches while
#: a differently-named agent that merely ends in the word does not.
MANAGED_AGENT = "manager"

#: The fixed first lines the doctrine prescribes. Kept in step with
#: `agents/manager.md` ("Proof package upward") and
#: `skills/delegation/references/manager-brief.md` ("Evidence format").
SENTINELS = ("## Proof package", "## Stopped:")

BLOCK_REASON = (
    "atelier manager-package-gate: your turn ends only with the full proof package — "
    "per-criterion evidence, what you deliberately deferred, out-of-scope notes you are "
    "reporting rather than fixing, and the worker log — sent as a final message whose "
    "first line is `## Proof package`, or else an escalation whose first line is "
    "`## Stopped: <named condition>`. Every worker you dispatched has already delivered "
    "its report, so there is nothing left to wait on: continue straight to that final "
    "message now, and do not send another progress note."
)


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


def _is_managed(agent_type):
    """True for `manager` and for any plugin/path qualification of it.

    The last segment after `:` or `/` is the bare agent name, so `manager`,
    `atelier:manager`, and `plugin:atelier/manager` all match while
    `code-manager` does not.
    """
    if not isinstance(agent_type, str):
        return False
    name = agent_type.strip().rsplit(":", 1)[-1].rsplit("/", 1)[-1]
    return name == MANAGED_AGENT


def _decide(payload):
    """`skip` (already nudged once), `pass` (sentinel present), or `nudge`."""
    if payload.get("stop_hook_active"):
        return "skip"
    message = payload.get("last_assistant_message")
    if not isinstance(message, str):
        message = ""
    return "pass" if message.lstrip().startswith(SENTINELS) else "nudge"


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)

        agent_type = payload.get("agent_type")
        if not _is_managed(agent_type):
            sys.exit(0)  # not our agent: silent, and nothing logged

        decision = _decide(payload)
        if decision == "nudge":
            _emit({"decision": "block", "reason": BLOCK_REASON})

        # One row per manager stop, whichever way it went. Unlike config-custody
        # the passes are logged too: the ratio of packages to progress notes is
        # the only evidence for whether the doctrine change or the hook is what
        # holds, and a nudge-only ledger cannot show it.
        agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(payload.get("cwd")),
        )({
            "session_id": payload.get("session_id"),
            "agent_id": payload.get("agent_id"),
            "agent_type": agent_type,
            "decision": decision,
        })
        sys.exit(0)

    except Exception:
        # Fail open, and silently: a broken gate must never block a finished
        # subagent, and there is no logger to report into on the paths that can
        # fail before one is bound.
        sys.exit(0)


if __name__ == "__main__":
    main()
