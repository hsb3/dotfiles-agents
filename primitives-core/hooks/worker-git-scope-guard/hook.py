#!/usr/bin/env python3
"""worker-git-scope-guard — PreToolUse guard on a subagent's mutating git.

Two halves of one hazard: a worker's git call destroying work the worker does not own.

  1. **A stash in a shared tree.** When workers are not worktree-isolated they share one
     checkout, so a stash sweeps every sibling's uncommitted work into one entry and a
     conflicted pop plus a drop loses it. Denied whenever the resolved directory is the
     main checkout rather than the worker's own linked worktree. Independent of any
     configuration and of where HEAD is.
  2. **A write landing on a protected branch.** A worktree shares the repo's `.git` and
     its remote, so a commit made with HEAD on a protected branch lands on the real one.
     `commit`, `merge`, `rebase`, `cherry-pick`, `revert`, `am` while HEAD is protected,
     and any `push` aimed at a protected ref. Armed only by `protected-branches:` in
     `.claude/atelier.local.md`; there is no built-in list, so this half is inert until a
     project names its own branches.

Subagents only — the payload carries `agent_id` / `agent_type` inside a subagent and not
in the main session, which owns integration and is never restricted here.

`--no-verify` does not bypass this: that flag skips git's own hooks, never the harness's.

**Not containment.** A worker that writes a shell script first, or drives git through
another tool, is not caught. Server-side branch protection is the layer above.

Stdlib-only, Python 3.9 compatible. Reads the hook JSON on stdin, prints one JSON object
on a deny and nothing otherwise, and always exits 0 — a guard that crashes must not block
the Bash tool.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# git subcommands that write a commit onto the current branch
WRITE_SUBS = {"commit", "merge", "rebase", "cherry-pick", "revert", "am"}

# The stash forms that MOVE work. `list` and `show` are reads and never fire.
STASH_MUTATORS = {"push", "pop", "apply", "drop", "clear", "branch", "save",
                  "create", "store"}

# git global options that consume a following value (skipped when locating the subcommand)
VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

ACTIVATION_RELPATH = os.path.join(".claude", "atelier.local.md")

# A frontmatter block is a few dozen lines; anything larger is not an activation file.
# The same cap every other hook in this bundle applies before it parses a byte.
ACTIVATION_MAX_BYTES = 256 * 1024

PROTECTED_BRANCHES_KEY = "protected-branches"


# ---------------------------------------------------------------------------
# Activation file (tolerant hand parser — stdlib only, no PyYAML)
#
# Deliberately duplicated per hook rather than shared: each hook owns its own reading of
# the file so one hook's parser change cannot silently move another hook's behaviour.
# Narrowed here to the single sequence key this hook reads.
# ---------------------------------------------------------------------------

def _resolve_project_dir(payload_cwd):
    """Env anchor first, else the payload cwd, else None."""
    base = os.environ.get("CLAUDE_PROJECT_DIR") or payload_cwd
    if not base or not isinstance(base, str):
        return None
    try:
        return os.path.abspath(base)
    except Exception:
        return None


def _resolve_activation_path(project_dir):
    override = os.environ.get("ATELIER_ACTIVATION_FILE")
    if override:
        return override
    if not project_dir:
        return None
    return os.path.join(project_dir, ACTIVATION_RELPATH)


def _unquote(value):
    """Strip surrounding quotes and any trailing YAML comment."""
    value = value.strip()
    if value[:1] in ("'", '"'):
        quote = value[0]
        close = value.find(quote, 1)
        return value[1:close] if close != -1 else value[1:]
    hash_at = value.find(" #")
    if hash_at != -1:
        value = value[:hash_at].rstrip()
    return value


def _split_inline_list(raw):
    """`["a", "b"]` / `[a, b]` -> ["a", "b"]. Commas inside quotes are respected."""
    inner = raw.strip()[1:-1]
    items = []
    buf = []
    quote = None
    for ch in inner:
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


def _parse_frontmatter(text):
    """Branch names under `protected-branches:` in a YAML frontmatter block.

    Block or inline form. Anything it cannot make sense of — no fences, no closing
    fence, a trailing comment where the value belongs — returns [], which leaves the
    protected-branch half inert rather than half-armed.
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
        return []

    end = None
    for index in range(start, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return []

    branches = []
    in_key = False
    for line in lines[start:end]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indented = line[:1].isspace()
        item = line.strip()

        if in_key and item.startswith("- "):
            value = _unquote(item[2:])
            if value:
                branches.append(value)
            continue
        if in_key and item == "-":
            continue
        if indented:
            continue  # nested mapping under some other key: not ours

        colon = item.find(":")
        if colon == -1:
            continue
        key = item[:colon].strip().lower()
        raw_value = item[colon + 1:].strip()
        in_key = False

        # `protected:` (config-custody's file-path key) is a DIFFERENT key and is never
        # read here: a file glob must never be mistaken for a branch name.
        if key == PROTECTED_BRANCHES_KEY:
            if raw_value.startswith("[") and raw_value.endswith("]"):
                branches.extend(_split_inline_list(raw_value))
            elif not raw_value:
                in_key = True

    return branches


def _load_protected_branches(project_dir):
    """The protected-branch set for this project. Any trouble at all -> empty."""
    path = _resolve_activation_path(project_dir)
    if not path:
        return frozenset()
    try:
        if os.path.getsize(path) > ACTIVATION_MAX_BYTES:
            return frozenset()
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(ACTIVATION_MAX_BYTES)
    except Exception:
        return frozenset()
    try:
        return frozenset(_parse_frontmatter(text))
    except Exception:
        return frozenset()


# ---------------------------------------------------------------------------
# Shell command parsing
# ---------------------------------------------------------------------------

# (?<!<)/(?!<) reject `<<<` herestrings (no terminator to find); the trailing
# lookahead rejects `<<` mid-expression (e.g. `1 << 3`), which is never a real opener
HEREDOC_START = re.compile(r"(?<!<)<<(?!<)-?\s*['\"]?(\w+)['\"]?(?=\s|$)")


def strip_heredocs(command):
    """Drop heredoc bodies so a git literal inside one is never read as an invocation.

    Only drops when the terminator is actually found — an unmatched `<<` (a shift
    operator, a stray word) must keep every line, since dropping text here is a
    silent fail-open and keeping it is at worst an over-deny.
    """
    lines = command.split("\n")
    out, i = [], 0
    while i < len(lines):
        m = HEREDOC_START.search(lines[i])
        if m:
            terminator = m.group(1)
            j = i + 1
            while j < len(lines) and lines[j].strip() != terminator:
                j += 1
            if j < len(lines):
                out.append(lines[i])
                i = j + 1  # skip the body and the terminator line
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _cd_resolves(ctx, target):
    """A cd target is trusted only when it cannot silently leave the repo.

    An absolute path is trusted as-is (matching `git -C`, which never checks existence
    either). A relative descent is trusted only if it has no `..` component AND the
    resulting directory actually exists — `..` is rejected even when the parent happens
    to exist on disk, because that parent is very often outside the repo.
    """
    if target.startswith("/"):
        return True
    if os.path.pardir in target.split("/"):
        return False
    return os.path.isdir(os.path.normpath(os.path.join(ctx, target)))


def invocations(command, cwd):
    """Yield (subcommand, args, resolved_dir) for each git call in a shell command.

    `cd` updates the resolved dir for git calls later in the same command, mirroring
    how `git -C` already does; an ambiguous target (bare `cd`, `cd -`, an unresolved
    env var / `~` / `..`, or a nonexistent relative path) leaves it unchanged rather
    than guess — the base cwd is always at least as safe as a wrong guess.
    """
    command = strip_heredocs(command)
    ctx = cwd
    # ponytail: splits on raw text, so a separator INSIDE a quoted arg still fragments
    # the command and can hide a real invocation; a real shell tokenizer would close this
    for part in re.split(r"&&|\|\||;|\||\n", command):
        try:
            toks = shlex.split(part)
        except ValueError:
            toks = part.split()
        while toks and toks[0] == "cd":
            target = toks[1] if len(toks) > 1 else None
            consumed = 2 if target is not None else 1
            if target and target != "-" and _cd_resolves(ctx, target):
                ctx = (target if target.startswith("/")
                       else os.path.normpath(os.path.join(ctx, target)))
            toks = toks[consumed:]
        if "git" not in toks:
            continue
        toks = toks[toks.index("git"):]
        cdir, i = None, 1
        while i < len(toks):
            t = toks[i]
            if t == "-C":
                cdir = toks[i + 1] if i + 1 < len(toks) else None
                i += 2
                continue
            if t in VALUE_OPTS:
                i += 2
                continue
            if t.startswith("-"):
                i += 1
                continue
            yield t, toks[i + 1:], cdir or ctx
            break


def target_branches(args):
    """Refspec destinations in a `git push` arg list, or [] when none are given."""
    positional = [a for a in args if not a.startswith("-")]
    return [s.split(":")[-1].rsplit("/", 1)[-1] for s in positional[1:]]


def stash_moves_work(args):
    """True for the stash forms that move work, False for `list` and `show`.

    A bare `git stash`, or one starting with a flag, is the `push` form. Only the FIRST
    token can be the subcommand — a later bare word is a message or a pathspec, so
    `git stash -m list` must not read as `git stash list`. An unrecognised subcommand is
    left alone: git itself rejects it, and inventing a deny for a command that will not
    run buys nothing.
    """
    return not args or args[0].startswith("-") or args[0] in STASH_MUTATORS


# ---------------------------------------------------------------------------
# Resolvers that touch the world (passed into decide, so tests need neither)
# ---------------------------------------------------------------------------

def current_branch(cwd):
    """Branch name at HEAD in `cwd`, or None (detached HEAD, not a repo, git missing)."""
    out = _git(cwd, "--abbrev-ref", "HEAD")
    if out is None:
        return None
    name = out.strip()
    return name if name and name != "HEAD" else None


def shared_tree(cwd):
    """True when `cwd` is the main checkout, False in a linked worktree, None if unsure.

    Measured rather than assumed: `--git-common-dir` alone does NOT identify the main
    checkout, because from a SUBDIRECTORY of it git answers with a relative path
    (`../../.git`) that looks nothing like the `.git` returned at the root — reading
    that as a worktree would let the very stash this guard exists to stop straight
    through. Comparing it with `--git-dir` is what actually separates the two: they are
    the same directory in a main checkout and differ in a linked worktree, where
    `--git-dir` points into `.git/worktrees/<name>`.

    A common dir whose basename is not `.git` (a bare repo, a submodule) is reported as
    unsure rather than guessed at.
    """
    out = _git(cwd, "--git-common-dir", "--git-dir")
    if out is None:
        return None
    parts = out.split("\n")
    if len(parts) < 2:
        return None
    common, gitdir = (_abspath(cwd, p.strip()) for p in parts[:2])
    if not common or not gitdir:
        return None
    if os.path.basename(common.rstrip(os.sep)) != ".git":
        return None
    return common == gitdir


def _git(cwd, *args):
    """`git -C cwd rev-parse <args>` stdout, or None on any failure."""
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse"] + list(args),
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _abspath(cwd, path):
    """Absolute, symlink-resolved. realpath is load-bearing, not tidiness: git answers
    one of these two questions with its own already-resolved absolute path and the other
    with a path relative to the caller, so joining without resolving compares
    `/var/...` against `/private/var/...` on a platform with a symlinked temp or home
    and reports a shared checkout as a worktree."""
    if not path:
        return None
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd, path))


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def decide(data, branch_of, shared_of, protected):
    """The deny payload for one PreToolUse event, or None to stay silent.

    Every resolver is an argument so the whole decision is testable with no git repo
    and no activation file: `branch_of(dir) -> str|None`, `shared_of(dir) -> bool|None`,
    `protected` = the frozenset of protected branch names (empty = that half is inert).
    """
    if not (data.get("agent_id") or data.get("agent_type")):
        return None  # the main session owns integration and is never restricted here
    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or "."
    for sub, args, where in invocations(command, cwd):
        if sub == "stash":
            if stash_moves_work(args) and shared_of(where) is True:
                return _deny_stash()
        elif sub in WRITE_SUBS:
            if protected and branch_of(where) in protected:
                return _deny_branch("`git {0}`".format(sub), branch_of(where))
        elif sub == "push" and protected:
            targets = target_branches(args)
            hit = next((t for t in targets if t in protected), None)
            if hit is None and not targets:
                branch = branch_of(where)
                hit = branch if branch in protected else None
            if hit:
                return _deny_branch("`git push` targeting", hit)
    return None


