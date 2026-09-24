#!/usr/bin/env python3
"""Catch a file a report-only subagent (reviewer/scout) left behind in a checkout.

    trace_check.py snapshot <repo> <file>   # before dispatch
    trace_check.py check <repo> <file>      # after dispatch -- names anything new

Both run `git status --porcelain=v1 -z --untracked-files=all --ignored=traditional`;
with `-uall`, `traditional` lists files inside an already-ignored dir individually
instead of collapsing to the dir, so a leak dropped there is still caught. Every git
call carries `--no-optional-locks` so a check never blocks on (or takes) index.lock.

ponytail: a path already dirty/untracked at snapshot time is invisible to `check` unless
its status code changes; only new (code, path) pairs are caught. Hash contents if a
rewrite of an existing entry ever matters. Also invisible: a write under `.git/` itself
(git status never reports it), and a write inside a nested repo or nested worktree --
status collapses those to one dir entry regardless of `-uall`.

Exit codes: snapshot 0 written, 2 usage/git error/refused path/missing parent dir.
check 0 clean, 1 new/gone entries or HEAD/stash change found, 2 usage/git
error/malformed snapshot/toplevel mismatch. Stdlib only.
"""

import argparse
import json
import os
import subprocess
import sys

STATUS_ARGS = [
    "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=traditional",
]


def run_git(repo, *args):
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", repo] + list(args), capture_output=True
    )


def git_entries(repo):
    """Run `git status` in `repo`; return (entries, error) -- error is a message or None."""
    proc = run_git(repo, *STATUS_ARGS)
    if proc.returncode != 0:
        return None, proc.stderr.decode("utf-8", "replace").strip() or "git status failed"
    return parse_status_z(proc.stdout), None


def parse_status_z(raw):
    """Parse `-z` porcelain output into a list of [code, path] pairs.

    A rename/copy record carries a second NUL-terminated field (the origin path);
    it is consumed so later records parse correctly but its value is dropped --
    only the destination path is tracked as the entry. The R/C marker can land in
    either status column (index vs. worktree), so both are checked.
    """
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    entries = []
    i = 0
    while i < len(fields):
        record = fields[i].decode("utf-8", "surrogateescape")
        code, path = record[:2], record[3:]
        if code[0] in "RC" or code[1] in "RC":
            i += 1  # origin path field, consumed and discarded
        entries.append([code, path])
        i += 1
    return entries


def git_ref(repo, ref):
    """`git rev-parse -q --verify <ref>`, or None when the ref does not resolve."""
    proc = run_git(repo, "rev-parse", "-q", "--verify", ref)
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", "replace").strip()


def toplevel(repo):
    """Resolve the checkout root; returns (path, error)."""
    proc = run_git(repo, "rev-parse", "--show-toplevel")
    if proc.returncode != 0:
        return None, proc.stderr.decode("utf-8", "replace").strip() or "not a git repository"
    return proc.stdout.decode("utf-8", "surrogateescape").strip(), None


def parent_dir_inside(root, file_path):
    """True when file_path's parent dir is `root` or nested under it, else False;
    None when the parent dir does not exist (the caller reports that separately).

    Walks up via `os.path.samefile` rather than string comparison so a bypass through
    a subdirectory alias or a case-insensitive-filesystem spelling of `root` is caught.
    """
    parent = os.path.dirname(os.path.abspath(file_path)) or os.sep
    if not os.path.isdir(parent):
        return None
    cur = parent
    while True:
        if os.path.samefile(cur, root):
            return True
        nxt = os.path.dirname(cur)
        if nxt == cur:
            return False
        cur = nxt


def display(path):
    """Render a path for stdout even when it is not valid UTF-8 -- never raises."""
    return path.encode("utf-8", "surrogateescape").decode("utf-8", "backslashreplace")


def cmd_snapshot(repo, file_path, stderr):
    root, error = toplevel(repo)
    if error is not None:
        stderr.write("trace_check: %s\n" % error)
        return 2

    inside = parent_dir_inside(root, file_path)
    if inside is None:
        stderr.write("trace_check: parent directory of %s does not exist\n" % file_path)
        return 2
    if inside:
        stderr.write(
            "trace_check: refusing to write the snapshot inside %s -- it would trace itself\n"
            % root
        )
        return 2

    entries, error = git_entries(repo)
    if error is not None:
        stderr.write("trace_check: %s\n" % error)
        return 2

    snapshot = {
        "toplevel": root,
        "head": git_ref(repo, "HEAD"),
        "stash": git_ref(repo, "refs/stash"),
        "entries": sorted(entries),
    }
    with open(file_path, "w") as handle:
        json.dump(snapshot, handle, sort_keys=True, indent=2)
        handle.write("\n")
    return 0


def _load_snapshot(file_path, stderr):
    """Read and validate the snapshot shape; return (toplevel, head, stash, pairs) or None."""
    try:
        with open(file_path) as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        stderr.write("trace_check: could not read snapshot %s: %s\n" % (file_path, exc))
        return None
    try:
        root, head, stash = data["toplevel"], data["head"], data["stash"]
        pairs = [(code, path) for code, path in data["entries"]]
    except (KeyError, TypeError, ValueError):
        stderr.write("trace_check: malformed snapshot %s\n" % file_path)
        return None
    return root, head, stash, pairs


def cmd_check(repo, file_path, stdout, stderr):
    loaded = _load_snapshot(file_path, stderr)
    if loaded is None:
        return 2
    snap_root, snap_head, snap_stash, known = loaded

    root, error = toplevel(repo)
    if error is not None:
        stderr.write("trace_check: %s\n" % error)
        return 2
    if root != snap_root:
        stderr.write(
            "trace_check: snapshot was taken in %s, this checkout is %s\n" % (snap_root, root)
        )
        return 2

    entries, error = git_entries(repo)
    if error is not None:
        stderr.write("trace_check: %s\n" % error)
        return 2
    current = {(code, path) for code, path in entries}
    known_set = set(known)
    new = sorted(current - known_set)
    gone = sorted(known_set - current)

    head = git_ref(repo, "HEAD")
    stash = git_ref(repo, "refs/stash")

    for code, path in new:
        stdout.write("%s %s\n" % (code, display(path)))
    for code, path in gone:
        stdout.write("gone %s %s\n" % (code, display(path)))
    if head != snap_head:
        stdout.write("head %s -> %s\n" % (snap_head or "none", head or "none"))
    if stash != snap_stash:
        stdout.write("stash %s -> %s\n" % (snap_stash or "none", stash or "none"))

    changed = bool(new) or bool(gone) or head != snap_head or stash != snap_stash
    return 1 if changed else 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="trace_check.py",
        description="Detect a file a report-only subagent left behind in a checkout.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "check"):
        p = sub.add_parser(name)
        p.add_argument("repo", help="the checkout to watch")
        p.add_argument("file", help="the snapshot file")
    return parser


def main(argv=None, stdout=None, stderr=None):
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if args.command == "snapshot":
            return cmd_snapshot(args.repo, args.file, stderr)
        return cmd_check(args.repo, args.file, stdout, stderr)
    except OSError as exc:
        stderr.write("trace_check: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
