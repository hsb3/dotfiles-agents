#!/usr/bin/env python3
"""Prepare and run the bounded native Codex review-tier trial."""
import argparse
import json
from pathlib import Path
import subprocess
import time


MODELS = ("gpt-5.6-terra", "gpt-6-astra")
CASES = ("usage", "roles")
TOKEN_KEYS = ("input_tokens", "output_tokens", "reasoning_tokens", "cached_input_tokens")


def aggregate_usage(snapshots):
    """Sum cumulative usage snapshots, treating a decrease as a fresh counter."""
    rows = [row for row in snapshots if isinstance(row, dict) and any(k in row for k in TOKEN_KEYS)]
    if not rows:
        return None
    totals, previous, seen = {}, {}, False
    for row in rows:
        input_tokens, cached = row.get("input_tokens"), row.get("cached_input_tokens")
        if isinstance(input_tokens, int) and isinstance(cached, int) and cached > input_tokens:
            return None
        for key in TOKEN_KEYS:
            value = row.get(key)
            if value is None:
                continue
            if not isinstance(value, int) or value < 0:
                return None
            totals[key] = totals.get(key, 0) + (value - previous[key] if key in previous and value >= previous[key] else value)
            previous[key], seen = value, True
    return totals if seen else None


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


def grade_findings(case, findings, oracle):
    expected = oracle[case]
    found = set()
    false_positive = 0
    for finding in findings:
        matches = [index for index, item in enumerate(expected)
                   if finding.get("id") == item.get("id") or finding.get("location") == item.get("location")]
        if matches:
            found.update(matches)
        else:
            false_positive += 1
    return {"found": len(found), "missed": len(expected) - len(found), "false_positive": false_positive}


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
''')
    _write(cases / "usage" / "CONTRACT.md", """Review this code. Usage snapshots are cumulative: sum deltas, so duplicate snapshots add zero and a lower value starts a new counter. For [100, 100, 130, 12], expected input usage is 142. Cached input is a subset of input, never an additional token category. Report only real defects.\n""")
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
    oracle = {"usage": [{"id": "cumulative-sum", "location": "usage.py:4"}],
              "roles": [{"id": "local-precedence", "location": "roles.py:4"},
                        {"id": "checksum-refusal", "location": "roles.py:7"}]}
    _write(output_dir / "oracle.json", json.dumps(oracle, indent=2) + "\n")


def _json_lines(text):
    for line in text.splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _usage_rows(value):
    if isinstance(value, dict):
        if any(key in value for key in TOKEN_KEYS):
            yield value
        for child in value.values():
            yield from _usage_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from _usage_rows(child)


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
                    return {"status": "verified", "model": payload.get("model"), "effort": payload.get("effort")}
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
    stdout, stderr = completed.stdout or "", completed.stderr or ""
    _write(run_dir / f"{stem}.stdout", stdout)
    _write(run_dir / f"{stem}.stderr", stderr)
    message = last_message.read_text() if last_message.exists() else ""
    findings, parse_error = parse_findings(message)
    oracle = json.loads((output_dir / "oracle.json").read_text())
    events = list(_json_lines(stdout))
    report = {"case": case, "model": model, "effort": "medium", "command": command,
              "elapsed_seconds": elapsed, "exit_code": getattr(completed, "returncode", None),
              "timed_out": timed_out, "stdout_path": str(run_dir / f"{stem}.stdout"),
              "stderr_path": str(run_dir / f"{stem}.stderr"), "findings": findings,
              "parse_error": parse_error, "usage": aggregate_usage([row for event in events for row in _usage_rows(event)]),
              "rollout": rollout_metadata(next((value for event in events if (value := _thread_started_id(event))), None))}
    report["grade"] = grade_findings(case, findings, oracle) if not parse_error else {"found": 0, "missed": len(oracle[case]), "false_positive": 0}
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
