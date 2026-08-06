"""Environment preconditions — what a reviewer needs to trust a trial row.

Cases can be environment-contingent (e.g. a candidate self-installs Playwright at
runtime — a blocked npm would collapse the pass path, and the pass would say
nothing about the candidate). `env_preconditions` records the observable
environment facts a run depended on (harness identity, CLI version, model,
timeout, campaign, and the NAMES ONLY of provider auth env vars present — never
values, so a secret can never reach the ledger). `detect_self_installs` scans a
trial's raw log for install-command signatures the agent ran at trial time, so a
reviewer reading a passing row can see the run was not hermetic.

Consumed by `agent_harness.core` (per-trial row + per-trial log header) and
rendered as the one-line console note in `run_candidate`.
"""

from __future__ import annotations

import json
import os

# Provider auth env vars we look for. Only the NAME is ever recorded — the value
# never leaves os.environ.
AUTH_ENV_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY")

# Install-command signatures that indicate a runtime self-install (the motivating
# case: `npx playwright install` run by the agent mid-trial, so a pass depends on
# the machine's network/npm rather than on the candidate).
INSTALL_SIGNATURES = (
    "npm install",
    "npm i ",
    "npx playwright install",
    "playwright install",
    "pnpm add",
    "yarn add",
    "bun add",
    "pip install",
    "pip3 install",
    "uv add",
    "uv pip install",
    "brew install",
    "apt-get install",
    "cargo install",
    "go install",
)

_MAX_ENTRY_CHARS = 120
_MAX_ENTRIES = 20


def env_preconditions(adapter, args) -> dict:
    """The environment facts behind a run — stable keys, JSON-serializable.

    Never includes secret values: `auth_env_present` is the sorted list of
    `AUTH_ENV_VARS` NAMES that are set, never their contents.
    """
    campaign = getattr(args, "campaign", "") or ""
    auth_env_present = sorted(k for k in AUTH_ENV_VARS if os.environ.get(k))
    return {
        "harness": adapter.name,
        "cli_version": adapter.cli_version(),
        "model": args.model or "default",
        "grader_model": getattr(args, "grader_model", None),
        "timeout": getattr(args, "timeout", None),
        "campaign": campaign,
        "auth_env_present": auth_env_present,
        "network_assumption": "assumed-available",
    }


def detect_self_installs(raw_log) -> list[str]:
    """Scan `raw_log` text for install-command signatures run at trial time.

    Returns a deterministic (sorted), deduped list of the matching lines
    (stripped, truncated to ~120 chars each), capped at ~20 entries so a
    pathological log can't bloat a row.
    """
    if not raw_log:
        return []
    found = set()
    for line in raw_log.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(sig in stripped for sig in INSTALL_SIGNATURES):
            found.add(stripped[:_MAX_ENTRY_CHARS])
    return sorted(found)[:_MAX_ENTRIES]


def render_header(preconditions: dict) -> str:
    """One `#`-prefixed line for the per-trial log: adapters' `parse_log` skip
    non-JSON lines, so this must precede the raw transcript, never be mixed in."""
    return "# preconditions: " + json.dumps(preconditions, sort_keys=True)


def render_note(preconditions: dict) -> str:
    """One-line console rendering of `preconditions` (no self_installs — that's
    per-trial, not known at `run_candidate` time)."""
    parts = [
        f"harness={preconditions['harness']}",
        f"cli={preconditions['cli_version']}",
        f"campaign={preconditions['campaign'] or '(none)'}",
        f"model={preconditions['model']}",
        f"grader={preconditions['grader_model']}",
        f"timeout={preconditions['timeout']}s",
        f"auth_env={','.join(preconditions['auth_env_present']) or '(none)'}",
        f"network={preconditions['network_assumption']}",
    ]
    return "preconditions: " + " · ".join(parts)
