#!/usr/bin/env python3
"""SessionStart surfacer: run the board decay checks so the curation rhythm cannot be skipped.

Step 3 of AGENTS.md's curation rhythm runs `board_health.py` over a fresh snapshot of
the kata board. A step that has to be remembered is a step that gets skipped, so this
hook runs it unasked at session start and puts one verdict line into session context.

WARN ONLY, NEVER A GATE. `board_health.py` exits 1 on any finding and 2 on an unreadable
input; neither becomes this hook's exit code. A health finding is triage input, not a
gate, and a session start is never blocked by this hook — every path exits 0, including
an unexpected exception.

Exactly one verdict line is printed per run, and the three cases are lexically distinct:

    board health: CLEAN — ...
    board health: FINDINGS — ...
    board health: COULD NOT MEASURE — ...

The third is the point of the hook. A run that could not reach the board must never read
like a clean board, so no error path may fall through to the clean wording: CLEAN_MARKER
appears in the clean verdict and nowhere else, and tests/test_board_health_hook.py
asserts that over a table of every failure case. Each could-not-measure line names WHICH
failure it hit — a missing `kata` binary and a dead hosted daemon are a ten-second and a
thirty-minute debug respectively, the same house rule scripts/check_labels.py states for
gates that cannot measure.

Named failures: the `kata` binary absent from PATH · the adapter, the checker, or the
label declaration missing from the tree · the export failing, timing out, or emitting
something that is not a §2 snapshot · the checker timing out, exiting 2, or exiting any
code but 0 or 1 · any unexpected exception, reported by its class name.

Environment. Per docs/override-convention.md a hook takes env-var overrides; every one
here has a default, and a blank or unparseable value falls back to it.

    CLAUDE_PROJECT_DIR       repo root; else this file's own repo root (walk up to .git)
    BOARD_HEALTH_PROJECT     kata project to measure          (default: dotfiles-agents)
    BOARD_HEALTH_KATA_BIN    binary the adapter shells out to (default: kata)
    BOARD_HEALTH_ADAPTER     snapshot exporter                (default: <root>/SCRIPTS/kata_board.py)
    BOARD_HEALTH_SCRIPT      decay checker                    (default: <root>/SCRIPTS/board_health.py)
    BOARD_HEALTH_VOCABULARY  declared labels, one per line    (default: <root>/SCRIPTS/core-labels.txt)
    BOARD_HEALTH_TIMEOUT     seconds per subprocess           (default: 20)

    SCRIPTS = primitives-core/skills/board-triage/scripts

The timeout exists because the kata daemon is hosted and remote: an unmeasured board
costs one line of context, a hung session start costs the session. 20s sits under the
30s registered in config.json, so this hook's own named timeout reason wins rather than
the harness killing it with no verdict at all.

Output is the SessionStart JSON envelope — {"hookSpecificOutput": {"hookEventName":
"SessionStart", "additionalContext": ...}} — which is the form every SessionStart hook
in this repo already emits, and which puts the verdict where the model reads it.

Stdlib-only. Reads the hook JSON on stdin and discards it: the registration's matcher
already selects the sources this fires on, and draining stdin keeps the caller from
seeing a broken pipe.
"""

import json
import os
import shutil
import subprocess
import sys
from collections import namedtuple

CLEAN_MARKER = "board health: CLEAN"
FINDINGS_MARKER = "board health: FINDINGS"
UNMEASURED_MARKER = "board health: COULD NOT MEASURE"

SCRIPTS = ("primitives-core", "skills", "board-triage", "scripts")
DEFAULT_PROJECT = "dotfiles-agents"
DEFAULT_KATA_BIN = "kata"
DEFAULT_TIMEOUT = 20.0
DETAIL_CAP = 300

Proc = namedtuple("Proc", "returncode stdout stderr")
Config = namedtuple("Config", "project kata_bin adapter script vocabulary timeout")


