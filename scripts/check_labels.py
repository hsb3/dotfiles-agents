#!/usr/bin/env python3
"""Label-vocabulary gate — the GitHub repo's label set is closed and must not drift.

GitHub mints labels on the side. `gh issue create --label`, a template, an imported
issue, an action, or a human in the web UI can each add a name nobody declared, and the
UI shows the result as a flat colourful list with no signal about which entries are
intentional. That is how this repo accumulated a stale sprawl alongside the labels
actually in use — `status:*`, `priority:*`, `area:*`, `phase:*`, `bug`, `feature`,
`chore`, `docs` and more, none of them ever announced, all of them since deleted by
hand. (The list is illustrative; the live set is whatever `gh` reports.) A vocabulary that
grows silently stops meaning anything: filters miss issues, two names split one concept,
and no reader can tell a live convention from a fossil.

So the set is CLOSED (owner ruling, 2026-09-07), and closed means exactly this:

  1. Every live label name is in `VOCABULARY`. A name that is not is an EXTRA, reported
     with the `gh label delete` that removes it.
  2. Every `VOCABULARY` name is live. One that is not is MISSING, reported with the
     `gh label create` that restores it. Missing matters as much as extra — a label
     deleted by hand quietly breaks the issue template that assigns it.

Set equality in both directions, and every problem carries its own fix command, because
a gate whose output has to be translated into commands is a gate people argue with.

`VOCABULARY` is a constant here rather than a parsed file because no tracked file declares
THIS set. `primitives-core/skills/board-triage/scripts/core-labels.txt` declares the core
KATA-BOARD vocabulary (decision-023), and the set below is a strict SUBSET of it: the
board-only names (`handoff`, `meta`, `needs-review`, `up-next`, the whole `area:*` family)
never reach GitHub, because the sync here is import-only and board labels do not propagate
outward. Reading that file would therefore make this gate demand labels the repo must not
have. `tests/test_core_labels.py` pins the subset relation instead, so the two cannot drift
apart silently. `.github/ISSUE_TEMPLATE/bug.yml` names one label it assigns, and
`primitives-core/hooks/plugin-feedback-session/report_issue.py` carries overridable
defaults for a CONSUMER's repo; neither is a declaration of ours. Deleting a label a
template depends on still goes red — through the missing-label path, check 2.

Where it runs: a step in the `drift guards` CI job and `make labels`, NOT in `make ci`.
Reading the live set needs `gh` and NETWORK, and `make ci` is offline-and-zero-install by
design; a CI job of its own was equally unavailable because `dev`'s branch protection
pins required checks by job NAME, so adding one would strand every open PR on a check
that never reports. Same placement, and for the same two reasons, as
`scripts/check_version_bump.py` and `scripts/check_vendored_drift.py`.

Network and tooling contract — EVERY failure to read the live set is RED, the same house
rule every CI-only gate here follows (decision-016 point 4): a gate that cannot measure is
red, never green, because a step that exits 0 having measured nothing is indistinguishable
in the CI summary from one that measured and found the set clean, and the whole cost of
that ruling is a re-run when the network blips.

  gh missing from PATH        exit 1. "A missing tool is a failed gate, never a skipped
                              one" — a machine that cannot run the check must not report
                              green, or everyone learns to read green as "it ran".
  gh fails, host unreachable  exit 1, saying so. NOT evidence of drift — the message says
                              that explicitly, so nobody goes hunting for a bad label —
                              but nothing was measured, so it cannot be green.
  gh fails, host reachable    exit 1, echoing gh's stderr. api.github.com answered and gh
                              still failed: broken auth, missing scope, rate limit.

The reachability probe therefore decides only WHICH failure gets named, not the exit
code. It stays because "your network is down" and "your token is bad" are a ten-second
and a thirty-minute debug respectively.

Deliberately NOT covered: label COLOUR and DESCRIPTION — only the name set is closed, and
churning on a hex code would make this gate noise. Also not covered: which labels are
applied to which issues (a label may legitimately go unused), and the kata board's own
labels, which are a different namespace entirely and only reach this gate if kata's
GitHub sync mints a new label on the repo — at which point it shows up here as an extra,
which is the intended alarm.

Stdlib-only, deterministic. Exit 0 = the live set was read and matches; exit 1 = drift,
or the live set could not be read at all.
Usage: python3 scripts/check_labels.py [--labels-json <file>|-]

Run the live path from a checkout of the repo you mean to check: `gh` resolves owner/repo
from the cwd's git remote, so from a fork it checks the FORK's labels, and from outside a
repo it fails red. `--labels-json` runs from anywhere.

"""

