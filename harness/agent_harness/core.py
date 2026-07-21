"""Run core — vendor-agnostic.

Owns the per-trial lifecycle: mktemp workspace ← fixture copy ← list-form
``subprocess.run`` (never shell, stdin closed) with a **timeout** (new vs the
prior art) ← raw stdout captured to a per-run log under ``runs/`` ← the adapter's
``parse_log`` ← grading ← one ledger row ← cleanup unless the trial failed or
``--keep-workspaces``.

Everything vendor-specific (argv, env scrub, injection, log format, exit-code
meaning) is delegated to the adapter; this module never names a vendor.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

from .adapters.base import Injection, NormalizedRecord
from .cases import load_cases
from .grading import run_check, run_grader, trial_passed
from .ledger import append_row, load_done, read_rows, row_key
from .report import print_report

# harness/agent_harness/core.py -> parents[1] == harness/
HARNESS_HOME = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CASES_DIR = str(HARNESS_HOME / "cases")
DEFAULT_RESULTS = str(HARNESS_HOME / "results.jsonl")
DEFAULT_RUNS_DIR = str(HARNESS_HOME / "runs")

DEFAULT_TRIALS = 3
DEFAULT_TIMEOUT = 600  # seconds; a hung CLI must not hang the pipeline (DESIGN §2)
CONFIGS = ("with", "baseline")
SMOKE_PROMPT = "Reply with exactly: OK"

ROW_FIELDS = (
    "ts", "harness", "model", "candidate", "case", "config", "trial", "kind",
    "grader_model", "passed", "checks", "grades", "skill_used", "tool_names",
    "plugin_errors", "exit_code", "error", "cost_usd", "duration_ms", "num_turns",
    "workspace", "cli_version",
)


@dataclass
class ProcResult:
    returncode: int
    raw: str
    timed_out: bool
    error: Optional[str]


def _coerce_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _run_subprocess(argv, cwd, env, timeout, log_path) -> ProcResult:
    """Run `argv` list-form (never shell), stdin closed, with a hard timeout.

    Captures stdout to `log_path` and returns a ProcResult. A timeout produces
    ``returncode=-1`` + an ``error`` string (a row, never a crash — DESIGN §3).
    """
    stderr = ""
    error = None
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
        stdout, stderr, returncode, timed_out = (
            proc.stdout or "",
            proc.stderr or "",
            proc.returncode,
            False,
        )
    except FileNotFoundError:
        stdout, returncode, timed_out = "", -1, False
        error = f"executable not found: {argv[0]}"
    except subprocess.TimeoutExpired as exc:
        stdout = _coerce_text(exc.stdout)
        stderr = _coerce_text(exc.stderr)
        returncode, timed_out = -1, True
        error = f"timeout after {timeout}s"
    if log_path:
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as fh:
                fh.write(stdout)
        except OSError:
            pass
    if error is None and returncode != 0:
        error = (stderr or "")[-2000:] or f"exit {returncode}"
    return ProcResult(returncode, stdout, timed_out, error)


def _log_path(runs_dir, *parts):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = "-".join(str(p) for p in parts)
    return os.path.join(runs_dir, f"{safe}-{stamp}.log")


def _build_row(
    *, ts, harness, model, candidate, case_id, config, trial, kind, grader_model,
    passed, checks, grades, record: NormalizedRecord, error, workspace,
):
    """Assemble the full DESIGN §7 row schema (cli_version filled by caller)."""
    return {
        "ts": ts,
        "harness": harness,
        "model": model,
        "candidate": candidate,
        "case": case_id,
        "config": config,
        "trial": trial,
        "kind": kind,
        "grader_model": grader_model,
        "passed": passed,
        "checks": checks,
        "grades": grades,
        "skill_used": record.skill_used,
        "tool_names": record.tool_names,
        "plugin_errors": record.plugin_errors,
        "exit_code": record.exit_code,
        "error": error,
        "cost_usd": record.cost_usd,
        "duration_ms": record.duration_ms,
        "num_turns": record.num_turns,
        "workspace": workspace,
        "cli_version": None,
    }


def run_trial(adapter, candidate, kind, candidate_dir, case, config, trial, args):
    """One trial: fresh workspace, fixture, headless run, grading, one row."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    model = args.model or "default"
    tmp = tempfile.mkdtemp(
        prefix=f"harness-{adapter.name}-{candidate}-{case['id']}-{config}-{trial}-"
    )
    ws = os.path.join(tmp, "ws")
    fixture = os.path.join(case["dir"], "fixture")
    if os.path.isdir(fixture):
        shutil.copytree(fixture, ws)
    else:
        os.makedirs(ws)

    if config == "with":
        injection = adapter.inject(kind, candidate_dir, tmp)
    else:
        injection = Injection([], [], True)  # baseline = injection omitted

    # supported=False => explicit skip row, never a silent no-op (DESIGN §3).
    if not injection.supported:
        shutil.rmtree(tmp, ignore_errors=True)
        return _build_row(
            ts=ts, harness=adapter.name, model=model, candidate=candidate,
            case_id=case["id"], config=config, trial=trial, kind=kind,
            grader_model=None, passed=None, checks=[], grades=[],
            record=NormalizedRecord(),
            error=f"unsupported: {adapter.name} cannot host kind={kind}",
            workspace=None,
        )

    argv, env = adapter.invocation(case["prompt"], ws, args.model, injection)
    log_path = _log_path(
        args.runs_dir, adapter.name, candidate, case["id"], config, trial
    )
    proc = _run_subprocess(argv, ws, env, args.timeout, log_path)
    record = adapter.parse_log(proc.raw)
    record.exit_code = proc.returncode
    record.error = proc.error

    checks = run_check(case["dir"], ws)
    assertions = case.get("assertions", [])
    grades = (
        run_grader(assertions, ws, record.result, args.grader_model, args.timeout)
        if assertions
        else []
    )
    passed = trial_passed(adapter, proc.returncode, record, checks, grades, config)

    # Failures keep their workspace for inspection; passing trials clean up
    # unless --keep-workspaces.
    keep = args.keep_workspaces or not passed
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)

    return _build_row(
        ts=ts, harness=adapter.name, model=model, candidate=candidate,
        case_id=case["id"], config=config, trial=trial, kind=kind,
        grader_model=args.grader_model if assertions else None,
        passed=passed, checks=checks, grades=grades, record=record,
        error=record.error, workspace=(ws if keep else None),
    )


