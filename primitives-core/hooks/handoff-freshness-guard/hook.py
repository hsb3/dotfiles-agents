#!/usr/bin/env python3
"""
handoff-freshness-guard — PreCompact hook.

Before compaction proceeds, checks whether the project's handoff file is
fresh. If stale/missing on a MANUAL /compact, blocks and tells the user to
run /handoff first. On AUTO compaction, never blocks (a blocked auto-compact
near a full context window could wedge the session with no way to recover
context headroom) — instead it logs and emits non-blocking guidance via
`systemMessage`.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreCompact):
  - stdin JSON fields consumed: session_id, cwd, trigger ("manual"|"auto")
  - stdout JSON: {"decision": "block", "reason": "...", "systemMessage": "..."}
    OR {"systemMessage": "..."} (non-blocking) OR nothing (allow silently)
  - exit 0 with decision:"block" blocks compaction (confirmed: PreCompact
    supports top-level decision control, same as exit code 2 but non-fatal
    to the hook process itself).
  - exit 2 is the guaranteed-block path (used defensively as a fallback is
    NOT needed here since decision:"block" on exit 0 is documented and
    sufficient) — we use JSON decision control exclusively so a fail-open
    default is possible without special-casing exit codes.
  - Fail-open: any internal error -> exit 0, no JSON (compaction proceeds).

Per-project override: a `handoff:` key in `.claude/atelier.local.md` either
names the project's handoff file (`handoff: docs/HANDOFF.md`), or declares
that the handoff lives outside the repo entirely — on a tracker board, say —
with a stamp file standing in as its only freshness signal:

    handoff:
      mode: external
      stamp: .claude/handoff.stamp
      location: the DFA board task

In external mode the stamp's mtime answers the freshness question the
handoff file's mtime answers in file mode, and the block text points at the
stamp and the location instead of at a repo path that does not exist.
Either form takes full precedence over the standard candidate search below
(found or not — an override that names a file that does not yet exist means
"missing", not "fall back to the trio"). Absent, unparseable, or
out-of-project-root overrides leave the standard search untouched. The
activation-file parser here is intentionally a duplicate of
config-custody/worker-context's, not an import: each hook directory is
copied and symlinked on its own (ADR 0017), so a cross-hook import would
break the moment one hook is installed without the other.
"""

import json
import os
import subprocess
import sys
import time
import traceback

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)
import codex_lifecycle
import atelier_local  # noqa: E402

# ---------------------------------------------------------------------------
# Config (env-overridable)
# ---------------------------------------------------------------------------

FRESHNESS_MINUTES_DEFAULT = 30
LOG_STREAM = "handoff-guard"
LOG_PATH_ENV = "HANDOFF_GUARD_LOG_PATH"

# Used only when no `handoff:` key is armed — neither a file override nor an
# external stamp (see _find_handoff).
CANDIDATE_PATHS = [
    "_meta/HANDOFF.md",
    "HANDOFF.md",
    ".claude/HANDOFF.md",
]

# Human-readable listing of CANDIDATE_PATHS ("a, b, or c"), for the
# missing-handoff message below — derived rather than hand-duplicated so the
# message can't drift from the actual search order if the list ever changes.
def _describe_candidates(paths):
    if len(paths) == 1:
        return paths[0]
    return ", ".join(paths[:-1]) + ", or " + paths[-1]


CANDIDATE_PATHS_DESC = _describe_candidates(CANDIDATE_PATHS)

# ---------------------------------------------------------------------------
# Per-project override (.claude/atelier.local.md `handoff:` key)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
HANDOFF_KEY = "handoff"

# A frontmatter block is a few dozen lines; anything larger is not an
# activation file and reading it into a hook that runs before every
# compaction is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024


def _resolve_project_dir(cwd):
    """CLAUDE_PROJECT_DIR env anchor first, else the resolved payload cwd —
    same anchor config-custody/worker-context use to locate
    .claude/atelier.local.md, and the same anchor agentlog.resolve_project
    uses for the `project` field on this hook's rows."""
    base = (os.environ.get("CLAUDE_PROJECT_DIR") if os.environ.get("ATELIER_HARNESS") != "codex" else None) or cwd
    try:
        return os.path.abspath(base)
    except Exception:
        return cwd


