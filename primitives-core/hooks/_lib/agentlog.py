"""agentlog — the one append path for every hook ledger in this marketplace.

Hooks used to each roll a private `_log`, each defaulting to
`$CLAUDE_PROJECT_DIR/logs/<name>.jsonl`. Two consequences, both bad once the
rows became an analytics dataset rather than in-session guidance: ledgers
scattered into whatever repo a session happened to be in, and a row carried no
field naming its producer, so it was unattributable the moment it was separated
from its filename. With a mirror plugin (`plugin-oc-atelier`) writing
near-identical rows on another harness, that was ambiguous by construction.

Layout — one global, partitioned root, matching the opencode side exactly:

    ${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl

Content — an identity envelope stamped on every row, envelope keys first:

    {"v": 1, "plugin": "atelier", "harness": "claude-code",
     "stream": "config-custody", "ts": "2026-08-20T15:37:08.666Z",
     "project": "/repo/x", ...caller payload}

`stream` is what keeps a row identifiable after files are concatenated, `v`
is what makes the shape changeable later, and `project` replaces the
per-project directory as the grouping key.

Resolution order for a stream's path: the hook's own `<NAME>_LOG_PATH`
override (unchanged from before — only the fallback moved), else the
partitioned root above.

Import contract: hooks live at `<hooks-root>/<name>/hook.py` and this module
at `<hooks-root>/_lib/agentlog.py`. `../_lib` relative to the hook's own
directory therefore resolves both in `primitives-core/` and in an installed
plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
Each hook spends that contract with the same two-line preamble::

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
    import agentlog

Stdlib-only, Python 3.9 compatible, zero install. Every write is best-effort:
logging must never raise into a hook, and a hook must never fail because a
disk was full or a directory was read-only.
"""

import json
import os
from datetime import datetime, timezone

SCHEMA_VERSION = 1
HARNESS = "codex" if os.environ.get("ATELIER_HARNESS") == "codex" else "claude-code"
# ponytail: single default plugin id — every hook that uses this today ships in
# `atelier`. A hook in another plugin passes plugin="<id>" to make_logger rather
# than growing a registry here.
PLUGIN = "atelier"

#: Envelope keys are owned by this module. A caller payload may not set them —
#: see `_envelope` for why that is enforced rather than trusted.
ENVELOPE_KEYS = ("v", "plugin", "harness", "stream", "ts", "project")


def log_root(plugin=PLUGIN):
    """`${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>`.

    XDG_DATA_HOME is honoured only when absolute: the spec says a relative
    value must be ignored, and honouring one here would land the ledger
    somewhere relative to the process cwd — the scattering this root exists
    to end.
    """
    base = os.environ.get("XDG_DATA_HOME")
    if not base or not os.path.isabs(base):
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "agent-logs", HARNESS, plugin)


def resolve_project(cwd=None):
    """The project a row belongs to — a field now, not a directory.

    CLAUDE_PROJECT_DIR is set by Claude Code for hook commands; the payload
    cwd is the fallback for a harness that does not set it. Unlike the old
    per-hook resolvers, an unresolvable project is no longer a reason to skip
    logging — the row lands in the partitioned root either way and simply
    carries a null project.
    """
    return (os.environ.get("CLAUDE_PROJECT_DIR") if HARNESS != "codex" else None) or cwd or None


def stream_path(stream, override_env=None, plugin=PLUGIN):
    """Absolute path for one stream, honouring the hook's own path override."""
    if override_env:
        override = os.environ.get(override_env)
        if override:
            return override
    return os.path.join(log_root(plugin), stream + ".jsonl")


def _now_iso():
    """ISO-8601 UTC with millisecond precision: `2026-08-20T15:37:08.666Z`.

    Sorts lexically in the order it sorts chronologically, and parses without
    per-consumer handling — the two things the old epoch float did not do.
    """
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _envelope(stream, project, record, plugin=PLUGIN, version=SCHEMA_VERSION):
    """Envelope keys first, then any caller key that is not an envelope key.

    The envelope wins on collision rather than the payload. That inverts the
    opencode spread (`{...envelope, ...payload}`) deliberately: `ts` in
    particular used to be stamped at each call site, and a call site that
    still sets one must not be able to reintroduce an epoch float into a
    field consumers now parse as ISO-8601. Enforcing it here makes that
    structurally true instead of a convention every future hook has to know.
    """
    row = {
        "v": version,
        "plugin": plugin,
        "harness": HARNESS,
        "stream": stream,
        "ts": _now_iso(),
        "project": project,
    }
    if isinstance(record, dict):
        for key, value in record.items():
            if key not in row:
                row[key] = value
    return row


def append(stream, record, project=None, override_env=None, plugin=PLUGIN, version=SCHEMA_VERSION):
    """Stamp the envelope on `record` and append it to `stream` as one line."""
    path = stream_path(stream, override_env, plugin)
    row = _envelope(stream, project, record, plugin, version)
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, default=str) + "\n")
    except Exception:
        # Logging must never break the hook it is logging for.
        try:
            os.write(2, b"atelier: agentlog append failed\\n")
        except Exception:
            pass
        return None
    return row


def make_logger(stream, override_env=None, project=None, plugin=PLUGIN):
    """Bind a stream to a one-argument `log(record)` for a hook's call sites.

    Hooks resolve their project once and then log several times; binding here
    keeps the stream name and override spelled once per hook rather than at
    every write site, which is what the old private writers got wrong.
    """

    def log(record):
        return append(stream, record, project, override_env, plugin)

    return log
