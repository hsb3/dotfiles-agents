# agent-harness

_Reusable extender-evaluation harness: drive Claude Code (and, from Wave 2, opencode)
headlessly against a fixture workspace with a candidate extender injected, grade the
outcome, append one ledger row._

Status: active — Wave 1 (chassis + claude adapter). The full operator guide + extraction
checklist land in Wave 4; design of record is `../_meta/research/agent-harness/DESIGN.md`.

## What it is

A self-contained uv project (`harness/`) with three layers:

- **Adapters** (`agent_harness/adapters/`) — one module per vendor behind a fixed six-member
  API (`preflight`, `inject`, `invocation`, `parse_log`, `success`, `name`). `ClaudeAdapter`
  is wired; adding opencode is a new module + one registry line, no core change.
- **Run core** (`agent_harness/core.py`) — vendor-agnostic: mktemp workspace ← fixture copy ←
  list-form `subprocess.run` (never a shell, stdin closed, **hard timeout**) ← per-run log
  under `runs/` ← adapter `parse_log` ← grading ← one ledger row ← cleanup unless failed.
- **Eval + ledger** (`cases.py`, `grading.py`, `ledger.py`, `report.py`) — cases are data
  (`cases/<candidate>/<case-id>/{case.json, fixture/, check.py}`), two-tier grading
  (deterministic `check.py` + a pinned-Haiku claude rubric grader), append-only
  `results.jsonl` keyed `harness|model|candidate|case|config|trial`.

## Run it

```sh
# from the repo root — uv builds the project's venv on first use
uv run --project harness agent-harness <candidate> --candidate-dir <path/to/extender> \
    --harness claude [--model M] [--trials N] [--configs with,baseline]

uv run --project harness agent-harness <candidate> --report        # aggregate rows
uv run --project harness agent-harness <candidate> --candidate-dir <path> --smoke  # loadability
```

Make targets (repo root): `make harness-test`, `make harness-eval ITEM=<candidate> [HARNESS=] [MODEL=]`,
`make harness-report ITEM=<candidate>`. None are part of `make ci` — the harness is its own
project and evals need live CLIs + API keys.

## Invariants

- **No repo coupling**: nothing under `harness/` imports from or reads repo files outside
  `harness/`. Candidates and cases are passed as paths at runtime. (`tests/test_coupling.py`
  guards this; Wave 4 wires the grep gate into CI.)
- The **grader is always the claude CLI** with a pinned Haiku model, held constant across every
  harness/model cell so grades stay comparable (DESIGN §3/D4).
- `runs/` (per-run logs) and temp workspaces are gitignored; `results.jsonl` is tracked
  (battle-test evidence, DESIGN §8-D3).
