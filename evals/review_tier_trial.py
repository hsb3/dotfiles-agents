#!/usr/bin/env python3
"""Prepare and run the bounded native Codex review-tier trial."""
import argparse
import json
from pathlib import Path
import subprocess
import time


MODELS = ("gpt-5.6-terra", "gpt-6-astra")
CASES = ("usage", "roles")
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")


def parse_usage(events):
    """Native turn.completed usage values are per-turn increments, never snapshots."""
    totals = {key: None for key in USAGE_KEYS}
    for event in events:
        usage = event.get("usage") if isinstance(event, dict) and event.get("type") == "turn.completed" else None
        if not isinstance(usage, dict):
            continue
        for key in USAGE_KEYS:
            value = usage.get(key)
            if isinstance(value, int) and value >= 0:
                totals[key] = (totals[key] or 0) + value
    return totals


def parse_findings(text):
    try:
        body = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        return [], f"parse failure: {exc}"
    findings = body.get("findings") if isinstance(body, dict) else None
    if not isinstance(findings, list):
        return [], "parse failure: JSON object requires findings list"
    clean = []
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("explanation"), str):
            return [], "parse failure: each finding requires explanation"
        if not isinstance(finding.get("id"), str) and not isinstance(finding.get("location"), str):
            return [], "parse failure: each finding requires id or location"
        clean.append({key: finding[key] for key in ("id", "location", "explanation") if key in finding})
    return clean, None


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def prepare(output_dir):
    output_dir = Path(output_dir)
    cases = output_dir / "cases"
    _write(cases / "usage" / "usage.py", '''def total_usage(snapshots):
    total = 0
    for snapshot in snapshots:
        total += snapshot["input_tokens"]
    return total

def uncached_input(snapshot):
    return snapshot["input_tokens"] - snapshot["cached_input_tokens"]
''')
    _write(cases / "usage" / "CONTRACT.md", """Review this code. Usage snapshots are cumulative: sum deltas, so duplicate snapshots add zero and a lower value starts a new counter. For [100, 100, 130, 12], expected input usage is 142. Cached input is a subset of input; uncached input is input minus cached, so 100 and 30 yields 70. Report only real defects.\n""")
    _write(cases / "roles" / "roles.py", '''from pathlib import Path

def resolve_role(global_role, local_role):
    return global_role or local_role

def write_managed(path, content, expected_checksum):
    Path(path).write_text(content)
''')
    _write(cases / "roles" / "CONTRACT.md", """Review this code. A local role overrides a global role. A managed file with content different from its expected checksum must be refused, never overwritten; a missing file may be created. Report only real defects.\n""")
    prompt = """Review only the files in this directory against CONTRACT.md. Return exactly one JSON object: {\"findings\":[{\"location\":\"file.py:line\",\"explanation\":\"concise defect\"}]}. Do not include markdown, prose outside JSON, or speculative findings.\n"""
    for case in CASES:
        _write(cases / case / "PROMPT.txt", prompt)
    oracle = {"usage": {"findings": [{"id": "cumulative-sum", "explanation": "total_usage adds cumulative snapshots instead of deltas, so 100,100,130,12 returns 342 rather than 142."}], "controls": ["uncached_input(100, 30) returns 70"]},
              "roles": {"findings": [{"id": "local-precedence", "explanation": "resolve_role returns the global role when a local role must override it."}, {"id": "checksum-refusal", "explanation": "write_managed overwrites changed managed content instead of refusing it."}], "controls": ["write_managed creates a missing file"]}}
    _write(output_dir / "oracle.json", json.dumps(oracle, indent=2) + "\n")


def _json_lines(text):
    for line in text.splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _text(value):
    return value.decode(errors="replace") if isinstance(value, bytes) else value or ""


def _thread_started_id(event):
    if not isinstance(event, dict) or event.get("type") != "thread.started":
        return None
    payload = event.get("payload", event)
    if isinstance(payload, dict):
        return payload.get("thread_id") or payload.get("id")
    return None


def rollout_metadata(thread_id):
    if not thread_id:
        return {"status": "unverified", "reason": "no thread.started id"}
    paths = Path.home().glob(f".codex/sessions/**/rollout-*{thread_id}*.jsonl")
    for path in paths:
        try:
            for event in _json_lines(path.read_text()):
                if event.get("type") == "turn_context" and isinstance(event.get("payload"), dict):
                    payload = event["payload"]
                    model, effort = payload.get("model"), payload.get("effort")
                    if isinstance(model, str) and model and isinstance(effort, str) and effort:
                        return {"status": "verified", "model": model, "effort": effort, "path": str(path)}
                    return {"status": "unverified", "reason": "matching rollout lacks model or effort", "path": str(path)}
        except OSError:
            continue
    return {"status": "unverified", "reason": "matching rollout metadata unavailable"}


def run_case(case, model, output_dir, runner=subprocess.run):
    output_dir, case_dir = Path(output_dir), Path(output_dir) / "cases" / case
    if case not in CASES or model not in MODELS or not case_dir.is_dir():
        raise ValueError("unknown case/model or unprepared output directory")
    run_dir = output_dir / "runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case}-{model}"
    last_message = run_dir / f"{stem}.last-message.txt"
    artifacts = [run_dir / f"{stem}.{suffix}" for suffix in ("stdout", "stderr", "json")]
    if any(path.exists() for path in artifacts):
        raise FileExistsError(f"refusing existing run artifacts for {stem}")
    last_message.unlink(missing_ok=True)
    command = ["codex", "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check",
               "--cd", str(case_dir), "--model", model, "-c", "model_reasoning_effort=medium",
               "--output-last-message", str(last_message), (case_dir / "PROMPT.txt").read_text()]
    started = time.monotonic()
    try:
        completed = runner(command, capture_output=True, text=True, timeout=300)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        completed, timed_out = exc, True
    elapsed = time.monotonic() - started
    stdout, stderr = _text(completed.stdout), _text(completed.stderr)
    _write(run_dir / f"{stem}.stdout", stdout)
    _write(run_dir / f"{stem}.stderr", stderr)
    message = last_message.read_text() if last_message.exists() else ""
    findings, parse_error = parse_findings(message)
    events = list(_json_lines(stdout))
    report = {"case": case, "model": model, "effort": "medium", "command": command,
              "elapsed_seconds": elapsed, "exit_code": getattr(completed, "returncode", None),
              "timed_out": timed_out, "stdout_path": str(run_dir / f"{stem}.stdout"),
              "stderr_path": str(run_dir / f"{stem}.stderr"), "findings": findings,
              "parse_error": parse_error, "usage": parse_usage(events),
              "rollout": rollout_metadata(next((value for event in events if (value := _thread_started_id(event))), None)),
              "limitations": ["Findings are ungraded; compare them semantically against the external oracle.", "Usage is available only from native turn.completed event.usage."]}
    _write(run_dir / f"{stem}.json", json.dumps(report, indent=2) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--output-dir", required=True, type=Path)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--case", required=True, choices=CASES)
    run_parser.add_argument("--model", required=True, choices=MODELS)
    run_parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.action == "prepare":
        prepare(args.output_dir)
    else:
        print(json.dumps(run_case(args.case, args.model, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
