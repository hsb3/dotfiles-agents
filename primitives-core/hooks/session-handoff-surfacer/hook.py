#!/usr/bin/env python3
"""
session-handoff-surfacer — SessionStart hook.

On a genuinely COLD start (source "startup" or "clear"), discovers the
project's handoff file and injects a pointer plus a capped head excerpt so a
fresh session picks up prior work without re-deriving it. This is the
"consume" edge of the handoff loop; handoff-freshness-guard is the "produce"
edge (it nags before compaction if the handoff wasn't refreshed).

Silent no-op on "resume"/"compact" (context is already present — surfacing
would be pure noise) and when no handoff file exists.

When the handoff lives outside the repo (see below) there is no file to
excerpt, so a cold start gets a POINTER instead: where the handoff lives and
which stamp tracks its freshness. That pointer is surfaced whether or not
the stamp exists — the stamp is a freshness signal, while the handoff itself
is on the board either way, and silence would leave the cold session with
nothing.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (SessionStart):
  - stdin JSON fields consumed: session_id, transcript_path, cwd,
    hook_event_name, source ("startup"|"resume"|"clear"|"compact"),
    optionally model, agent_type, session_title.
  - stdout JSON (ONLY when surfacing):
    {"hookSpecificOutput": {"hookEventName": "SessionStart",
                             "additionalContext": "..."}}
    NOTE: SessionStart nests additionalContext under hookSpecificOutput —
    this is DIFFERENT from UserPromptSubmit's top-level additionalContext
    (see context-watermark/hook.py), which is why this hook does not reuse
    that shape.
  - exit 0 always; fail-open on any internal error (no stdout, just a
    best-effort log line).

Per-project override: a `handoff:` key in `.claude/atelier.local.md` either
names the project's handoff file (`handoff: docs/HANDOFF.md`), or declares
that the handoff lives outside the repo entirely — on a tracker board, say —
with a stamp file standing in as its only freshness signal:

    handoff:
      mode: external
      stamp: .claude/handoff.stamp
      location: the DFA board task

Either form takes full precedence over the standard candidate search below
(found or not — a file override that names a file that does not yet exist
means "no handoff", not "fall back to the trio"). Absent, unparseable, or
out-of-project-root overrides leave the standard search untouched. The
activation-file parser here is intentionally a duplicate of
config-custody/worker-context's, not an import: each hook directory is
copied and symlinked on its own (ADR 0017), so a cross-hook import would
break the moment one hook is installed without the other.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import json
import os
import subprocess
import sys
import traceback

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

HEAD_LINES_DEFAULT = 15
LOG_STREAM = "handoff-surfacer"
LOG_PATH_ENV = "HANDOFF_SURFACER_LOG_PATH"

# Same discovery precedence as handoff-freshness-guard/hook.py. Used only
# when no `handoff:` key is armed — neither a file override nor an external
# stamp (see _find_handoff).
CANDIDATE_PATHS = [
    "_meta/HANDOFF.md",
    "HANDOFF.md",
    ".claude/HANDOFF.md",
]

# Sources that count as a genuine cold start.
SURFACE_SOURCES = {"startup", "clear"}

# ---------------------------------------------------------------------------
# Per-project override (.claude/atelier.local.md `handoff:` key)
# ---------------------------------------------------------------------------

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")
HANDOFF_KEY = "handoff"

# A frontmatter block is a few dozen lines; anything larger is not an
# activation file and reading it into a hook that runs on every session
# start is not worth it.
ACTIVATION_MAX_BYTES = 256 * 1024


def _resolve_project_dir(cwd):
    """CLAUDE_PROJECT_DIR env anchor first, else the resolved payload cwd —
    same anchor config-custody/worker-context use to locate
    .claude/atelier.local.md, and the same anchor agentlog.resolve_project
    uses for the `project` field on this hook's rows."""
    base = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
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


