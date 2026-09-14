"""Run core — vendor-agnostic.

Owns the per-trial lifecycle: mktemp workspace ← fixture copy ← list-form
``subprocess.Popen`` (never shell, stdin closed) with a **timeout** (new vs the
prior art) ← raw stdout captured to a per-run log under ``runs/`` ← the adapter's
``parse_log`` ← grading ← one ledger row ← cleanup unless the trial failed or
``--keep-workspaces``.

Everything vendor-specific (argv, env scrub, injection, log format, exit-code
meaning) is delegated to the adapter; this module never names a vendor.
"""

from __future__ import annotations

import os
import pathlib
import signal
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from . import preconditions
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
    "ts", "campaign", "harness", "model", "candidate", "case", "config", "trial",
    "kind", "grader_model", "passed", "checks", "grades", "skill_used", "tool_names",
    "plugin_errors", "exit_code", "error", "cost_usd", "duration_ms", "num_turns",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens",
    "workspace", "log_path", "cli_version", "preconditions",
)


@dataclass
class ProcResult:
    returncode: int
    raw: str
    timed_out: bool
    error: Optional[str]
    preconditions: Optional[dict] = None


def _run_subprocess(argv, cwd, env, timeout, log_path, precondition_env=None) -> ProcResult:
    """Run `argv` list-form (never shell), stdin closed, with a hard timeout.

    Captures stdout to `log_path` and returns a ProcResult. A timeout produces
    ``returncode=-1`` + an ``error`` string (a row, never a crash — DESIGN §3).

    ``precondition_env`` (optional) is the env-fact dict from
    ``preconditions.env_preconditions`` *without* self-installs yet — this
    function detects self-installs from the captured stdout, merges them in, and
    (when a log is written) prepends the result as a single ``#``-prefixed
    comment line ahead of the raw transcript so both adapters' `parse_log`
    (which skip non-JSON lines) still fold the real events. The merged dict is
    returned via ``ProcResult.preconditions`` so the caller can put the exact
    same data in the ledger row (no drift between log header and row).
    """
    stderr = ""
    error = None
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=subprocess.DEVNULL,
            start_new_session=os.name == "posix",
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            returncode, timed_out = proc.returncode, False
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()
            stdout, stderr = proc.communicate()
            returncode, timed_out = -1, True
            error = f"timeout after {timeout}s"
    except FileNotFoundError:
        stdout, returncode, timed_out = "", -1, False
        error = f"executable not found: {argv[0]}"
    full_preconditions = None
    if precondition_env is not None:
        full_preconditions = dict(precondition_env)
        full_preconditions["self_installs"] = preconditions.detect_self_installs(stdout)
    if log_path:
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as fh:
                if full_preconditions is not None:
                    fh.write(preconditions.render_header(full_preconditions) + "\n")
                fh.write(stdout)
        except OSError:
            pass
    if error is None and returncode != 0:
        error = (stderr or "")[-2000:] or f"exit {returncode}"
    return ProcResult(returncode, stdout, timed_out, error, full_preconditions)


def _log_path(runs_dir, *parts):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = "-".join(str(p) for p in parts)
    return os.path.join(runs_dir, f"{safe}-{stamp}-{uuid.uuid4().hex}.log")


def _portable_log_path(log_path):
    """Row-friendly log path: relative to the invocation cwd (repo root in normal
    use, so rows link as ``harness/runs/…log``); absolute if the log lives outside
    the cwd tree. Never couples to a hardcoded repo path (DESIGN §5)."""
    if not log_path:
        return None
    try:
        rel = os.path.relpath(log_path)
    except ValueError:  # pragma: no cover - different drive (Windows only)
        return log_path
    return rel if not rel.startswith("..") else log_path


def _build_row(
    *, ts, campaign, harness, model, candidate, case_id, config, trial, kind,
    grader_model, passed, checks, grades, record: NormalizedRecord, error,
    workspace, log_path, preconditions: Optional[dict] = None,
):
    """Assemble the full DESIGN §7 row schema (cli_version filled by caller)."""
    return {
        "ts": ts,
        "campaign": campaign,
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
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "cache_read_tokens": record.cache_read_tokens,
        "cache_creation_tokens": record.cache_creation_tokens,
        "workspace": workspace,
        "log_path": _portable_log_path(log_path),
        "cli_version": None,
        "preconditions": preconditions,
    }


def run_trial(adapter, candidate, kind, candidate_dir, case, config, trial, args):
    """One trial: fresh workspace, fixture, headless run, grading, one row."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    model = args.model or "default"
    campaign = getattr(args, "campaign", "") or ""
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

    env_precond = preconditions.env_preconditions(adapter, args)

    # supported=False => explicit skip row, never a silent no-op (DESIGN §3).
    if not injection.supported:
        shutil.rmtree(tmp, ignore_errors=True)
        skip_precond = dict(env_precond, self_installs=[])
        return _build_row(
            ts=ts, campaign=campaign, harness=adapter.name, model=model,
            candidate=candidate, case_id=case["id"], config=config, trial=trial,
            kind=kind, grader_model=None, passed=None, checks=[], grades=[],
            record=NormalizedRecord(),
            error=f"unsupported: {adapter.name} cannot host kind={kind}",
            workspace=None, log_path=None, preconditions=skip_precond,
        )

    argv, env = adapter.invocation(case["prompt"], ws, args.model, injection)
    log_path = _log_path(
        args.runs_dir, adapter.name, candidate, case["id"], config, trial
    )
    proc = _run_subprocess(
        argv, ws, env, args.timeout, log_path, precondition_env=env_precond
    )
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
        ts=ts, campaign=campaign, harness=adapter.name, model=model,
        candidate=candidate, case_id=case["id"], config=config, trial=trial,
        kind=kind, grader_model=args.grader_model if assertions else None,
        passed=passed, checks=checks, grades=grades, record=record,
        error=record.error, workspace=(ws if keep else None), log_path=log_path,
        preconditions=proc.preconditions,
    )


def _preconditions_note(adapter, args):
    """One-line environment/preconditions header for the run log (#172).

    Cases can be environment-contingent (e.g. a candidate self-installs Playwright
    at runtime — a blocked npm would collapse the pass path). We can't fully
    control that yet, but we record the observable preconditions so a later reader
    knows what environment produced the rows. Renders from
    `preconditions.env_preconditions` so the console line and the data recorded
    per-trial (row + log header) can't drift apart (task-22 gap 2)."""
    return preconditions.render_note(preconditions.env_preconditions(adapter, args))


def run_candidate(adapter, candidate, kind, candidate_dir, args):
    """Full behavioral run: cases × configs × trials, resumable."""
    cases = load_cases(candidate, args.cases_dir, only=args.case)
    done = load_done(args.results)
    version = adapter.cli_version()
    model = args.model or "default"
    campaign = getattr(args, "campaign", "") or ""
    print(_preconditions_note(adapter, args))
    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    ran = skipped = 0
    for case in cases:
        for config in configs:
            for trial in range(args.trials):
                stub = {
                    "campaign": campaign,
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
