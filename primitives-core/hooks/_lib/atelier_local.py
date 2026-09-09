"""atelier_local — select the harness-appropriate activation file and parse a top-level key.

The activation file's frontmatter, parsed narrowly: one named key as a scalar, a
mapping of sub-keys, or a sequence. Everything else is ignored, and anything
unreadable answers None, so a malformed file behaves exactly as an absent one
(`docs/override-convention.md`, fail-open).

Every hook that reads the activation file parses it here, and nothing else does
(ADR 0017: `_lib/` is a member of every hooks assembly, so importing it is safe
where importing another hook's module is not). Each hook keeps its own byte-source
and parsing limits, including committed custody policy. Harness paths and worktree inheritance are selected here for every reader.

Stdlib-only, Python 3.9 compatible.
"""

import os
import subprocess

ACTIVATION_MAX_BYTES = 256 * 1024


def harness_name():
    """An explicit harness wins over inherited native-session markers."""
    return os.environ.get("ATELIER_HARNESS") or (
        "codex" if os.environ.get("CODEX_THREAD_ID") else "claude-code")


def configured_agents(project_dir):
    """Native agents configured by project files, never installed executables."""
    agents = []
    for name in ("claude", "codex", "opencode"):
        if (os.path.isdir(os.path.join(project_dir, "." + name))
                and not os.path.islink(os.path.join(project_dir, "." + name))):
            agents.append(name)
    if "opencode" not in agents and any(os.path.isfile(os.path.join(project_dir, name))
           and not os.path.islink(os.path.join(project_dir, name))
           for name in ("opencode.json", "opencode.jsonc")):
        agents.append("opencode")
    return tuple(agents)


def _destination(agents):
    if len(agents) > 1:
        return ".agents/atelier.local.md"
    native = agents[0] if agents else {"claude-code": "claude"}.get(harness_name(), harness_name())
    return "." + native + "/atelier.local.md"


def _candidates(agents, shared):
    paths = ([".agents/atelier.local.md"] if shared else []) + [_destination(agents)]
    paths.extend("." + name + "/atelier.local.md" for name in ("claude", "codex", "opencode"))
    return list(dict.fromkeys(paths))


def activation_candidates(project_dir):
    """Shared policy, canonical destination, then fixed native legacy order."""
    return [os.path.join(project_dir, path) for path in _candidates(
        configured_agents(project_dir),
        os.path.lexists(os.path.join(project_dir, ".agents/atelier.local.md")))]


def committed_activation_candidates(project_dir):
    """Apply the same selector to HEAD's tree, never mutable working files."""
    try:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        result = subprocess.run(["git", "-C", project_dir, "ls-tree", "-z", "HEAD"],
                                env=env, capture_output=True, text=True, timeout=3, check=True)
        entries = {}
        for record in result.stdout.split("\0"):
            if record:
                metadata, name = record.split("\t", 1)
                entries[name] = metadata.split()[0]
        agents = [name for name in ("claude", "codex", "opencode")
                  if entries.get("." + name) == "040000"]
        if "opencode" not in agents and any(entries.get(name) in ("100644", "100755")
                for name in ("opencode.json", "opencode.jsonc")):
            agents.append("opencode")
        shared = subprocess.run(["git", "-C", project_dir, "cat-file", "-e",
                                 "HEAD:.agents/atelier.local.md"], env=env,
                                capture_output=True, timeout=3).returncode == 0
        return _candidates(agents, shared)
    except (OSError, ValueError, subprocess.SubprocessError):
        return []


def policy_paths(project_dir):
    """Every policy location setup must inspect before it changes placement."""
    return [os.path.join(project_dir, directory, "atelier.local.md")
            for directory in (".claude", ".codex", ".opencode", ".agents")]


def activation_destination(project_dir):
    """Canonical creation location; explicit overrides remain authoritative."""
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    return os.path.abspath(os.path.join(project_dir, override)) if override else os.path.join(
        project_dir, _destination(configured_agents(project_dir)))


