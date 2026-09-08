#!/usr/bin/env python3
"""
lane-snapshot — the snapshot daemon behind the SessionStart hook.

Every worker worktree under the configured glob gets its whole working tree
(tracked, untracked, staged, unstaged) committed to `refs/lane-snapshots/<name>`
on a fixed interval. Workers hold read-only git and their output stays
uncommitted until hand-over, so a crash, a mistaken `worktree remove`, or a
prune destroys it. This is the net under that.

Recover one file:      git show refs/lane-snapshots/<name>:<path>
List what it holds:    git ls-tree -r --name-only refs/lane-snapshots/<name>
Recover the lot:       git restore --source refs/lane-snapshots/<name> -- .

Three modes:
  (default)   loop forever, one scan every LANE_SNAPSHOT_INTERVAL seconds
  --once      one scan pass, then exit (what the tests drive)
  --check     doctor mode: report ref staleness, exit nonzero when the net has
              a hole. A gate that cannot measure reports red, never green.

Root resolution, in precedence order:
  1. $LANE_SNAPSHOT_ROOT
  2. argv[1], which the hook fills in from the SessionStart payload's `cwd`
  3. `git rev-parse --show-toplevel` from this script's OWN directory

(3) is the mechanism the acceptance criterion names, and it is the fallback
rather than the primary for one reason: shipped as a plugin, this file lives in
the plugin cache under ${CLAUDE_PLUGIN_ROOT}, not in the repo being protected,
so its own location resolves to the wrong repository or to none. (3) is correct
and sufficient for a repo-local install, where the script does sit inside the
tree it guards. What matters in every case is that no absolute path is ever
hardcoded: the origin failure was a daemon whose baked-in ROOT survived a repo
rename and then snapshotted nothing, silently, for its entire life.

This file must have ZERO third-party dependencies (Python 3 stdlib only).
"""

import argparse
import glob
import hashlib
import os
import subprocess
import sys
import time

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import agentlog  # noqa: E402  (path must be primed before this import)

# ---------------------------------------------------------------------------
# Config (env-overridable; the same defaults are hardcoded here as fallbacks so
# the module behaves identically when run outside the shipped hook wiring)
# ---------------------------------------------------------------------------

INTERVAL_DEFAULT = 180
WORKTREES_DEFAULT = os.path.join(".claude", "worktrees", "agent-*")
LOG_STREAM = "lane-snapshot"
LOG_PATH_ENV = "LANE_SNAPSHOT_LOG_PATH"
REF_PREFIX = "refs/lane-snapshots/"

GIT_TIMEOUT = 120

# A snapshot commit is machine bookkeeping, not authorship. Pinning the ident
# keeps the commits identifiable and — the operational half — means the daemon
# still works on a machine with no `user.email` configured, where `commit-tree`
# would otherwise refuse.
SNAPSHOT_IDENT = {
    "GIT_AUTHOR_NAME": "lane-snapshot",
    "GIT_AUTHOR_EMAIL": "lane-snapshot@localhost",
    "GIT_COMMITTER_NAME": "lane-snapshot",
    "GIT_COMMITTER_EMAIL": "lane-snapshot@localhost",
}


def env_int(name, default, env=None):
    raw = (os.environ if env is None else env).get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def env_str(name, default, env=None):
    return (os.environ if env is None else env).get(name) or default


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def git(args, env=None):
    """Run one git command; return (returncode, stdout). Never raises — one
    lane's failing call must not take the daemon down for every other lane."""
    child = dict(os.environ)
    if env:
        child.update(env)
    try:
        proc = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=GIT_TIMEOUT, env=child,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "{0}: {1}".format(type(exc).__name__, exc)
    return proc.returncode, (proc.stdout or "").strip()


# ---------------------------------------------------------------------------
# Root + lane discovery
# ---------------------------------------------------------------------------

def resolve_root(argv_root=None, env=None, script_dir=None):
    """The repo whose lanes get snapshotted, or None when nothing resolves.

    Precedence as documented in the module docstring. Effects arrive as
    arguments (env dict, script dir) so the precedence is testable without a
    process. None is returned rather than a guess: a daemon pointed at the
    wrong tree is the failure this whole hook exists to stop.
    """
    env = os.environ if env is None else env
    for candidate in (env.get("LANE_SNAPSHOT_ROOT"), argv_root):
        if candidate:
            return os.path.abspath(candidate)
    script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))
    code, out = git(["-C", script_dir, "rev-parse", "--show-toplevel"])
    return out if code == 0 and out else None


