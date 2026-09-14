"""Two-tier grading + the pass rule.

Tier 1 — deterministic ``check.py`` run in the final workspace.
Tier 2 — an LLM rubric grader. Per DESIGN §3/D4 the grader is **always the
claude CLI with a pinned Haiku model**, held constant across every harness/model
cell so grades stay comparable (grader drift would confound the deltas). This is
a deliberate, documented dependency on the claude CLI even for opencode-only runs.

The pass rule routes exit-code semantics through the adapter's ``success()`` and
keeps the workbench's clean-load + all-grades-pass logic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

GRADER_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "grades": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "passed": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["id", "passed", "evidence"],
                },
            }
        },
        "required": ["grades"],
    }
)

GRADER_PROMPT = (
    "You are an impartial grader for a coding-agent trial. Judge each assertion "
    "against the trial workspace (your current directory) and the agent's final "
    "response below. You may Read/Grep/Glob files. Be strict: an assertion "
    "passes only with concrete evidence you can cite (file path + line, or a "
    "quoted excerpt). If you cannot determine an assertion, mark it failed with "
    "evidence starting 'unknown:'. Do not give benefit of the doubt.\n\n"
    "Workspace files:\n{digest}\n\n"
    "Agent's final response (truncated):\n{result}\n\n"
    "Assertions (JSON):\n{assertions}\n\n"
    "Return JSON matching the schema: every assertion id exactly once."
)


def workspace_digest(workspace, cap=80):
    """Relative path + size listing of the trial workspace (grader context)."""
    entries = []
    for root, _dirs, files in os.walk(workspace):
        for f in sorted(files):
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, workspace)
            try:
                entries.append(f"{rel} ({os.path.getsize(fp)}B)")
            except OSError:
                entries.append(f"{rel} (unreadable)")
    listed = entries[:cap]
    if len(entries) > cap:
        listed.append(f"... and {len(entries) - cap} more")
    return "\n".join(listed) or "(empty)"


def run_check(case_dir, workspace):
    """Run a case's optional check.py in the workspace; return grade dicts."""
    check = os.path.join(case_dir, "check.py")
    if not os.path.isfile(check):
        return []
    try:
        proc = subprocess.run(
            [sys.executable, check],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120,
        )
        grades = json.loads(proc.stdout)
        if isinstance(grades, list):
            return grades
        raise ValueError("check.py output is not a JSON list")
    except Exception as exc:  # noqa: BLE001 — any check failure is a failed grade
        return [{"id": "check.py", "passed": False, "evidence": f"check-error: {exc}"}]


def run_grader(assertions, workspace, result_text, model, timeout):
    """Grade LLM-rubric assertions with a fresh-context claude grader run."""
    prompt = GRADER_PROMPT.format(
        digest=workspace_digest(workspace),
        result=(result_text or "")[:3000],
        assertions=json.dumps(assertions),
    )
    cmd = [
        "claude",
        "-p",
        prompt,
        "--bare",
        "--model",
        model,
        "--output-format",
        "json",
        "--json-schema",
        GRADER_SCHEMA,
        "--allowedTools",
        "Read,Grep,Glob",
    ]
    fail = [
        {"id": a["id"], "passed": False, "evidence": "grader-error"} for a in assertions
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout
        )
        payload = json.loads(proc.stdout)
        grades = (payload.get("structured_output") or {}).get("grades")
        return grades if isinstance(grades, list) else fail
    except Exception:  # noqa: BLE001 — grader problems must not crash the run
        return fail


def trial_passed(adapter, returncode, record, checks, grades, config):
    """The pass rule: clean CLI run, clean load (with-config), all grades pass.

    Exit-code semantics are delegated to the adapter (``success``) so honest vs
    lying exit codes are handled per vendor; everything else is vendor-neutral.
    """
    if not adapter.success(returncode, record):
        return False
    if config == "with" and record.plugin_errors:
        return False
    graded = list(checks) + list(grades)
    if not graded:
        return True
    return all(bool(g.get("passed")) for g in graded)