def run_candidate(adapter, candidate, kind, candidate_dir, args):
    """Full behavioral run: cases × configs × trials, resumable."""
    cases = load_cases(candidate, args.cases_dir, only=args.case)
    done = load_done(args.results)
    version = adapter.cli_version()
    model = args.model or "default"
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    ran = skipped = 0
    for case in cases:
        for config in configs:
            for trial in range(args.trials):
                stub = {
                    "harness": adapter.name,
                    "model": model,
                    "candidate": candidate,
                    "case": case["id"],
                    "config": config,
                    "trial": trial,
                }
                if row_key(stub) in done:
                    skipped += 1
                    continue
                row = run_trial(
                    adapter, candidate, kind, candidate_dir, case, config, trial, args
                )
                row["cli_version"] = version
                append_row(args.results, row)
                ran += 1
                if row["passed"] is None:
                    mark = "∅"
                elif row["passed"]:
                    mark = "✓"
                else:
                    mark = "✗"
                print(f"{mark} {adapter.name} {case['id']} {config} trial {trial}")
    print(f"\n{ran} trial(s) run, {skipped} skipped (already in {args.results})")
    print_report(candidate, read_rows(args.results, candidate))


def smoke(adapter, candidate, kind, candidate_dir, args):
    """Loadability check: inject the candidate, fail on plugin_errors."""
    with tempfile.TemporaryDirectory(prefix=f"harness-smoke-{candidate}-") as tmp:
        ws = os.path.join(tmp, "ws")
        os.makedirs(ws)
        injection = adapter.inject(kind, candidate_dir, tmp)
        if not injection.supported:
            print(f"kind: {kind}\n∅ {adapter.name} cannot host kind={kind} — skip")
            return False
        argv, env = adapter.invocation(SMOKE_PROMPT, ws, args.model, injection)
        log_path = _log_path(args.runs_dir, adapter.name, "smoke", candidate)
        proc = _run_subprocess(argv, ws, env, args.timeout, log_path)
        record = adapter.parse_log(proc.raw)
    loaded = ", ".join(p.get("name", "?") for p in record.plugins) or "(none)"
    print(f"harness: {adapter.name}\nkind: {kind}\nplugins loaded: {loaded}")
    ok = proc.returncode == 0 and not record.plugin_errors
    for err in record.plugin_errors:
        print(f"✗ plugin_error: {err}")
    if proc.returncode != 0:
        print(f"✗ exit {proc.returncode}: {(proc.error or '')[:400]}")
    print("✓ loadability OK" if ok else "✗ loadability FAILED")
    return ok