def repo_root(env):
    """CLAUDE_PROJECT_DIR when set, else this file's own repo root."""
    override = (env.get("CLAUDE_PROJECT_DIR") or "").strip()
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    walk = here
    while walk != os.path.dirname(walk):
        if os.path.exists(os.path.join(walk, ".git")):
            return walk
        walk = os.path.dirname(walk)
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def config(env=None):
    env = os.environ if env is None else env
    scripts = os.path.join(repo_root(env), *SCRIPTS)

    def pick(name, default):
        return (env.get("BOARD_HEALTH_" + name) or "").strip() or default

    try:
        timeout = float(pick("TIMEOUT", ""))
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    return Config(
        project=pick("PROJECT", DEFAULT_PROJECT),
        kata_bin=pick("KATA_BIN", DEFAULT_KATA_BIN),
        adapter=pick("ADAPTER", os.path.join(scripts, "kata_board.py")),
        script=pick("SCRIPT", os.path.join(scripts, "board_health.py")),
        vocabulary=pick("VOCABULARY", os.path.join(scripts, "core-labels.txt")),
        timeout=timeout if timeout > 0 else DEFAULT_TIMEOUT,
    )


def unmeasured(reason):
    return f"{UNMEASURED_MARKER} — {reason}"


def _detail(text):
    """One-line, length-capped subprocess output for a could-not-measure reason."""
    flat = " ".join((text or "").split())
    if not flat:
        return "(no output)"
    return flat if len(flat) <= DETAIL_CAP else flat[:DETAIL_CAP] + "…"


def _run(argv, timeout, stdin=""):
    proc = subprocess.run(argv, input=stdin, text=True, capture_output=True, timeout=timeout)
    return Proc(proc.returncode, proc.stdout, proc.stderr)


def _is_snapshot(text):
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return False
    return isinstance(parsed, dict) and isinstance(parsed.get("items"), list)


def verdict(cfg, run=None, which=shutil.which):
    """The one line this run prints. Never raises; never returns an empty string."""
    run = run or _run
    try:
        if which(cfg.kata_bin) is None:
            return unmeasured(
                f"the `{cfg.kata_bin}` binary is not on PATH, so no board snapshot can be"
                " exported — install kata, or point BOARD_HEALTH_KATA_BIN at it"
            )
        for what, path, var in (
            ("the board adapter kata_board.py", cfg.adapter, "BOARD_HEALTH_ADAPTER"),
            ("the decay checker board_health.py", cfg.script, "BOARD_HEALTH_SCRIPT"),
            ("the label declaration core-labels.txt", cfg.vocabulary, "BOARD_HEALTH_VOCABULARY"),
        ):
            if not os.path.exists(path):
                return unmeasured(f"{what} is not at {path} — set {var} to its real location")

        try:
            export = run(
                [sys.executable, cfg.adapter, "export", "--project", cfg.project],
                cfg.timeout, "",
            )
        except subprocess.TimeoutExpired:
            return unmeasured(
                f"the board export timed out after {cfg.timeout:g}s — the hosted kata daemon"
                " is unreachable or too slow to answer"
            )
        if export.returncode != 0:
            return unmeasured(
                f"the board export exited {export.returncode} — the hosted kata daemon is"
                f" unreachable or refused the request: {_detail(export.stderr)}"
            )
        if not _is_snapshot(export.stdout):
            return unmeasured(
                "the board export produced something that is not a snapshot (board-triage"
                f" SKILL.md §2 expects an object with an 'items' list): {_detail(export.stdout)}"
            )

        try:
            health = run(
                [sys.executable, cfg.script, "--vocabulary", cfg.vocabulary],
                cfg.timeout, export.stdout,
            )
        except subprocess.TimeoutExpired:
            return unmeasured(
                f"the decay checker timed out after {cfg.timeout:g}s on a snapshot that did"
                " export — rerun it by hand over the board"
            )
        if health.returncode == 0:
            return (
                f"{CLEAN_MARKER} — measured {cfg.project}: no decay found, no triage pass due"
            )
        if health.returncode == 1:
            return (
                f"{FINDINGS_MARKER} — measured {cfg.project}: run the board-triage pass"
                f" (AGENTS.md curation rhythm step 4). Advisory, nothing is blocked.\n"
                f"{health.stdout.strip()}"
            )
        return unmeasured(
            f"the decay checker exited {health.returncode}, so it judged nothing:"
            f" {_detail(health.stderr or health.stdout)}"
        )
    except Exception as exc:  # noqa: BLE001 — an unmeasured board must still be reported
        return unmeasured(
            f"unexpected {type(exc).__name__} while measuring: {_detail(str(exc))}"
        )


def emit(line):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": line,
    }}))


def main():
    try:
        sys.stdin.read()
    except Exception:  # noqa: BLE001
        pass
    try:
        line = verdict(config())
    except Exception as exc:  # noqa: BLE001
        line = unmeasured(f"unexpected {type(exc).__name__} before measuring: {exc}")
    try:
        emit(line)
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