import argparse
import json
import shutil
import socket
import subprocess
import sys

VOCABULARY = frozenset(
    {
        "type:feat",  # new capability
        "type:fix",  # bug intake, the only kind of issue humans file here
        "type:chore",  # maintenance, deps, housekeeping
        "decision",  # awaiting or recording an owner ruling
        "epic",  # a container for child issues
    }
)

GH_TIMEOUT = 60
PROBE_HOST = ("api.github.com", 443)
PROBE_TIMEOUT = 5


def check(live_names):
    """Sorted problem strings for one live label set. Pure: no network, no disk, no gh."""
    live = set(live_names)
    problems = [
        f"extra label {name!r} is not in the closed vocabulary — "
        f"declare it in scripts/check_labels.py or remove it: gh label delete '{name}'"
        for name in live - VOCABULARY
    ]
    problems += [
        f"missing label {name!r} is in the vocabulary but not on the repo — "
        f"restore it: gh label create '{name}'"
        for name in VOCABULARY - live
    ]
    return sorted(problems)


def parse_gh_labels(text):
    """Label names out of `gh label list --json name` output: `[{"name": "..."}]`."""
    return [entry["name"] for entry in json.loads(text)]


def read_labels(path):
    """Injected label set from a file, or from stdin when path is `-`."""
    if path == "-":
        return parse_gh_labels(sys.stdin.read())
    with open(path, encoding="utf-8") as fh:
        return parse_gh_labels(fh.read())


def _github_reachable():
    """Can we open a socket to the API at all? Separates a blip from a broken gate."""
    try:
        socket.create_connection(PROBE_HOST, timeout=PROBE_TIMEOUT).close()
        return True
    except OSError:
        return False


def gh_labels():
    """Live label names via gh. Returns (names, error) — exactly one is None."""
    if shutil.which("gh") is None:
        return None, "gh is not on PATH — this gate cannot run here"
    try:
        p = subprocess.run(
            ["gh", "label", "list", "--json", "name", "--limit", "200"],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, f"gh label list did not complete: {exc}"
    if p.returncode != 0:
        return None, f"gh label list failed: {p.stderr.strip() or '(no stderr)'}"
    try:
        return parse_gh_labels(p.stdout), None
    except (ValueError, KeyError, TypeError) as exc:
        return None, f"gh label list returned unparseable JSON: {exc}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--labels-json",
        metavar="FILE",
        help="read `gh label list --json name` output from FILE (`-` for stdin) "
        "instead of shelling out to gh",
    )
    args = ap.parse_args(argv)

    if args.labels_json:
        live = read_labels(args.labels_json)
        source = f"injected from {args.labels_json}"
    else:
        live, err = gh_labels()
        if err is not None:
            # Every read failure is red — the probe only picks the message. Guarded on
            # `gh` being present so a missing binary is never blamed on the network.
            if shutil.which("gh") is not None and not _github_reachable():
                err += ("; api.github.com is unreachable — that is a reachability "
                        "failure, NOT evidence of drift, but nothing was measured and a "
                        "gate that cannot measure is red (decision-016). Re-run it")
            print(f"✗ labels: {err}")
            return 1
        source = "gh label list"

    problems = check(live)
    if problems:
        print(f"✗ labels: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"✓ labels clean — {len(live)} live label(s) match the closed vocabulary of "
          f"{len(VOCABULARY)} ({source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
