"""worktree-root — own Claude Code's worktree creation so `checkout-root` places it.

One handler for three events, dispatched on `hook_event_name`:

- WorktreeCreate: create the worktree under the activation file's `checkout-root`
  (native `.claude/worktrees` when unset) of the MAIN checkout, with native branch
  naming, base ref and `.worktreeinclude` copying. Prints only the path on stdout.
  Any refusal exits 1 with the reason on stderr: creation fails loudly.
- SubagentStop: remove the agent's worktree through the shared guards below (the
  harness keeps every hook-created agent worktree). Always exits 0.
- WorktreeRemove: the same guards, at the root or the native root; a failed guard
  exits 1 and leaves everything in place.

Guards: `<root>/<leaf>` on branch `worktree-<leaf>`, clean including untracked files,
no commit absent from every other ref. Removal is unforced; `branch -d` may keep it.

Stdlib-only.
"""

import json
import os
import shutil
import subprocess
import sys
import time

# The shared modules live beside the hook dirs, at `<hooks-root>/_lib/`. That relative
# hop resolves both in primitives-core/ and in an installed plugin, where `hooks/_lib`
# is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import atelier_local  # noqa: E402


FETCH_TIMEOUT = 15  # seconds; native waits 5, the hook's own budget is 60
FETCH_MAX_AGE = 86400  # native refreshes origin when FETCH_HEAD is older than a day


class Refused(Exception):
    pass


