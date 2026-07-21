"""CLI entrypoint — ``agent-harness`` (also ``python -m agent_harness``).

One call shape (DESIGN §1): run(harness, model, candidate, case, config) → rows.
The candidate *directory* is passed as a path at runtime (``--candidate-dir``);
the harness never reads repo files outside ``harness/`` (coupling rule §5).

Exit codes: 0 ok · 1 preflight/loadability fail · 2 bad args/candidate ·
3 unknown harness.
"""

from __future__ import annotations

import argparse
import os
import sys

from .adapters import UnknownHarness, get_adapter, list_adapters
from .candidate import detect_kind
from .core import (
    DEFAULT_CASES_DIR,
    DEFAULT_RESULTS,
    DEFAULT_RUNS_DIR,
    DEFAULT_TIMEOUT,
    DEFAULT_TRIALS,
    run_candidate,
    smoke,
)
from .grading import DEFAULT_GRADER_MODEL
from .ledger import read_rows
from .report import print_report


def _parser():
    ap = argparse.ArgumentParser(
        prog="agent-harness",
        description="Evaluate a coding-agent extender under a harness (DESIGN §3).",
    )
    ap.add_argument("candidate", help="candidate name (ledger + cases/<name>/ key)")
    ap.add_argument(
        "--candidate-dir",
        help="path to the extender dir to inject (required unless --report)",
    )
    ap.add_argument(
        "--harness",
        default="claude",
        help=f"harness to drive (valid: {', '.join(list_adapters())})",
    )
    ap.add_argument("--case", help="run a single case id")
    ap.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    ap.add_argument("--configs", default="with,baseline")
    ap.add_argument("--model", help="trial model override (default: CLI default)")
    ap.add_argument(
        "--grader-model",
        default=DEFAULT_GRADER_MODEL,
        help="pinned grader model (recorded per row; keep stable for comparability)",
    )
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--allow-bash", action="store_true")
    ap.add_argument(
        "--keep-workspaces",
        action="store_true",
        help="keep passing trials' workspaces too (failures are always kept)",
    )
    ap.add_argument("--smoke", action="store_true", help="loadability check only")
    ap.add_argument("--report", action="store_true", help="aggregate existing rows")
    ap.add_argument("--cases-dir", default=DEFAULT_CASES_DIR)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)
    return ap


def main(argv=None):
    args = _parser().parse_args(argv)

    try:
        adapter = get_adapter(args.harness, allow_bash=args.allow_bash)
    except UnknownHarness as exc:
        print(str(exc), file=sys.stderr)
        return 3

    if args.report:
        print_report(args.candidate, read_rows(args.results, args.candidate))
        return 0

    pf = adapter.preflight()
    if pf == "missing":
        print(
            f"{adapter.name} CLI not on PATH — install it or run in the devcontainer",
            file=sys.stderr,
        )
        return 1
    if pf == "noauth":
        print(f"{adapter.name} CLI not authenticated — configure credentials", file=sys.stderr)
        return 1

    if not args.candidate_dir:
        print("--candidate-dir is required (path to the extender to inject)", file=sys.stderr)
        return 2
    if not os.path.isdir(args.candidate_dir):
        print(f"no such candidate dir: {args.candidate_dir}", file=sys.stderr)
        return 2
    kind = detect_kind(args.candidate_dir)
    if kind is None:
        print(
            f"{args.candidate_dir}: not recognizable as skill / agent / plugin",
            file=sys.stderr,
        )
        return 2

    if args.smoke:
        return 0 if smoke(adapter, args.candidate, kind, args.candidate_dir, args) else 1

    run_candidate(adapter, args.candidate, kind, args.candidate_dir, args)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