def lane_paths(root, pattern=None, env=None):
    """Absolute paths of the worktrees matching the glob, sorted."""
    pattern = pattern or env_str("LANE_SNAPSHOT_WORKTREES", WORKTREES_DEFAULT, env)
    return sorted(p for p in glob.glob(os.path.join(root, pattern)) if os.path.isdir(p))


def _index_path(root, name):
    """A scratch index outside every worktree, unique per (root, lane).

    Out of tree so a live agent's own index is never touched, and keyed by root
    so two repos with a same-named lane cannot collide.
    """
    digest = hashlib.sha1(root.encode("utf-8", "replace")).hexdigest()[:10]
    return os.path.join(
        os.environ.get("TMPDIR") or "/tmp",
        "lane-snap-{0}-{1}.idx".format(digest, name),
    )


# ---------------------------------------------------------------------------
# One lane, one pass
# ---------------------------------------------------------------------------

def snapshot_lane(root, lane, log):
    """Snapshot one worktree. Returns the new commit sha, or None when nothing
    changed or the lane could not be read. Never raises."""
    name = os.path.basename(lane.rstrip(os.sep))
    ref = REF_PREFIX + name
    index = _index_path(root, name)
    try:
        # git REFUSES an existing-but-empty index file, and a stale index from a
        # crashed pass would silently narrow the snapshot. Always start clean.
        try:
            os.unlink(index)
        except FileNotFoundError:
            pass
        except OSError as exc:
            log({"event": "error", "lane": name, "error": "index unlink: {0}".format(exc)})
            return None

        scratch = {"GIT_INDEX_FILE": index}
        code, out = git(["-C", lane, "add", "-A"], scratch)
        if code != 0:
            log({"event": "error", "lane": name, "error": "add -A: {0}".format(out)})
            return None
        code, tree = git(["-C", lane, "write-tree"], scratch)
        if code != 0 or not tree:
            log({"event": "error", "lane": name, "error": "write-tree: {0}".format(tree)})
            return None

        code, parent = git(["-C", root, "rev-parse", "-q", "--verify", ref])
        parent = parent if code == 0 and parent else ""
        if parent:
            code, parent_tree = git(["-C", root, "rev-parse", parent + "^{tree}"])
            if code == 0 and parent_tree == tree:
                return None  # idle lane: identical tree, no commit, no cost

        message = "snapshot {0} {1}".format(
            name, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        args = ["-C", lane, "commit-tree", tree]
        if parent:
            args += ["-p", parent]
        args += ["-m", message]
        code, commit = git(args, SNAPSHOT_IDENT)
        if code != 0 or not commit:
            log({"event": "error", "lane": name, "error": "commit-tree: {0}".format(commit)})
            return None

        code, out = git(["-C", root, "update-ref", ref, commit])
        if code != 0:
            log({"event": "error", "lane": name, "error": "update-ref: {0}".format(out)})
            return None

        log({"event": "snapshot", "lane": name, "ref": ref, "commit": commit})
        return commit
    except Exception as exc:  # a lane must never kill the daemon
        log({"event": "error", "lane": name, "error": "{0}: {1}".format(type(exc).__name__, exc)})
        return None
    finally:
        try:
            os.unlink(index)
        except OSError:
            pass


def scan(root, log, pattern=None):
    """One pass over every lane. Returns (lanes_seen, snapshots_written)."""
    lanes = lane_paths(root, pattern)
    written = 0
    for lane in lanes:
        if snapshot_lane(root, lane, log):
            written += 1
    row = {"event": "scan", "root": root, "lanes": len(lanes), "snapshots": written}
    if not lanes:
        # THE row this hook exists for. A glob that matches nothing looks
        # exactly like a working net from the outside; only the daemon can say
        # it protected nothing.
        row["warning"] = (
            "no worktrees matched {0} under {1} — snapshotting nothing".format(
                pattern or env_str("LANE_SNAPSHOT_WORKTREES", WORKTREES_DEFAULT), root,
            )
        )
    log(row)
    return len(lanes), written


# ---------------------------------------------------------------------------
# --check: doctor mode
# ---------------------------------------------------------------------------

def ref_ages(root, now=None):
    """{lane name: age in seconds} for every refs/lane-snapshots/* ref, or None
    when the refs could not be read at all (unmeasurable, therefore red)."""
    code, out = git([
        "-C", root, "for-each-ref",
        "--format=%(refname)\t%(committerdate:unix)", REF_PREFIX,
    ])
    if code != 0:
        return None
    now = time.time() if now is None else now
    ages = {}
    for line in out.splitlines():
        if "\t" not in line:
            continue
        refname, stamp = line.split("\t", 1)
        try:
            ages[refname[len(REF_PREFIX):]] = now - int(stamp)
        except ValueError:
            continue
    return ages


def check(root, interval, pattern=None, out=sys.stdout):
    """Report the net's health. 0 = every live lane has a fresh ref."""
    if not root:
        print("lane-snapshot: no repo root resolved — cannot measure, reporting red", file=out)
        return 1
    ages = ref_ages(root)
    if ages is None:
        print("lane-snapshot: cannot read {0}* in {1} — cannot measure, "
              "reporting red".format(REF_PREFIX, root), file=out)
        return 1

    threshold = 2 * interval
    lanes = [os.path.basename(p.rstrip(os.sep)) for p in lane_paths(root, pattern)]
    problems = []
    for name in lanes:
        if name not in ages:
            problems.append("{0}: live worktree with no snapshot ref at all".format(name))
        elif ages[name] > threshold:
            problems.append(
                "{0}: stale — last snapshot {1}s ago, threshold {2}s".format(
                    name, int(ages[name]), threshold,
                )
            )

    orphans = sorted(set(ages) - set(lanes))
    for name in orphans:
        # Adds-only pruning: a ref outliving its worktree is the point, not a
        # fault. Reported so the operator knows what is holding disk.
        print("lane-snapshot: {0}{1} kept for a worktree that is gone "
              "(recover: git show {0}{1}:<path>)".format(REF_PREFIX, name), file=out)

    if problems:
        print("lane-snapshot: {0} problem(s) against a {1}s threshold".format(
            len(problems), threshold), file=out)
        for problem in problems:
            print("  - " + problem, file=out)
        return 1
    if not lanes:
        print("lane-snapshot: no live lanes under {0} — nothing to protect".format(root), file=out)
        return 0
    print("lane-snapshot: {0} live lane(s), all snapshotted within {1}s".format(
        len(lanes), threshold), file=out)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="snapshot_lanes.py",
        description=(
            "Snapshot every agent worktree's working tree into "
            "refs/lane-snapshots/<name> on an interval. "
            "Recover with: git show refs/lane-snapshots/<name>:<path>"
        ),
    )
    parser.add_argument(
        "root", nargs="?",
        help="repo root to protect; overridden by $LANE_SNAPSHOT_ROOT, and "
             "derived from this script's own location when neither is given",
    )
    parser.add_argument("--once", action="store_true", help="one scan pass, then exit")
    parser.add_argument(
        "--check", action="store_true",
        help="doctor mode: report ref staleness against 2x the interval; "
             "exit 1 when a live lane is stale, unprotected, or unmeasurable",
    )
    parser.add_argument(
        "--interval", type=int, default=None,
        help="seconds between passes (default $LANE_SNAPSHOT_INTERVAL or {0})".format(
            INTERVAL_DEFAULT),
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    interval = args.interval if args.interval is not None else env_int(
        "LANE_SNAPSHOT_INTERVAL", INTERVAL_DEFAULT
    )
    root = resolve_root(args.root)

    if args.check:
        return check(root, interval)

    log = agentlog.make_logger(LOG_STREAM, LOG_PATH_ENV, root)
    if not root:
        log({"event": "error", "error": "no repo root resolved — refusing to run"})
        print("lane-snapshot: no repo root resolved", file=sys.stderr)
        return 1

    log({
        "event": "start",
        "root": root,
        "interval": interval,
        "pattern": env_str("LANE_SNAPSHOT_WORKTREES", WORKTREES_DEFAULT),
        "pid": os.getpid(),
        "once": bool(args.once),
    })

    while True:
        try:
            scan(root, log)
        except Exception as exc:  # a bad pass must not end the daemon
            log({"event": "error", "error": "scan: {0}: {1}".format(type(exc).__name__, exc)})
        if args.once:
            return 0
        time.sleep(max(interval, 1))


if __name__ == "__main__":
    sys.exit(main())
