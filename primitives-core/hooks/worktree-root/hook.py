"""worktree-root — own Claude Code's worktree creation so `checkout-root` places it.

One handler for three events, dispatched on `hook_event_name`:

- WorktreeCreate: create the worktree under the activation file's `checkout-root`
  (native `.claude/worktrees` when unset) of the MAIN checkout, with native branch
  naming, base ref and `.worktreeinclude` copying. Prints only the path on stdout.
  Any refusal exits 1 with the reason on stderr: creation fails loudly.
- SubagentStop: remove an agent worktree this hook created when it is clean and its
  branch holds no commit reachable only from itself (the harness keeps every
  hook-created agent worktree). Always exits 0.
- WorktreeRemove: remove the registered worktree and its `worktree-*` branch.

Stdlib-only.
"""

import json
import os
import shutil
import subprocess
import sys

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`. That relative
# hop resolves both in primitives-core/ and in an installed plugin, where `hooks/_lib`
# is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import atelier_local  # noqa: E402


class Refused(Exception):
    pass


def git(cwd, *args):
    env = {key: val for key, val in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(["git", "-C", str(cwd)] + list(args), env=env,
                          capture_output=True, text=True, timeout=60)


def must(cwd, *args):
    proc = git(cwd, *args)
    if proc.returncode:
        raise Refused("git {0} failed: {1}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout


def placement(cwd):
    """(main checkout, root) for any dir in the repo; ValueError when invalid."""
    main, _common = atelier_local.main_checkout(cwd)
    root = atelier_local.checkout_root(str(main))
    if root is None:
        root = os.path.join(str(main), ".claude", "worktrees")
    return str(main), os.path.realpath(str(root))


def base_ref_setting(main):
    """`worktree.baseRef`: local project > project > user settings; unreadable skipped."""
    for path in (os.path.join(main, ".claude", "settings.local.json"),
                 os.path.join(main, ".claude", "settings.json"),
                 os.path.join(os.path.expanduser("~"), ".claude", "settings.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                value = json.load(fh).get("worktree", {}).get("baseRef")
        except Exception:
            continue
        if value is not None:
            return value
    return None


def registered(main):
    """{realpath: branch ref or None} from `git worktree list --porcelain`."""
    entries, path = {}, None
    for line in must(main, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = os.path.realpath(line[len("worktree "):])
            entries[path] = None
        elif line.startswith("branch ") and path:
            entries[path] = line[len("branch "):]
    return entries


def copy_includes(main, dest):
    """Copy untracked, gitignored files matching `.worktreeinclude` (native semantics)."""
    include = os.path.join(main, ".worktreeinclude")
    if not os.path.isfile(include):
        return
    # Two listings intersected: combining both exclude sources in one call is a union.
    ignored = set(must(main, "ls-files", "-z", "--others", "--ignored",
                       "--exclude-standard").split("\0"))
    listed = must(main, "ls-files", "-z", "--others", "--ignored",
                  "--exclude-from=" + include).split("\0")
    real_dest = os.path.realpath(dest)
    for rel in sorted(p for p in listed if p and p in ignored):
        src, dst = os.path.join(main, rel), os.path.join(dest, rel)
        if os.path.islink(src) or not os.path.isfile(src) or os.path.lexists(dst):
            continue
        parent = os.path.realpath(os.path.dirname(dst))
        if parent != real_dest and not parent.startswith(real_dest + os.sep):
            continue  # a committed symlink would carry the copy out of the worktree
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print("worktree-root: copied {0}".format(rel), file=sys.stderr)


def create(payload):
    cwd = payload.get("cwd") or os.getcwd()
    name = payload.get("name") or ""
    try:
        main, root = placement(cwd)
    except ValueError as exc:
        raise Refused(str(exc))
    if not name or os.path.isabs(name) or ".." in name.replace("\\", "/").split("/"):
        raise Refused("worktree name {0!r} must be a non-empty relative name with no "
                      "'..' segment".format(name))
    path = os.path.realpath(os.path.join(root, name))
    if not path.startswith(root + os.sep):
        raise Refused("worktree name {0!r} resolves to {1}, not strictly inside {2}".format(
            name, path, root))
    if os.path.lexists(path):
        raise Refused("{0} already exists".format(path))
    branch = "worktree-" + name.replace("/", "+")
    head = must(cwd, "rev-parse", "--verify", "HEAD").strip()
    base = head
    if base_ref_setting(main) != "head":
        origin = git(main, "rev-parse", "--verify", "-q", "refs/remotes/origin/HEAD")
        if origin.returncode == 0 and origin.stdout.strip():
            base = origin.stdout.strip()
    proc = git(main, "worktree", "add", "-b", branch, path, base)
    sys.stderr.write(proc.stdout + proc.stderr)
    if proc.returncode:
        raise Refused("git worktree add failed")
    copy_includes(main, path)
    print(path)


def subagent_stop(payload):
    agent_id, cwd = payload.get("agent_id"), payload.get("cwd")
    if not agent_id or not cwd:
        return
    try:
        main, root = placement(cwd)
    except ValueError:
        return
    path = os.path.realpath(cwd)
    branch = "refs/heads/worktree-agent-" + agent_id
    if path != os.path.realpath(os.path.join(root, "agent-" + agent_id)):
        return
    if registered(main).get(path) != branch:
        return
    if must(path, "status", "--porcelain").strip():
        print("worktree-root: kept {0}: uncommitted changes".format(path), file=sys.stderr)
        return
    only_here = must(path, "rev-list", "HEAD", "--not",
                     "--exclude=" + branch[len("refs/heads/"):], "--branches",
                     "--tags", "--remotes")
    if only_here.strip():
        print("worktree-root: kept {0}: commits on no other ref".format(path), file=sys.stderr)
        return
    must(main, "worktree", "remove", "--force", path)
    must(main, "branch", "-D", branch[len("refs/heads/"):])


def remove(payload):
    target = payload.get("worktree_path")
    if not target or not os.path.lexists(target):
        return
    path = os.path.realpath(target)
    try:
        main, _common = atelier_local.main_checkout(payload.get("cwd") or path)
    except ValueError as exc:
        raise Refused(str(exc))
    main = str(main)
    entries = registered(main)
    if path == os.path.realpath(main) or path not in entries:
        raise Refused("{0} is not a linked worktree of {1}".format(path, main))
    must(main, "worktree", "remove", "--force", path)
    branch = entries[path] or ""
    if branch.startswith("refs/heads/worktree-"):
        must(main, "branch", "-D", branch[len("refs/heads/"):])


HANDLERS = {"WorktreeCreate": create, "SubagentStop": subagent_stop,
            "WorktreeRemove": remove}


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    handler = HANDLERS.get(event)
    if handler is None:
        return 0
    try:
        handler(payload)
    except (Refused, OSError, subprocess.SubprocessError) as exc:
        print("worktree-root: {0}: {1}".format(event, exc), file=sys.stderr)
        return 0 if event == "SubagentStop" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