def git(cwd, *args, timeout=60):
    env = {key: val for key, val in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(["git", "-C", str(cwd)] + list(args), env=env,
                          capture_output=True, text=True, timeout=timeout)


def must(cwd, *args):
    proc = git(cwd, *args)
    if proc.returncode:
        raise Refused("git {0} failed: {1}".format(" ".join(args), proc.stderr.strip()))
    return proc.stdout


def anchor(cwd):
    """(top, git common dir), resolved; ValueError outside a repository."""
    try:
        main, common = atelier_local.main_checkout(cwd)
        return str(main), str(common)
    except ValueError:
        pass
    # No main checkout (separate git dir, submodule): native anchors on the toplevel.
    top = git(cwd, "rev-parse", "--show-toplevel")
    common = git(cwd, "rev-parse", "--git-common-dir")
    if top.returncode or common.returncode:
        raise ValueError("{0} is not in a git repository".format(cwd))
    return (os.path.realpath(top.stdout.strip()),
            os.path.realpath(os.path.join(cwd, common.stdout.strip())))


def placement(cwd, native=False):
    """(top, root) for any dir in the repo; `native` ignores the key. ValueError when invalid."""
    main, common = anchor(cwd)
    root = None if native else atelier_local.checkout_root(main)
    if root is None:
        root = os.path.join(main, ".claude", "worktrees")
    root = os.path.realpath(str(root))
    # A committed `.claude` or `.claude/worktrees` symlink must not aim creation elsewhere.
    if not inside(root, main) or root == common or inside(root, common):
        raise ValueError("worktree root {0} is not strictly inside {1} and outside {2}".format(
            root, main, common))
    return main, root


def inside(path, parent):
    return path.startswith(parent.rstrip(os.sep) + os.sep)


def base_ref_setting(main):
    """`worktree.baseRef`: local project > project > user settings; unreadable skipped."""
    user = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    for path in (os.path.join(main, ".claude", "settings.local.json"),
                 os.path.join(main, ".claude", "settings.json"),
                 os.path.join(user, "settings.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                value = json.load(fh).get("worktree", {}).get("baseRef")
        except Exception:
            continue
        if value is not None:
            return value
    return None


def refresh_origin(main):
    """Best-effort `fetch origin <default>` when FETCH_HEAD is missing or a day old."""
    if git(main, "remote", "get-url", "origin").returncode:
        return
    try:
        common = git(main, "rev-parse", "--git-common-dir").stdout.strip()
        age = time.time() - os.path.getmtime(os.path.join(main, common, "FETCH_HEAD"))
    except OSError:
        age = FETCH_MAX_AGE
    if age < FETCH_MAX_AGE:
        return
    short = git(main, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD").stdout.strip()
    branch = short[len("origin/"):] if short.startswith("origin/") else "main"
    try:
        failed = git(main, "fetch", "-q", "origin", branch, timeout=FETCH_TIMEOUT).returncode
    except subprocess.TimeoutExpired:
        failed = True
    if failed:
        print("worktree-root: fetch of origin/{0} failed; using local refs".format(branch),
              file=sys.stderr)


def base_commit(cwd, main):
    """Native base: HEAD for `baseRef: head`, else origin/HEAD, origin/main, then HEAD."""
    if base_ref_setting(main) != "head":
        refresh_origin(main)
        for ref in ("refs/remotes/origin/HEAD", "refs/remotes/origin/main"):
            proc = git(main, "rev-parse", "--verify", "-q", ref + "^{commit}")
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
    return must(cwd, "rev-parse", "--verify", "HEAD").strip()


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
    flat = name.replace("/", "+")
    path = os.path.join(root, flat)
    if os.path.realpath(path) != path:
        raise Refused("worktree name {0!r} resolves to {1}, not {2}".format(
            name, os.path.realpath(path), path))
    if os.path.lexists(path):
        if path in registered(main):  # native resumes an existing worktree by name
            print(path)
            return
        raise Refused("{0} already exists".format(path))
    branch = "worktree-" + flat
    proc = git(main, "worktree", "add", "-b", branch, path, base_commit(cwd, main))
    sys.stderr.write(proc.stdout + proc.stderr)
    if proc.returncode:
        raise Refused("git worktree add failed")
    try:
        copy_includes(main, path)
    except (Refused, OSError) as exc:
        git(main, "worktree", "remove", "--force", path)
        git(main, "branch", "-D", branch)
        raise Refused("{0}; rolled back {1}".format(exc, path))
    print(path)


def release(main, root, path):
    """Remove `path` only as this hook creates it, clean and holding no unique commit."""
    leaf = os.path.basename(path)
    branch = "refs/heads/worktree-" + leaf
    if os.path.dirname(path) != root:
        raise Refused("{0} is not directly under {1}".format(path, root))
    entries = registered(main)
    if path not in entries:
        raise Refused("{0} is not a linked worktree of {1}".format(path, main))
    if entries[path] != branch:
        raise Refused("{0} is on {1}, not worktree-{2}".format(path, entries[path], leaf))
    # Explicit flag: `status.showUntrackedFiles=no` would otherwise hide untracked work.
    if must(path, "status", "--porcelain", "--untracked-files=all").strip():
        raise Refused("{0} has uncommitted changes".format(path))
    for line in must(path, "ls-files", "-v", "-z").split("\0"):
        tag, rel = line[:1], line[2:]
        # Both flags hide edits from status: assume-unchanged always, skip-worktree on disk.
        if tag.islower() or (tag == "S" and os.path.lexists(os.path.join(path, rel))):
            raise Refused("{0} has a hidden change at {1} (assume-unchanged or "
                          "skip-worktree)".format(path, rel))
    if must(path, "rev-list", "HEAD", "--not", "--exclude=worktree-" + leaf, "--branches",
            "--tags", "--remotes").strip():
        raise Refused("{0} has commits on no other ref".format(path))
    must(main, "worktree", "remove", path)
    if git(main, "branch", "-d", "worktree-" + leaf).returncode:
        print("worktree-root: removed {0}; kept branch worktree-{1}: not merged into HEAD".format(
            path, leaf), file=sys.stderr)


def subagent_stop(payload):
    agent_id, cwd = payload.get("agent_id"), payload.get("cwd")
    if not agent_id or not cwd:
        return
    path = os.path.realpath(cwd)
    if os.path.basename(path) != "agent-" + agent_id:
        return
    try:
        main, root = placement(os.path.dirname(path))
    except ValueError:
        return
    if os.path.dirname(path) == root:
        release(main, root, path)


def remove(payload):
    target = payload.get("worktree_path")
    if not target or not os.path.lexists(target):
        return
    path = os.path.realpath(target)
    parent = os.path.dirname(path)
    try:
        main, root = placement(parent)
        if parent != root:  # a `--worktree` session stays native while the key is set
            main, root = placement(parent, native=True)
        release(main, root, path)
    except Refused as exc:
        raise Refused("{0}; left in place".format(exc))
    except ValueError as exc:
        raise Refused("{0} is not a worktree this hook manages ({1}); left in place".format(
            path, exc))


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