def _unquote(value):
    """Strip surrounding quotes and any trailing YAML comment.

    Quote handling comes first: `handoff: "docs/HANDOFF.md"  # note` must
    yield `docs/HANDOFF.md`, while a quoted path is allowed to contain a `#`.
    """
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        close = value.find(quote, 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at].rstrip()
    return value


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


def _parse_handoff_config(text):
    """Return the `handoff:` key from a YAML frontmatter block as a config
    dict, or None if absent/blank/unparseable.

        handoff: docs/HANDOFF.md   ->  {"mode": "file", "path": "docs/HANDOFF.md", ...}

        handoff:                   ->  {"mode": "external", "stamp": "...", ...}
          mode: external
          stamp: .claude/handoff.stamp
          location: the DFA board task

    Deliberately narrow (mirrors worker-context's `enforce`-only parser):
    understands one top-level key, either its scalar value or one level of
    indented sub-keys beneath it, and ignores everything else. Anything it
    cannot make sense of — no fences, no closing fence, a sequence under the
    key — returns None, so a malformed activation file behaves exactly as if
    the key were absent (fall back to the standard search).
    """
    lines = text.splitlines()

    start = None
    for index, line in enumerate(lines):
        stripped = line.lstrip("﻿").strip()
        if not stripped:
            continue
        if stripped == "---":
            start = index + 1
        break  # the first non-blank line must be the opening fence
    if start is None:
        return None

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return None

    config = None
    index = start
    while index < end:
        line = lines[index]
        index += 1
        if not line.strip() or line[:1].isspace() or line.strip().startswith("#"):
            continue
        item = line.strip()
        colon = item.find(":")
        if colon == -1:
            continue
        if item[:colon].strip().lower() != HANDOFF_KEY:
            continue
        # A comment where the value would be reads as no value at all, so
        # `handoff:  # note` opens the mapping form rather than resolving a
        # path named "# note". _unquote only strips a comment that follows a
        # value, which is why the leading case is caught before it.
        rest = item[colon + 1:].strip()
        value = "" if rest.startswith("#") else _unquote(rest)
        if value:
            config = _normalize_handoff({"path": value})
            continue
        # Nothing after the colon: the mapping form, whose children are the
        # indented lines that follow. The scan advances the shared cursor
        # rather than returning, so a key written twice still takes the last
        # value — the same duplicate rule the top level has always had.
        children = {}
        while index < end:
            child = lines[index]
            if not child.strip():
                index += 1
                continue
            if not child[:1].isspace():
                break  # back at the top level: the mapping is over
            index += 1
            sub = child.strip()
            if sub.startswith("#"):
                continue
            if sub.startswith("-"):
                children = None  # a list, not a mapping: unreadable, stay inert
                break
            sub_colon = sub.find(":")
            if sub_colon == -1:
                continue
            children[sub[:sub_colon].strip().lower()] = _unquote(sub[sub_colon + 1:])
        config = _normalize_handoff(children)
    return config


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
        return _parse_handoff_config(text)
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
    untracked, so neither travels into a linked worktree, and a session started
    there would be told there is no handoff at all. The main checkout's copy is
    used only when the direct path holds no file, and the returned path is
    reported as-is — a `../` in the surfaced pointer is the honest statement
    that the handoff lives outside this checkout.
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


def _env_path(name, default):
    v = os.environ.get(name)
    return v if v else default


HEAD_LINES = _env_int("HANDOFF_SURFACER_HEAD_LINES", HEAD_LINES_DEFAULT)


# ---------------------------------------------------------------------------
# Handoff discovery + head excerpt
# ---------------------------------------------------------------------------

