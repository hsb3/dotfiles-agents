# agent-harness

_Reusable extender-evaluation harness: drive Claude Code or opencode headlessly
against a fixture workspace with a candidate extender injected, grade the outcome,
append one ledger row._

Status: active — Wave 4 (hardening + reuse-readiness). Design of record:
`../_meta/research/agent-harness/DESIGN.md`.

## What it is

One call shape — `run(harness, model, candidate, case, config)` → one appended JSONL
row — over a grid of `{claude, opencode} × models × {with, baseline} × trials`. A
self-contained uv project (`harness/`) in three layers:

- **Adapters** (`agent_harness/adapters/`) — one module per vendor behind a fixed
  six-member API (`preflight`, `inject`, `invocation`, `parse_log`, `success`, `name`
  + `cli_version`). Adding a harness is a new module + one registry line; the core
  never changes.
- **Run core** (`agent_harness/core.py`) — vendor-agnostic: mktemp workspace ←
  fixture copy ← list-form `subprocess.run` (never a shell, stdin closed, **hard
  timeout**) ← per-run log under `runs/` ← adapter `parse_log` ← grading ← one ledger
  row ← cleanup unless the trial failed or `--keep-workspaces`.
- **Eval + ledger** (`cases.py`, `grading.py`, `ledger.py`, `report.py`) — cases are
  data; two-tier grading (deterministic `check.py` + a pinned-Haiku claude rubric
  grader); append-only `results.jsonl`.

## Quickstart

```sh
# 1. Auth. Both CLIs authenticate headlessly from ANTHROPIC_API_KEY. On this
#    machine the key lives in the macOS keychain (Henry's `secret` CLI):
export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"

# 2. One eval (a skill candidate, claude, one model, both configs, 3 trials):
uv run --project harness agent-harness mermaid \
    --candidate-dir primitives-core/skills/mermaid \
    --harness claude --model claude-sonnet-4-5 --configs with,baseline --trials 3

# 3. Aggregate the ledger for a candidate:
uv run --project harness agent-harness mermaid --report

# 4. Loadability smoke only (inject the candidate, fail on plugin_errors):
uv run --project harness agent-harness mermaid \
    --candidate-dir primitives-core/skills/mermaid --smoke
```

Make targets (from the repo root):

| Target | Does |
|---|---|
| `make harness-test` | Run the harness unit tests (uv project; also a path-filtered CI lane). |
| `make harness-eval ITEM=<name> [HARNESS=] [MODEL=] [CAMPAIGN=]` | Eval a roster primitive. Resolves a skill *directory* (`primitives-core/skills/<name>/`) **and** a flat agent file (`primitives-core/agents/<name>.md`, auto-staged into a temp dir). |
| `make harness-report ITEM=<name>` | Aggregate the ledger for a candidate. |
| `make harness-coupling` | The stdlib-only no-repo-coupling gate (also in `make ci`). |

`harness-eval`/`harness-report` are **not** part of `make ci` — evals need live CLIs
+ API keys. Only the unit tests + the coupling gate gate CI.

### Grid syntax

`--harness` and `--model` are comma-separated to expand the grid; one command runs
every `(harness, model)` cell:

```sh
uv run --project harness agent-harness mermaid \
    --candidate-dir primitives-core/skills/mermaid \
    --harness claude,opencode --model claude-sonnet-4-5,claude-haiku-4-5 \
    --configs with,baseline --trials 3
```

Bare model ids are provider-normalized per harness (claude takes `claude-sonnet-4-5`
as-is; opencode maps it to `anthropic/claude-sonnet-4-5`), so one bare-id list spans
both harnesses and forms comparable cross-harness pairs. Unsupported injection kinds
(e.g. a Claude plugin under opencode) appear as explicit `passed=None` skip rows, not
silent gaps.

### Campaign

`--campaign <label>` (default `""`) is the first segment of the resume key
(`campaign|harness|model|candidate|case|config|trial`). Use it to keep a **re-run
after a harness fix** distinct from the pre-fix rows in the same ledger:

```sh
# re-run only the claude cells after a harness fix, without touching prior rows
uv run --project harness agent-harness mermaid \
    --candidate-dir primitives-core/skills/mermaid \
    --harness claude --campaign skillfix --configs with,baseline --trials 3
```

Rows written before the field read as `""` (backward compatible). The report shows a
`campaign` column only when some row carries a non-empty label, and deltas are
computed **within** a campaign, so a labeled re-run never merges with the old rows.

## Case authoring

A case is data, never code:

```
cases/<candidate>/<case-id>/
    case.json      { "prompt": "…", "assertions": [ { "id": "a1", "text": "binary, evidence-checkable" } ] }
    fixture/       (optional) seed files copied into the trial workspace
    check.py       (optional) deterministic stdlib script run in the final workspace,
                   printing a JSON list of { id, passed, evidence }
```

Grading is two-tier: `check.py` (tier 1, deterministic) then the LLM rubric grader
over `assertions` (tier 2). The pass rule: the CLI exits clean, no `plugin_errors` in
the `with` config, and every check + grade passes. Design a case so the `baseline`
config plausibly fails — the signal is the **with − baseline delta**, not the
absolute pass rate.

