# Agent Harness — design + build plan

_A reusable extender-evaluation harness: drive Claude Code or opencode headlessly against a
fixture workspace with a candidate extender injected, grade the outcome, append one ledger row._

Status: active — signed off by Henry 2026-07-21; decisions resolved in §8.
Sources: recon of fleet-dashboard, dotfiles-agents-workbench, mcp-agent-bus (2026-07-21 session)
verifying `~/Documents/CODING-AGENT-META-HARNESSES.md`.

## 1 · Goals and non-goals

**Goals**

- One call shape: `run(harness, model, candidate, case, config)` → one appended JSONL row.
  Harness ∈ {claude, opencode} (owner decision 2026-07-21). Config ∈ {with, baseline}.
- **Cross-harness evaluation**: the same candidate + case run under both CLIs. Same model,
  different harness isolates the harness effect (e.g. Claude Sonnet via `claude` vs via
  opencode's `anthropic/` provider).
- **Cross-model evaluation**: `claude --model X` and `opencode -m provider/model` make model a
  first-class run dimension; opencode's multi-provider support extends this beyond Anthropic.
- Battle-tested **in this repo first** — real eval cases for marketplace primitives — then
  extracted to its own repo (app or package, shape decided after battle-testing).

**Non-goals (v1)**

- codex / copilot adapters. The recon captured their invocation patterns and quirks (codex:
  success must be judged by non-empty `--output-last-message`, exit code lies; copilot:
  `--allow-all-tools` + empty-stdout check) — recorded here for a later adapter, not built now.
- Docker sandboxing (Harbor territory; revisit at extraction time).
- PocketBase / extender-db ingestion — but the ledger schema is kept stable so `evals/`
  eval_runs can ingest rows later (§6).
- Running evals in CI. Evals need API keys + live CLIs; CI runs only the harness's unit tests.

## 2 · Prior art — what is scavenged, what is new

| Source | Take | Status |
|---|---|---|
| workbench `scripts/run_eval.py` | The chassis: temp-workspace lifecycle, per-kind injection, two-tier grading, JSONL ledger + resume key, 29 unit tests | Port with an adapter seam |
| fleet-dashboard `harness/harness.mjs` | Dispatcher discipline: name→argv table, no-shell argv, stdin always closed, per-vendor env scrub (`CLAUDECODE`) | Pattern, re-expressed in Python |
| mcp-agent-bus `apps/job-market/adapters/CONTRACT.md` | Adapter interface shape: preflight → `ok|missing|noauth`, setup, run → status token; isolated HOME per run | Formalized as the Python adapter API |
| mcp-agent-bus bake-off memory | opencode invocation + traits (exit 0/1, clean HOME isolation, `--format json`) | Basis of the opencode adapter |

**Why build rather than adopt** (Harbor / promptfoo / agent-catalog-eval, from the VENDORED
survey): none can inject a *Claude Code extender* (`--plugin-dir` / synthetic skill wrapper /
`--agents`), which is the entire point; Harbor is Docker-heavy with a dataset format to learn;
promptfoo has no CC-CLI adapter; agent-catalog-eval is early-stage with only opencode wired.
**Charter note:** extender-db's CHARTER records "harness is REUSED, never built" (EDB-14/19).
This build is ~80 % reuse of our own workbench chassis plus the multi-harness seam nothing
external offers — Henry reconciles the charter wording at promotion time.

New in this build (gaps the recon exposed): **timeouts** (fleet-dashboard has none — a hung CLI
hangs the pipeline), **structured per-run logs** (raw stdout append was the prior art's only
logging), the **harness and model dimensions** in the ledger key, and the **opencode injection
path** (nothing prior injects extenders into opencode).

## 3 · Architecture

Three layers, one self-contained directory (`harness/`, §5), Python 3 as a uv project
(`harness/pyproject.toml` from day one) — dependencies allowed (owner decision: no stdlib
restriction; use deps where they pay, keep stdlib where natural).

**Adapter layer** — one module per vendor implementing:

```
name                                          # "claude" | "opencode"
preflight() -> "ok" | "missing" | "noauth"    # CLI on PATH + auth probe; from CONTRACT.md
inject(kind, candidate_dir, tmpdir)
    -> Injection(flags, files, supported)     # supported=False => explicit skip row, never silent
invocation(prompt, workspace, model, injection) -> (argv, env)
parse_log(raw) -> NormalizedRecord            # vendor log -> vendor-neutral record
success(returncode, record) -> bool
```

- **ClaudeAdapter** — from the workbench, near-verbatim: `claude -p <prompt> --bare
  --output-format stream-json --verbose --permission-mode acceptEdits [--model M]` + injection
  flags. Injection by kind: plugin → `--plugin-dir`; skill → synthetic-plugin wrapper
  (workbench `synth_plugin()`); agent → `--agents` JSON built from frontmatter.
  Env scrub: `del env["CLAUDECODE"]` (nested-claude detection).
- **OpencodeAdapter** — from mcp-agent-bus: `opencode run --dir <ws> -m <provider/model>
  --format json --dangerously-skip-permissions <prompt>`, isolated throwaway HOME per run
  (proven trait: clean isolation, honest exit 0/1). Injection rides opencode's **plugin
  capability, very similar to Claude Code's** (owner confirmation 2026-07-21 — no portability
  concern); the Wave-2 opening scout confirms only the exact mechanics (flags/paths per kind).
  **Any agent needing opencode knowledge loads the `opencode-expertise` skill from this very
  marketplace.** Kinds opencode genuinely can't host still produce explicit `supported=False`
  skip rows.