def activation_path(project_dir, inherit=True):
    """Select one file: explicit override, harness-local file, legacy, main checkout.

    A present malformed/unreadable file (including a dangling symlink) still wins.
    Only absence permits inheritance; never merge policies or migrate user files.
    """
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return os.path.abspath(os.path.join(project_dir or os.getcwd(), override))
    if not project_dir:
        return None
    candidates = activation_candidates(project_dir)
    for path in candidates:
        if os.path.lexists(path):
            return path
    if inherit:
        try:
            # Discovery belongs to this cwd, even when called from a routed worker tool.
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_")}
            proc = subprocess.run(
                ["git", "-C", project_dir, "rev-parse", "--git-common-dir"],
                env=env, capture_output=True, text=True, timeout=3)
            if proc.returncode == 0 and proc.stdout.strip():
                common = os.path.abspath(os.path.join(project_dir, proc.stdout.strip()))
                if os.path.basename(common) == ".git":
                    main = os.path.dirname(common)
                    if main != os.path.abspath(project_dir):
                        for path in activation_candidates(main):
                            if os.path.lexists(path):
                                return path
        except (OSError, subprocess.SubprocessError):
            pass
    return candidates[0]


def unquote(value):
    """Strip surrounding quotes, else a trailing ` #` comment."""
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        close = value.find(quote, 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at].rstrip()
    return value


def _frontmatter(text):
    """(lines, start, end) of the frontmatter block, or None."""
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
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return lines, start, index
    return None


def _inline_list(raw):
    """`["a", "b"]` / `[a, b]` -> ["a", "b"]. Commas inside quotes are respected."""
    items = []
    buf = []
    quote = None
    for ch in raw.strip()[1:-1]:
        if quote:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch == ",":
            items.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf).strip())
    return [item for item in items if item]


def _block(lines, index, end):
    """The lines under a bare `key:` -> (next index, mapping or None, sequence or None).

    A block is a sequence the moment it holds one `- ` item, a mapping when it holds
    only `sub: value` lines, and neither when it is empty. Only an unindented line
    carrying a colon ends it — the next top-level key — so a comment or a stray word
    at any indent is skipped rather than treated as the end.
    """
    children = {}
    items = []
    is_sequence = False
    while index < end:
        line = lines[index]
        item = line.strip()
        if not item or item.startswith("#"):
            index += 1
            continue
        if item == "-" or item.startswith("- "):
            index += 1
            is_sequence = True
            entry = unquote(item[2:])
            if entry:
                items.append(entry)
            continue
        if not line[:1].isspace():
            if ":" in item:
                break
            index += 1
            continue
        index += 1
        colon = item.find(":")
        if colon != -1:
            children[item[:colon].strip().lower()] = unquote(item[colon + 1:])
    return index, (children or None), (items if is_sequence else None)


def parse_key(text, key):
    """The named key's value: a str (scalar), a dict (mapping), a list (sequence),
    or None when the key is absent, blank or unreadable.

    A key written twice resolves to its last written FORM, except that repeated
    sequence forms merge — naming a list twice must never silently shrink the list
    a guard enforces. Mixing forms is the case that clause does NOT cover:
    `protected: [main]` then `protected: junk` resolves to the scalar, every
    sequence consumer coerces a scalar to no items, and the guard stays armed
    over nothing. That is the fail-open rule of `docs/override-convention.md`
    applied to a malformed file rather than a bug — and it is why
    `activation.py check` exists, which reports such a key as inert.
    """
    block = _frontmatter(text)
    if block is None:
        return None
    lines, index, end = block
    key = key.lower()
    value = None
    items = []
    sequence = False
    while index < end:
        line = lines[index]
        index += 1
        if not line.strip() or line[:1].isspace() or line.strip().startswith("#"):
            continue
        item = line.strip()
        colon = item.find(":")
        if colon == -1 or item[:colon].strip().lower() != key:
            continue
        rest = item[colon + 1:].strip()
        if rest.startswith("[") and rest.endswith("]"):
            items.extend(_inline_list(rest))
            sequence = True
            continue
        # A comment where the value would be reads as no value at all, so
        # `watermark:  # note` opens the block form rather than yielding "# note".
        scalar = "" if rest.startswith("#") else unquote(rest)
        if scalar:
            value, sequence = scalar, False
            continue
        index, children, entries = _block(lines, index, end)
        if entries is None:
            value, sequence = children, False
        else:
            items.extend(entries)
            sequence = True
    return items if sequence else value


def read_key(project_dir, key):
    """`parse_key` against the project's activation file. Any trouble -> None."""
    try:
        path = activation_path(project_dir)
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
        return parse_key(text, key)
    except Exception:
        return None
