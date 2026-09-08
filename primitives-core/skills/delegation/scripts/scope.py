#!/usr/bin/env python3
"""Measure a brief's owned-file list before the brief is dispatched.

Takes the paths a brief hands a worker -- on argv, or one per line on stdin when argv
carries none -- and reports how much material that list is: `files`, `bytes`, `lines`,
and how many of those files are `binary`.

An entry it cannot measure is never folded into the totals. A glob, a missing path, a
directory, or a file it cannot read is listed under `unresolved` and the exit code is 1,
so the figure reads as a floor rather than a total. Globs are reported, never expanded:
expanding here would measure whatever this process's cwd happens to contain, which is
not necessarily the tree the brief was written against.

This is a dispatch-time measurement of a brief. It is deliberately not part of
`context-watermark`, which measures a live transcript on `UserPromptSubmit` and
`PostToolUse`; nothing here reads a transcript or fires on an event.

Stdlib only. No clocks, no randomness; the same input yields the same bytes out.
Exit codes: 0 fully measured, 1 something unresolved, 2 no paths given.
"""

import argparse
import json
import os
import sys

GLOB_CHARS = "*?["
NUL_WINDOW = 8000
TOTALS = ("files", "bytes", "lines", "binary")


def unresolved_reason(path):
    """Why `path` cannot be measured, or None when it is a readable regular file."""
    if os.path.isfile(path):
        return None
    if os.path.isdir(path):
        return "directory"
    if any(char in path for char in GLOB_CHARS):
        return "glob"
    return "missing"


def measure(entries):
    """Total up `entries`, an owned-file list, into one figure dict."""
    figure = {"files": 0, "bytes": 0, "lines": 0, "binary": 0, "unresolved": []}
    for path in dict.fromkeys(entries):
        reason = unresolved_reason(path)
        data = None
        if reason is None:
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except OSError:
                reason = "unreadable"
        if reason is not None:
            figure["unresolved"].append({"path": path, "reason": reason})
            continue
        figure["files"] += 1
        figure["bytes"] += len(data)
        if b"\x00" in data[:NUL_WINDOW]:
            figure["binary"] += 1
        else:
            trailing = 1 if data and not data.endswith(b"\n") else 0
            figure["lines"] += data.count(b"\n") + trailing
    return figure


def render(figure):
    """The figure as plain text: one `key value` line each, then any unresolved entry."""
    out = ["%s %d" % (key, figure[key]) for key in TOTALS]
    out.append("unresolved %d" % len(figure["unresolved"]))
    width = max([len(item["reason"]) for item in figure["unresolved"]] or [0])
    for item in figure["unresolved"]:
        out.append("  %-*s  %s" % (width, item["reason"], item["path"]))
    return "\n".join(out) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="scope.py",
        description="Measure a brief's owned-file list: files, bytes, lines, binaries.",
        epilog="Exit 1 means at least one entry could not be measured, so the totals "
               "are a floor. Globs are reported, never expanded.",
    )
    parser.add_argument(
        "path",
        nargs="*",
        help="the brief's owned files; read from stdin, one per line, when omitted",
    )
    parser.add_argument("--json", action="store_true", help="emit the figure as JSON")
    return parser


def main(argv=None, stdin=None, stdout=None, stderr=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)

    paths = args.path or [line.strip() for line in stdin.read().splitlines() if line.strip()]
    if not paths:
        stderr.write(
            "scope: no paths given -- pass the brief's owned-file list on argv,"
            " or one path per line on stdin\n"
        )
        return 2

    figure = measure(paths)
    if args.json:
        stdout.write(json.dumps(figure, indent=2, sort_keys=True) + "\n")
    else:
        stdout.write(render(figure))
    return 1 if figure["unresolved"] else 0


if __name__ == "__main__":
    sys.exit(main())