**Run core** — vendor-agnostic: `mktemp` workspace ← fixture copy ← `subprocess.run(argv,
timeout=T, stdin=DEVNULL, env=scrubbed)` (list-form argv, never shell) ← raw output captured to
a per-run log file ← adapter's `parse_log` → NormalizedRecord (`result`, `tool_names`,
`plugin_errors`, `skill_used`, `exit_code`, `cost_usd`, `duration_ms`, `num_turns`, `error`) ←
cleanup unless failed or `--keep-workspaces`.

**Eval + ledger layer** — unchanged workbench conventions:

- Case = data, not code: `cases/<candidate>/<case-id>/{case.json, fixture/, check.py}`.
  `case.json` = `{prompt, assertions:[{id, text}]}`. `check.py` = deterministic stdlib script
  run in the final workspace, printing `[{id, passed, evidence}]`.
- Grading tier 1: `check.py`. Tier 2: LLM rubric grader — **always the claude CLI with the
  pinned grader model** (`claude-haiku-4-5-20251001`), read-only tools (`Read,Grep,Glob`),
  JSON-schema output, evidence-required, "no benefit of the doubt". The grader is held constant
  across every cell — including opencode cells — because grades must be comparable across the
  grid; grader drift would confound harness/model deltas. (Consequence: the claude CLI is a
  dependency even for opencode-only runs. Accepted.)
- Pass rule (workbench): exit 0, no plugin errors in `with` config, all checks + grades pass.
- Ledger: `results.jsonl`, append-only, `json.dumps(sort_keys=True)`, one row per trial.
  **Resume key: `harness|model|candidate|case|config|trial`** (workbench key + the two new
  dimensions). Row schema = the workbench's 20 fields + `harness` (model already present).
- `baseline` config = identical run, injection flags omitted. Deltas computed **within a
  (harness, model) cell**; the cross-harness portability verdict compares `with`-config pass
  rates across cells.

## 4 · The evaluation grid

A run request expands to: `{claude, opencode} × models × {with, baseline} × trials` per
(candidate, case). Every cell yields a row — including explicit `skipped/unsupported` rows for
injection kinds a harness can't host. **No silent caps**: the report states which cells ran,
which were skipped and why.

Report aggregation (`--report`): per (candidate, case) — pass rate per cell, with-vs-baseline
delta per cell, pass@n / pass^n, cost and duration mean ± stdev, and a portability line
(candidate works under: claude ✓/✗, opencode ✓/✗/unsupported).

## 5 · Repo integration

- **Home: `harness/` at repo root** — a self-contained uv project (own `pyproject.toml` +
  `uv.lock`), zero imports from `scripts/` (extraction = move the directory). A
  no-repo-coupling grep gate enforces this from Wave 1.
- **Naming adjacency**: root `evals/` is the extender-db PocketBase project — a different
  system. `harness/` (the runner) vs `evals/` (the database). Harness ledger rows are exactly
  the provenance extender-db's `eval_runs` wants; ingestion is a deferred integration, enabled
  by keeping the row schema stable.
