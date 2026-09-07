#!/usr/bin/env python3
"""PreToolUse guard: deny Bash commands that would check out or recreate `main` locally.

`main` is the CI-assembled distribution branch (ADR 0007/0008) — a local checkout
turns dev's ignored residue into untracked noise and risks committing workbench
junk to the consumer surface. Inspect it via `git show origin/main:<path>` or a
throwaway `git worktree add ... origin/main` instead (worktrees use a detached or
differently-named checkout, so they never trip this guard's exact-token match).

**Only this repo is guarded.** A project-scoped hook is armed for the whole session,
so it used to refuse `git checkout main` in any OTHER repo the session visited, where
`main` is the ordinary default branch and checking it out is correct (card twhq). Each
simple command therefore carries an effective directory — the payload's `cwd`, moved by
a leading `cd` for the segments that follow it and by `git -C <dir>` for that one
invocation — and the guard stays silent unless that directory is inside the guarded
repo. The repo is `CLAUDE_PROJECT_DIR` when set, else this file's own repo root, and
containment is a realpath prefix test, so a linked worktree under the root is inside
while a sibling like `<root>-other` is not. The segment-and-`cd` parsing is adapted from
the `no_agent_writes_on_main` guard in a sibling repo (its `_cd_resolves` /
`invocations`), with one deliberate inversion: there an unresolvable `cd` leaves the
directory unchanged, here it resolves to *unknown* and unknown is treated as **inside**.
That is the fail-safe direction — a false deny costs a rephrased command, while a false
allow silently checks `main` out in this working directory, which is the whole thing the
guard exists to prevent.

Stdlib-only. Reads the hook JSON on stdin; on a match, emits a PreToolUse deny.

The guard never blocks the Bash tool on its own failure: `main()` swallows any error
and exits 0 (the error-suppression that used to live in the settings.json command
string `... 2>/dev/null || true`, folded in-script so the registration is a plain
script invocation per ADR 0002). Directory resolution touches the filesystem but never
shells out, and any error it raises is caught the same way.
"""
import json
import os
import re
import shlex
import sys

BRANCH = "main"

# git global options that consume a following value (must be skipped to find the subcommand)
VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def guarded_root():
    """The repo this guard protects: CLAUDE_PROJECT_DIR, else this file's repo root."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(os.path.join(here, "..", "..", ".."))  # <root>/.claude/hooks/<name>


def resolve(ctx, target):
    """Directory a `cd <target>` lands in, or None when it cannot be resolved.

    An absolute path is trusted as-is (it needs no filesystem lookup, and `git -C`
    does not check existence either); a relative one must exist under `ctx`. A bare
    `cd`, `cd -`, a `~` or an unexpanded `$VAR` is unknowable from here and returns
    None, which `inside()` reads as "inside" rather than guessing.
    """
    if not target or target == "-" or target.startswith("~") or "$" in target:
        return None
    if os.path.isabs(target):
        return target
    if ctx is None:
        return None
    landed = os.path.normpath(os.path.join(ctx, target))
    return landed if os.path.isdir(landed) else None


def inside(path, root):
    """True when `path` is the guarded repo or below it; True also when unknown."""
    if path is None:
        return True  # fail safe: an unresolvable directory keeps the guard armed
    try:
        p, r = os.path.realpath(path), os.path.realpath(root)
    except OSError:
        return True
    return p == r or p.startswith(r + os.sep)


def offending(command, cwd=None, root=None):
    """Return a human-readable reason if `command` checks out / creates local main."""
    root = root or guarded_root()
    try:
        ctx = cwd or os.getcwd()
    except OSError:  # cwd deleted out from under the process — unknown, so: inside
        ctx = "."
    # Examine each simple command so `cd x && git switch main` is still caught.
    for part in re.split(r"&&|\|\||;|\|", command):
        try:
            toks = shlex.split(part)
        except ValueError:
            toks = part.split()
        while toks and toks[0] == "cd":  # a `cd` moves every LATER segment too
            target = toks[1] if len(toks) > 1 else None
            ctx = resolve(ctx, target)
            toks = toks[2:] if target else toks[1:]
        if "git" not in toks:
            continue
        toks = toks[toks.index("git"):]
        sub, args, where = None, [], ctx
        i = 1
        while i < len(toks):
            t = toks[i]
            if t == "-C":  # overrides the directory for THIS invocation only
                where = resolve(ctx, toks[i + 1]) if i + 1 < len(toks) else None
                i += 2
                continue
            if t in VALUE_OPTS:
                i += 2
                continue
            if t.startswith("-"):
                i += 1
                continue
            sub, args = t, toks[i + 1:]
            break
        if not inside(where, root):
            continue  # another repo's `main` is that repo's business
        if sub in ("checkout", "switch") and BRANCH in args:
            return f"`git {sub}` targeting `{BRANCH}`"
        if sub == "branch" and BRANCH in args and not (
            {"-d", "-D", "--delete"} & set(args)
        ):
            return f"`git branch` creating local `{BRANCH}`"
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    command = (payload.get("tool_input") or {}).get("command") or ""
    reason = offending(command, payload.get("cwd"))
    if not reason:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Blocked: {reason}. `main` is the CI-published distribution branch "
                "(publish-only, ADR 0007/0008) and must never be checked out in this "
                "working directory — it turns dev's ignored residue into untracked "
                "noise. Inspect it with `git show origin/main:<path>` or "
                "`git worktree add <dir> origin/main` instead."
            ),
        }
    }))


if __name__ == "__main__":
    # Never let a hook failure block or noise the Bash tool: swallow everything and
    # exit 0 (replaces the former `2>/dev/null || true` on the settings.json command).
    try:
        main()
    except Exception:  # noqa: BLE001 — a guard must fail open, not surface tracebacks
        pass