def _deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _deny_stash():
    return _deny(
        "atelier worker-git-scope-guard: `git stash` in a checkout shared with sibling "
        "workers. A stash here sweeps up every sibling's uncommitted work, and a "
        "conflicted pop followed by a drop destroys it with nothing left to recover "
        "from. Commit your own work on your own branch instead, or leave it in the tree "
        "and report what is unfinished. If you need a clean tree to run something, say "
        "so and stop — the dispatching session sequences that. `git stash list` and "
        "`git stash show` are reads and are never blocked."
    )


def _deny_branch(what, branch):
    return _deny(
        "atelier worker-git-scope-guard: {0} protected branch `{1}`. A worktree shares "
        "this repo's .git and its remote, so a worker's write on a protected branch "
        "lands on the real one. Work on your own branch (git switch -c <slug>) and hand "
        "the branch back, or leave the changes uncommitted for the dispatching session "
        "to review. --no-verify does not bypass this — it only skips git's own hooks."
        .format(what, branch)
    )


def main():
    """The whole entry point is fail-open, not just its `__main__` wrapper: the module is
    also imported and called directly, and a guard that raises there would take its caller
    down instead of quietly allowing the call."""
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return
        protected = _load_protected_branches(_resolve_project_dir(data.get("cwd")))
        out = decide(data, current_branch, shared_tree, protected)
        if out is not None:
            print(json.dumps(out))
    except Exception:  # noqa: BLE001 — a guard fails open, never with a traceback
        return


if __name__ == "__main__":
    main()
