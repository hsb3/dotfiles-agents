#!/usr/bin/env python3
"""PreToolUse guard: deny Bash commands that would check out or recreate `main` locally.

`main` is the CI-assembled distribution branch (ADR 0007/0008) — a local checkout
turns dev's ignored residue into untracked noise and risks committing workbench
junk to the consumer surface. Inspect it via `git show origin/main:<path>` or a
throwaway `git worktree add ... origin/main` instead (worktrees use a detached or
differently-named checkout, so they never trip this guard's exact-token match).

Stdlib-only. Reads the hook JSON on stdin; on a match, emits a PreToolUse deny.
"""
import json
import re
import shlex
import sys

BRANCH = "main"

# git global options that consume a following value (must be skipped to find the subcommand)
VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def offending(command: str):
    """Return a human-readable reason if `command` checks out / creates local main."""
    # Examine each simple command so `cd x && git switch main` is still caught.
    for part in re.split(r"&&|\|\||;|\|", command):
        try:
            toks = shlex.split(part)
        except ValueError:
            toks = part.split()
        if "git" not in toks:
            continue
        toks = toks[toks.index("git"):]
        sub, args = None, []
        i = 1
        while i < len(toks):
            t = toks[i]
            if t in VALUE_OPTS:
                i += 2
                continue
            if t.startswith("-"):
                i += 1
                continue
            sub, args = t, toks[i + 1:]
            break
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
    reason = offending(command)
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
    main()