### The delta-framing rule

**When a case's rubric is derived from the skill's own doctrine, Δ measures
doctrine-conformance, not independent quality.** A `+1.0` on such a case says "the
skill fired and the model followed its rules end-to-end" — a real, valuable signal,
but not "the skill makes objectively better output than an unaided model by some
neutral standard." State which kind of delta a case yields when you cite it.

## Known caveats

- **Hermeticity asymmetry (claude vs opencode).** opencode runs under a throwaway
  `$HOME` + injected `OPENCODE_CONFIG_DIR` — fully isolated. The claude adapter now
  runs under a fresh per-run `CLAUDE_CONFIG_DIR` + an `apiKeyHelper` (so no user
  plugins/skills bleed in and env-key auth works headlessly), which closed most of
  the Wave-1 gap — but dropping `--bare` re-enables LSP/hooks (no user hooks are
  configured here, so benign in practice). The harnesses are *close* but not
  byte-identical in isolation; within-cell deltas are unaffected (both configs of a
  cell share any bleed), but treat cross-harness *absolute* pass rates accordingly.
- **Environment-contingent cases.** Some cases self-install runtime dependencies
  (the readme case runs `npm`/Playwright to capture a real screenshot). A blocked
  npm or offline runner collapses that pass path. The run-log header records the
  observable `preconditions` (auth env, model, grader, timeout, network=assumed);
  full environment pinning is not built (issue #172).
- **Passing-trial workspaces are destroyed** unless `--keep-workspaces` — set it for
  campaign runs you may want to audit; failures always keep their workspace (path in
  the row's `workspace` field).
- **Vision-dependent grader assertions** (e.g. "the screenshot shows X") are not
  verifiable post-hoc from the text ledger — a latent hallucination surface.
- **The Skill tool requires a non-`--bare` claude invocation** (#170). `--bare` set
  `CLAUDE_CODE_SIMPLE=1`, which stripped `Skill`/`Task` from the advertised toolset,
  so an injected skill loaded but could never be invoked. See handoff-w4 for the full
  probe matrix and the replacement's rationale.
- **Claude auth without an interactive login.** The claude path authenticates via an
  `apiKeyHelper` that echoes `$ANTHROPIC_API_KEY`; if that variable is unset, trials
  produce honest `Not logged in` error rows (never a fabricated pass). opencode falls
  back to the same provider env var.

## Invariants

- **No repo coupling.** Nothing under `harness/` imports from or reads repo files
  outside `harness/`; candidates and cases are passed as paths at runtime. Guarded by
  `tests/test_coupling.py` (uv lane) **and** `scripts/check_harness_coupling.py`
  (`make harness-coupling`, wired into `make ci` — stdlib-only so it needs no uv).
- **The grader is always the claude CLI** with a pinned Haiku model, held constant
  across every harness/model cell so grades stay comparable (DESIGN §3/D4). A
  deliberate claude-CLI dependency even for opencode-only runs.
- `runs/` (per-run logs) and temp workspaces are gitignored; `results.jsonl` is
  tracked (battle-test evidence + future eval_runs feedstock, DESIGN §8-D3).
- Row schema is stable (DESIGN §7 + `campaign`, `log_path`, and normalized token
  fields: `input_tokens`/`output_tokens`/`cache_read_tokens`/`cache_creation_tokens`).

## Extraction checklist

`harness/` is built to become its own repo (or a package) by **moving the directory** —
the no-coupling invariant is what makes that a move, not a rewrite. When extracting:

1. **Move `harness/`** to the new repo root. It already carries its own
   `pyproject.toml` + `uv.lock` and an `agent-harness` entry point — no import
   rewrites (the coupling gate proves zero outside references).
2. **Re-home the two gates.** `scripts/check_harness_coupling.py` and the
   `harness-coupling` / `harness-test` / `harness-eval` / `harness-report` Makefile
   targets live in the *parent* repo today. Port the coupling script (it only needs
   `agent_harness`'s own path) and recreate the make targets, or fold them into the
   new repo's `Makefile` / `pyproject` scripts.
3. **Re-home the CI lane.** `.github/workflows/harness-test.yml` is path-filtered to
   `harness/**` here; in a standalone repo drop the path filter (everything is the
   harness) and keep the `pip install uv` + `make harness-test` steps.
4. **Point `--cases-dir` / `--candidate-dir` at the new locations.** Cases can travel
   inside the harness repo (`cases/`) or live in the repo under evaluation and be
   passed at runtime — both already work; nothing is hardcoded.
5. **Carry the auth contract.** The quickstart's `ANTHROPIC_API_KEY` line and the
   claude `apiKeyHelper` mechanism are machine-agnostic; document the target
   machine's key source (keychain, CI secret, …).
6. **Decide the ledger's fate.** `results.jsonl` is this repo's battle-test evidence;
   a fresh extraction typically starts an empty ledger. The row schema is stable, so
   old rows stay ingestible (extender-db `eval_runs`).
7. **Optional adapters.** codex/copilot invocation patterns are recorded in DESIGN §1
   (non-goals) for a later adapter; Docker sandboxing is deferred to extraction time.