def _main_checkout(path):
    """A linked worktree resolves to its main checkout; anything else returns
    `path` unchanged.

    `git rev-parse --git-common-dir` names the shared git dir: a bare `.git`
    from a main checkout's root, a path ending in `/.git` from anywhere inside
    a linked worktree. Every other answer — no git binary, not a repository, a
    bare repo or a submodule whose common dir is not `<root>/.git` — is treated
    as "not a linked worktree", so a machine without git behaves exactly as it
    did before.

    Duplicated across the atelier hooks by design, like the activation parser
    below: each hook dir is copied and symlinked on its own, so a shared module
    would be a cross-hook import that breaks the moment one of them is
    installed without the other.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--git-common-dir"],
            capture_output=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return path
    if proc.returncode != 0:
        return path
    common = proc.stdout.decode("utf-8", "replace").strip()
    if not common or common == ".git":
        return path  # a main checkout's own root
    if not os.path.isabs(common):
        common = os.path.join(path, common)
    common = os.path.abspath(common)
    if os.path.basename(common) != ".git":
        return path
    return os.path.dirname(common)


def _resolve_activation_path(project_dir):
    """The activation file this hook reads.

    ATELIER_ACTIVATION_FILE wins outright — an explicit override is never
    re-resolved. Otherwise it is the project dir's own copy, falling back to
    the main checkout's copy when no file sits at the direct path and the
    project dir is a linked worktree. The fallback is lazy — it costs a `git`
    subprocess only on the miss, and an activation file that IS present in the
    worktree (a tracked one, at its committed version) still wins.
    """
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return override
    path = os.path.join(project_dir, ACTIVATION_RELPATH)
    if os.path.isfile(path):
        return path
    main_dir = _main_checkout(project_dir)
    if main_dir == project_dir:
        return path
    return os.path.join(main_dir, ACTIVATION_RELPATH)


def _normalize_handoff(children):
    """The two written forms collapsed into one shape, or None when there is
    nothing to collapse (an empty `handoff:` with no children, or a sequence
    where a mapping belongs).

    Every sub-key is present in the result so callers can read one without
    guarding, and `mode` is lowercased but NOT validated here — an
    unrecognised mode has to survive the parser for `activation.py check` to
    name the bad value back to the operator.
    """
    if not children:
        return None
    return {
        "mode": (children.get("mode") or "file").lower(),
        "path": children.get("path") or None,
        "stamp": children.get("stamp") or None,
        "location": children.get("location") or None,
    }


def _handoff_config(text):
    """The `handoff:` key as a config dict, or None if absent/blank/unreadable.

        handoff: docs/HANDOFF.md   ->  {"mode": "file", "path": "docs/HANDOFF.md", ...}

        handoff:                   ->  {"mode": "external", "stamp": "...", ...}
          mode: external
          stamp: .claude/handoff.stamp
          location: the board task

    A sequence under the key is neither form and reads as absent, so a malformed
    activation file falls back to the standard search.
    """
    value = atelier_local.parse_key(text, HANDOFF_KEY)
    if isinstance(value, str):
        return _normalize_handoff({"path": value})
    return _normalize_handoff(value if isinstance(value, dict) else None)


def _load_handoff_config(project_dir):
    """Read the activation file. Any trouble at all -> None (no override)."""
    path = _resolve_activation_path(project_dir)
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return None
    try:
        return _handoff_config(text)
    except Exception:
        return None


def _load_handoff_override(project_dir):
    """The configured handoff FILE path, or None.

    None also covers external mode, where the project has no handoff file at
    all — a caller that only knows about files must see "no override" there,
    not a stamp path it would then read as a handoff.
    """
    config = _load_handoff_config(project_dir)
    if not config or config["mode"] != "file":
        return None
    return config["path"]


def _resolve_override_path(value, project_dir):
    """Validated absolute path for an override value, confined to
    project_dir, or None when value is blank or escapes the project root.

    An escaping value is treated as if no override were set (same fail-open
    posture as an absent key) — this hook must never read outside its
    project's jurisdiction on an untrusted or misconfigured path.

    The same lazy worktree fallback the activation file gets applies to what
    the activation file NAMES: a stamp is gitignored and a handoff file may be
    untracked, so neither travels into a linked worktree, and stat'ing the
    absent copy would block every compaction a worktree session attempts. The
    main checkout's copy is used only when the direct path holds no file, and
    the returned path is reported as-is — a `../` in the block message is the
    honest statement that the signal lives outside this checkout.
    """
    if not value:
        return None
    try:
        abs_path = value if os.path.isabs(value) else os.path.join(project_dir, value)
        abs_path = os.path.normpath(abs_path)
        relpath = os.path.relpath(abs_path, project_dir)
    except Exception:
        return None
    if relpath.split(os.sep)[0] == "..":
        return None
    if os.path.isfile(abs_path):
        return abs_path
    main_dir = _main_checkout(project_dir)
    if main_dir != project_dir:
        candidate = os.path.normpath(os.path.join(main_dir, relpath))
        if os.path.isfile(candidate):
            return candidate
    return abs_path


def _env_int(name, default):
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


FRESHNESS_MINUTES = _env_int(
    "HANDOFF_GUARD_FRESHNESS_MINUTES", FRESHNESS_MINUTES_DEFAULT
)


# ---------------------------------------------------------------------------
# Handoff discovery
# ---------------------------------------------------------------------------

def _find_handoff(cwd):
    """Return (path, mtime, searched, mode, location) for the file whose
    mtime answers the freshness question, with path/mtime None when it does
    not exist — searched is a human-readable description of where the hook
    looked, used only in the block message.

    A valid, in-project-root `handoff:` override in .claude/atelier.local.md
    is authoritative — found or not, it is the only location checked, and
    the standard candidate search below never runs. In external mode the
    file being stat'ed is the stamp, not a handoff; `mode` says which, so
    the caller can pick message text that sends the operator to the right
    place. Absent, unparseable, out-of-root, or external-without-a-usable-
    stamp configurations fall back unchanged to the documented precedence
    order.
    """
    project_dir = _resolve_project_dir(cwd)
    config = _load_handoff_config(project_dir) or {}

    named = None
    mode = "file"
    location = None
    if config.get("mode") == "external":
        named = _resolve_override_path(config.get("stamp"), project_dir)
        if named is not None:
            mode = "external"
            location = config.get("location")
    elif config.get("mode") == "file":
        named = _resolve_override_path(config.get("path"), project_dir)

    if named is not None:
        searched = os.path.relpath(named, project_dir).replace(os.sep, "/")
        if os.path.isfile(named):
            try:
                return named, os.path.getmtime(named), searched, mode, location
            except OSError:
                return None, None, searched, mode, location
        return None, None, searched, mode, location

    for rel in CANDIDATE_PATHS:
        path = os.path.join(cwd, rel)
        if os.path.isfile(path):
            try:
                return path, os.path.getmtime(path), rel, "file", None
            except OSError:
                continue
    return None, None, CANDIDATE_PATHS_DESC, "file", None


def _age_minutes(mtime):
    return (time.time() - mtime) / 60.0


def _external_reason(status, stamp, location):
    """Block text for external mode. It names the stamp and where the
    handoff actually lives, never a repo path — telling someone whose
    handoff is on a board to "run /handoff" would send them to a file that
    is not the handoff.
    """
    where = "; the handoff lives at: {0}".format(location) if location else ""
    if status == "stale":
        return ("Handoff signal is stale (stamp {0}{1}) — update the handoff "
                "and touch the stamp, then /compact.".format(stamp, where))
    return ("No handoff signal found (stamp {0} has never been touched{1}) — "
            "update the handoff and touch the stamp, then /compact.".format(
                stamp, where))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)
        if isinstance(payload, dict):
            payload = codex_lifecycle.prepare(payload)
            if payload is None:
                return

        session_id = payload.get("session_id", "unknown")
        cwd = payload.get("cwd") or os.getcwd()
        trigger = payload.get("trigger", "unknown")  # "manual" | "auto"
        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(cwd),
        )

        path, mtime, searched, mode, location = _find_handoff(cwd)

        if path is None:
            status = "missing"
            age = None
        else:
            age = _age_minutes(mtime)
            status = "fresh" if age < FRESHNESS_MINUTES else "stale"

        blocked = False
        out = None

        if status == "fresh":
            # Allow silently.
            out = None
        else:
            if trigger == "manual":
                blocked = True
                reason = _external_reason(status, searched, location) if mode == "external" else (
                    "Handoff is stale/missing — run /handoff first, then /compact."
                    if status == "stale"
                    else "No handoff file found ({0}) — run /handoff first, "
                    "then /compact.".format(searched)
                )
                out = {
                    "decision": "block",
                    "reason": reason,
                    "systemMessage": reason,
                }
            else:
                # AUTO trigger: never block. A blocked auto-compact near a
                # full context window could wedge the session (no headroom
                # left to run /handoff or anything else). Emit non-blocking
                # guidance instead; PostCompact/next UserPromptSubmit turn
                # can pick up the slack.
                msg = (
                    "Auto-compaction is proceeding with a stale/missing handoff "
                    "signal (stamp {0}). Update the handoff and touch the stamp "
                    "soon to avoid losing externalized state on the next "
                    "compaction.".format(searched)
                    if mode == "external"
                    else "Auto-compaction is proceeding with a stale/missing handoff "
                    "file. Run /handoff soon to avoid losing externalized state "
                    "on the next compaction."
                )
                out = {"systemMessage": msg}

        if out is not None:
            if blocked and codex_lifecycle.enabled():
                out = {"continue": False, "stopReason": out["reason"],
                       "systemMessage": out["reason"]}
            print(json.dumps(out))

        log({
            "session_id": session_id,
            "cwd": cwd,
            "trigger": trigger,
            "handoff_path": path,
            "handoff_mode": mode,
            "handoff_age_minutes": age,
            "status": status,
            "blocked": blocked,
        })

        sys.exit(0)

    except Exception as e:
        # Fail-open: never block compaction on our own error.
        try:
            agentlog.append(LOG_STREAM, {
                "session_id": None,
                "trigger": None,
                "status": "error",
                "blocked": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=3),
            }, agentlog.resolve_project(), LOG_PATH_ENV)
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