def _find_handoff(cwd):
    """Return (path, relpath, mode, location) for the active handoff.

    A valid, in-project-root `handoff:` override in .claude/atelier.local.md
    is authoritative — found or not, it is the only location checked, and
    the standard candidate search below never runs. Absent, unparseable,
    out-of-root, or external-without-a-usable-stamp configurations fall back
    unchanged to the documented precedence order.

    In external mode `path` is always None — there is no local file to read,
    and the stamp is deliberately never opened — while `relpath` still names
    the stamp, because that is what the pointer and the log record report.
    """
    project_dir = _resolve_project_dir(cwd)
    config = _load_handoff_config(project_dir) or {}

    if config.get("mode") == "external":
        stamp = _resolve_override_path(config.get("stamp"), project_dir)
        if stamp is not None:
            relpath = os.path.relpath(stamp, project_dir).replace(os.sep, "/")
            return None, relpath, "external", config.get("location")
    elif config.get("mode") == "file":
        override_path = _resolve_override_path(config.get("path"), project_dir)
        if override_path is not None:
            if os.path.isfile(override_path):
                relpath = os.path.relpath(override_path, project_dir).replace(os.sep, "/")
                return override_path, relpath, "file", None
            return None, None, "file", None

    for rel in CANDIDATE_PATHS:
        path = os.path.join(cwd, rel)
        if os.path.isfile(path):
            return path, rel, "file", None
    return None, None, "file", None


def _read_head_lines(path, n):
    """Read the first n lines of a text file (best-effort; short reads are
    fine, this is a capped excerpt, not the full file)."""
    lines = []
    with open(path, "r", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= n:
                break
            lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def _format_message(relpath, head_text):
    return (
        f"A project handoff exists at {relpath} — read it before starting. "
        f"First lines:\n{head_text}"
    )


def _format_external_message(stamp, location):
    """The external-mode pointer. Without a location there is nowhere to
    send the session, so it says so and asks rather than implying the stamp
    is the handoff."""
    if location:
        return (
            f"This project's handoff lives outside the repo: {location}. "
            f"Read it before starting. Its freshness stamp is {stamp}."
        )
    return (
        f"This project's handoff lives outside the repo — its freshness stamp "
        f"is {stamp}, but this project set no location. Ask the user where the "
        f"handoff lives."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_stdin = sys.stdin.read()
        payload = json.loads(raw_stdin)

        session_id = payload.get("session_id", "unknown")
        cwd = payload.get("cwd") or os.getcwd()
        source = payload.get("source", "unknown")

        log = agentlog.make_logger(
            LOG_STREAM, LOG_PATH_ENV, agentlog.resolve_project(cwd),
        )

        path, relpath, mode, location = _find_handoff(cwd)

        if source not in SURFACE_SOURCES:
            log({
                "session_id": session_id,
                "source": source,
                "handoff_path": relpath,
                "handoff_mode": mode,
                "surfaced": False,
                "reason": "source not eligible for surfacing",
            })
            sys.exit(0)

        if mode == "external":
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": _format_external_message(relpath, location),
                },
                "systemMessage": (
                    f"atelier: surfaced external handoff pointer ({location})."
                    if location
                    else f"atelier: surfaced external handoff pointer (stamp {relpath})."
                ),
            }
            print(json.dumps(out))

            log({
                "session_id": session_id,
                "source": source,
                "handoff_path": relpath,
                "handoff_mode": mode,
                "surfaced": True,
            })
            sys.exit(0)

        if path is None:
            log({
                "session_id": session_id,
                "source": source,
                "handoff_path": None,
                "handoff_mode": mode,
                "surfaced": False,
                "reason": "no handoff file found",
            })
            sys.exit(0)

        head_text = _read_head_lines(path, HEAD_LINES)
        message = _format_message(relpath, head_text)

        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": message,
            },
            # Visible to the USER in the TUI — evidence the hook fired
            # (additionalContext is only ever seen by the model).
            "systemMessage": f"atelier: surfaced project handoff ({relpath}).",
        }
        print(json.dumps(out))

        log({
            "session_id": session_id,
            "source": source,
            "handoff_path": relpath,
            "handoff_mode": mode,
            "surfaced": True,
        })

        sys.exit(0)

    except Exception as e:
        # Fail-open: never break session start on our own error.
        try:
            agentlog.append(
                LOG_STREAM,
                {
                    "session_id": None,
                    "source": None,
                    "surfaced": False,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(limit=3),
                },
                agentlog.resolve_project(),
                LOG_PATH_ENV,
            )
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
