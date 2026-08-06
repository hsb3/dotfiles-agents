"""CLI entrypoint — ``agent-harness`` (also ``python -m agent_harness``).

One call shape (DESIGN §1): run(harness, model, candidate, case, config) → rows.
The candidate — a directory, or a flat agent ``.md`` file — is passed as a
path at runtime (``--candidate-dir``); the harness never reads repo files
outside ``harness/`` (coupling rule §5).

Exit codes: 0 ok · 1 preflight/loadability fail · 2 bad args/candidate ·
3 unknown harness.
"""

from __future__ import annotations

import argparse
import contextlib
import sys

from .adapters import UnknownHarness, get_adapter, list_adapters
from .candidate import detect_kind, resolved_candidate_dir
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
        help=(
            "path to the extender to inject — a directory, or a flat agent "
            ".md file (required unless --report)"
        ),
    )
    ap.add_argument(
        "--harness",
        default="claude",
        help=(
            "harness(es) to drive — comma-separated for a grid "
            f"(valid: {', '.join(list_adapters())}; e.g. claude,opencode)"
        ),
    )
    ap.add_argument("--case", help="run a single case id")
    ap.add_argument(
        "--campaign",
        default="",
        help=(
            "campaign label — the first dimension of the resume key "
            "(campaign|harness|model|candidate|case|config|trial). Use it to keep "
            "a re-run after a harness fix distinct from the pre-fix rows in the "
            "same ledger (e.g. --campaign skillfix). Default: '' (unlabeled)."
        ),
    )
    ap.add_argument("--trials", type=int, default=DEFAULT_TRIALS)
    ap.add_argument("--configs", default="with,baseline")
    ap.add_argument(
        "--model",
        help=(
            "trial model(s) — comma-separated for a grid (default: CLI default). "
            "Bare ids are provider-normalized per harness, so one list spans "
            "claude and opencode cells (e.g. claude-sonnet-4-5,claude-haiku-4-5)"
        ),
    )
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


def _cells(harness_arg, model_arg):
    """Expand comma-separated --harness/--model into ``(harness, model)`` cells.

    Model ids stay as-typed here (each adapter provider-normalizes at invocation,
    so one bare-id list spans claude and opencode cells — DESIGN §4). A missing
    ``--model`` yields a single ``None`` cell (the CLI default). Harness order and
    dedupe are preserved so ``claude,opencode`` runs claude cells then opencode.
    """
    harnesses = [h.strip() for h in (harness_arg or "").split(",") if h.strip()] or ["claude"]
    models = [m.strip() for m in model_arg.split(",") if m.strip()] if model_arg else [None]
    if not models:
        models = [None]
    return [(h, m) for h in harnesses for m in models]


def main(argv=None):
    args = _parser().parse_args(argv)
    cells = _cells(args.harness, args.model)

    # Validate every harness name up front (any unknown -> exit 3, unchanged).
    harnesses = list(dict.fromkeys(h for h, _ in cells))
    try:
        adapters = {h: get_adapter(h, allow_bash=args.allow_bash) for h in harnesses}
    except UnknownHarness as exc:
        print(str(exc), file=sys.stderr)
        return 3

    if args.report:
        print_report(args.candidate, read_rows(args.results, args.candidate))
        return 0

    # Candidate validation is shared by every cell (done once).
    if not args.candidate_dir:
        print("--candidate-dir is required (path to the extender to inject)", file=sys.stderr)
        return 2
    # Only the resolver call itself is guarded — cleanup of the staged dir
    # must still cover the whole run, but FileNotFoundError/ValueError raised
    # *inside* the run (e.g. from grading, case loading) must propagate rather
    # than be misreported as a candidate-arg error.
    stack = contextlib.ExitStack()
    try:
        candidate_dir = stack.enter_context(resolved_candidate_dir(args.candidate_dir))
    except FileNotFoundError:
        print(f"no such candidate path: {args.candidate_dir}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    with stack:
        kind = detect_kind(candidate_dir)
        if kind is None:
            print(
                f"{args.candidate_dir}: not recognizable as skill / agent / plugin",
                file=sys.stderr,
            )
            return 2

        single = len(cells) == 1
        ran_any = False
        smoke_all_ok = True
        for harness, model in cells:
            adapter = adapters[harness]
            pf = adapter.preflight()
            if pf != "ok":
                reason = (
                    "not on PATH — install it or run in the devcontainer"
                    if pf == "missing"
                    else "not authenticated — configure credentials"
                )
                print(f"{adapter.name} CLI {reason}", file=sys.stderr)
                # One cell: preserve the exit-1 contract. Grid: skip this
                # harness, let the reachable cells still run (no silent
                # whole-run abort).
                if single:
                    return 1
                continue
            args.model = model
            if args.smoke:
                ok = smoke(adapter, args.candidate, kind, candidate_dir, args)
                ran_any = True
                smoke_all_ok = smoke_all_ok and ok
                if single:
                    return 0 if ok else 1
            else:
                run_candidate(adapter, args.candidate, kind, candidate_dir, args)
                ran_any = True

        if args.smoke:
            return 0 if (ran_any and smoke_all_ok) else 1
        return 0 if ran_any else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