- Unit tests live in `harness/tests/`, run via uv (`make harness-test`). The repo's
  `make test`/`make ci` stay stdlib-only/zero-install (that invariant now scopes to the
  marketplace lanes, not `harness/`); a path-filtered `harness-test` CI lane lands at Wave 4.
  Eval-run make targets:
  `harness-eval ITEM=<candidate> [HARNESS=] [MODEL=]`, `harness-report ITEM=<candidate>`
  (mirroring the workbench targets; NOT part of `ci`).
- **Ledger tracked in git** (recommendation, §8-D3): it is the battle-test evidence and the
  future eval_runs feedstock; append-only JSONL diffs cleanly.
- **Branch discipline**: build on `feat/agent-harness` off `dev`, PR into `dev`. Never on
  `feat/extender-db` (separate lane, its promotion is pending) and never `main`.

## 6 · Build plan — deliverables · criteria · parallelism (no timelines)

**Wave 0 — sign-off (gate: Henry).** The §8 decisions. Nothing is built before this.

**Wave 1 — chassis + claude adapter (serial; one builder, opus-tier — coupled port).**
Deliverables: `harness/` core (run loop, adapter API, ledger, case loader, report), claude
adapter, timeouts, structured per-run logs, ported + extended unit tests, make targets.
Criteria: `make ci` green and `make harness-test` green; template-case smoke run appends a
schema-valid row with `harness=claude`; resume skips the completed key on re-run; kill-test
proves the timeout.

**Wave 2 — opencode adapter (scout, then builder).**
Opening scout confirms opencode's injection mechanics per kind (source: the
`opencode-expertise` skill in this repo, then opencode docs). Deliverables: OpencodeAdapter (preflight, throwaway-HOME
isolation, `-m provider/model` mapping, injection or explicit-unsupported per kind).
Criteria: the same template case produces rows in ≥2 opencode model cells and ≥1 claude cell
from one command; unsupported kinds appear as skip rows; a same-model cross-harness pair
(sonnet via both CLIs) runs end-to-end.

**Wave 3 — battle-test on this marketplace (parallel with Wave 2 after Wave 1).**
Case authoring is harness-agnostic data → parallel builders, one per candidate. Deliverables:
real cases for 2–3 roster primitives (at least one skill + one agent), full-grid runs
(`with`/`baseline` × 3 trials), committed ledger + report, findings filed as issues.
Criteria: every case has ≥1 deterministic check; baseline plausibly fails by design; deltas
reported per cell; a reviewer agent adversarially re-derives one full case's grading from the
raw logs before results are cited anywhere.

**Wave 4 — hardening + reuse readiness (serial reconciliation).**
Deliverables: operator README (per readme guidelines), extraction checklist (what migration to
its own repo needs: CLI entry, cases-dir flag), coupling grep gate wired into `make ci`,
the path-filtered `harness-test` CI lane, drift/cleanup punch list from Waves 1–3 handoffs.
Criteria: `make ci` green including the coupling gate; README complete; a cold-start smoke
(fresh clone, `make harness-eval` on the template) documented as run with output.

**Hard gates (run by the foreman, not asserted by crews):** `make ci`; one live end-to-end
grid run on a real candidate producing committed rows; the Wave-3 adversarial grading review.

## 7 · Data shapes (reference)

```jsonc
// case.json
{ "prompt": "…", "assertions": [{ "id": "a1", "text": "binary, evidence-checkable" }] }

// results.jsonl row (workbench 20 fields + harness)
{ "ts", "harness", "model", "candidate", "case", "config", "trial", "kind",
  "grader_model", "passed", "checks": [{id,passed,evidence}], "grades": [{id,passed,evidence}],
  "skill_used", "tool_names", "plugin_errors", "exit_code", "error",
  "cost_usd", "duration_ms", "num_turns", "workspace", "cli_version" }
```

## 8 · Decisions — resolved (owner sign-off, 2026-07-21)

- **D1 · Language:** Python 3, **dependencies allowed** (owner: "no stdlib restrictions").
  `harness/` is a uv project; the repo's stdlib-only zero-install invariant continues to
  apply to `make ci` and `tests/`, not to `harness/`.
- **D2 · Home:** root `harness/` — accepted as recommended (`evals/` adjacency acknowledged).
- **D3 · Ledger tracked:** yes — accepted as recommended.
- **D4 · Grader constancy:** claude + pinned Haiku in all cells — accepted as recommended.
- **D5 · opencode injection:** resolved — opencode's plugin capability is very similar to
  Claude Code's (owner), so no portability concern; the Wave-2 scout confirms mechanics only.
  Agents needing opencode knowledge load the `opencode-expertise` skill from this repo.
