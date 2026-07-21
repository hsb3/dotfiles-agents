# Wave 2 handoff — OpencodeAdapter

_Agent-harness build (`feat/agent-harness`). Wave 2 = the opencode vendor adapter behind the
Wave-1 seam, plus minimal CLI grid support. The run core is unchanged (seam honored)._

Status: **delivered.** `make harness-test` green (90 tests: Wave-1's 61 + 28 new + 1 rewritten
registry test); `make ci` green (120 marketplace tests). Live end-to-end **proven**: one command
ran a 4-cell grid (claude + opencode × two models), all four cells PASS, real ledger rows
appended. opencode version tested: **1.18.0**.

---

## 1 · What I built (owned files)

1. **`harness/agent_harness/adapters/opencode.py`** — the six-member Adapter API + `cli_version`.
2. **`harness/agent_harness/adapters/__init__.py`** — registered `OpencodeAdapter` (one line in
   `ADAPTERS` + `__all__` export).
3. **`harness/tests/test_opencode_adapter.py`** — 28 tests mirroring the claude adapter's coverage
   + opencode specifics + the CLI grid-cell expansion.
4. **`harness/agent_harness/cli.py`** — comma-separated `--harness`/`--model` expand to
   `(harness, model)` cells (new pure `_cells()` helper + a grid loop in `main()`). **No `core.py`
   change** — the grid lives entirely in the CLI, per the brief's "keep the diff minimal" clause.

### Out-of-scope change I was forced to make (flag for the foreman)

**`harness/tests/test_adapters_registry.py`** (NOT in my owned list) — one test used
`get_adapter("opencode")` as its example *unknown* harness, with the inline comment `# not wired
until Wave 2` and a file docstring reading "the vendor seam **Wave 2 extends**". Registering
opencode (my sanctioned deliverable #2) mechanically invalidates that assertion — you cannot
register `opencode` while a test asserts `opencode` is unregistered. I made the minimal swap
(placeholder `"opencode"` → `"codex"`, a documented non-goal adapter; added a
`test_opencode_is_registered`) because (a) it is atomic with my registry edit, not a separate
improvement, (b) the Wave-1 author explicitly signposted it as Wave-2's to flip, and (c) the
brief mandates a green `make harness-test`, impossible otherwise. Judgment recorded here rather
than silently absorbed. If a different owner holds that file, reconcile — but the case authors
own `cases/`, so no collision is expected.

---

## 2 · Empirical findings (opencode 1.18.0, probed live 2026-07-21)

The scout recon was strong; here is what the live probes confirmed / corrected. Verify commands
are reproducible via `opencode debug …` (no tokens burned) + the live run in §4.

- **Permission bypass = `--auto`.** 1.18.0 has **no** `--dangerously-skip-permissions` (proven via
  `opencode run --help`). `--auto` = "auto-approve permissions that are not explicitly denied";
  it covers the `write`/`edit` tool that a file-creation task needs. Belt-and-suspenders: the
  injected `opencode.json` also grants `permission.skill.<name>: allow` (the default `skill`
  permission is `ask`, which would block headless even under `--auto` leniency for a skill call).
- **`OPENCODE_CONFIG_DIR` works** (the scout's primary hypothesis; NOT in the local
  opencode-expertise skill, which predates it). Empirically: with `OPENCODE_CONFIG_DIR=<dir>`,
  `opencode debug skill` lists a skill dropped at `<dir>/skills/<name>/SKILL.md`,
  `opencode debug agent <name>` resolves `<dir>/agents/<name>.md`, and `opencode debug config`
  shows `<dir>/opencode.json` **merged into config** (my injected `permission.skill` grant
  appeared). Note: `opencode debug paths` still reports the HOME-based config path — so
  `OPENCODE_CONFIG_DIR` is an **additional layered search root** for the plural subdirs +
  `opencode.json`, not a replacement of the config path. This is exactly the injection surface.
- **Injection is via env, not CLI flags.** opencode has no `--plugin-dir` analogue. So the
  adapter's `inject()` materialises `<tmpdir>/oc-config` (with `skills/` or `agents/` +
  `opencode.json`) and returns it in `Injection.files=[config_dir]`; `invocation()` reads
  `files[0]` and exports `OPENCODE_CONFIG_DIR`. `Injection.flags` stays empty for every kind.
  Baseline config (injection omitted) → no `OPENCODE_CONFIG_DIR` → clean base run.
- **Throwaway HOME + env-var auth works with zero config.** A fresh `$HOME` (inside the run
  tmpdir, per handoff-w1 §7) has no `auth.json`; passing `ANTHROPIC_API_KEY` through is sufficient
  — opencode's anthropic provider falls back to it. Confirmed: full isolated run (throwaway HOME +
  `OPENCODE_CONFIG_DIR` + env key) created `HELLO.txt` correctly and `opencode debug skill`
  under that HOME showed only the built-in + my injected `eval-echo` (no user-config bleed — the
  isolation the claude adapter still lacks per handoff-w1 §8b).
- **`--format json` event schema** (matches the scout hypothesis). Envelope per JSONL line:
  `{"type": <t>, "timestamp": <ms-epoch>, "sessionID": …, "part": {…}}`. Top-level `type` is the
  **underscore** form (`step_start`, `text`, `tool_use`, `step_finish`, `error`); confusingly
  `part.type` uses **hyphens** (`step-start`, `tool`, `step-finish`). Discriminate on the envelope
  `type`. Field map used by `parse_log`:
  - `tool_use` → `part.tool` (e.g. `"write"`) → `tool_names`; `part.tool == "skill"` → `skill_used`.
  - `step_finish` → `part.cost` (summed → `cost_usd`), `part.reason` (`"tool-calls"|"stop"`).
  - `step_start` → counted → `num_turns`.
  - `text` → `part.text` → accumulated into `result`.
  - `duration_ms` → `max(timestamp) − min(timestamp)` across events (every event carries a numeric
    ms-epoch `timestamp`; no single duration field exists). The core does not pass wall-clock to
    `parse_log`, so this is the source of truth — consistent with the claude adapter reading its
    own log for duration.
  - **Missing-final-`step_finish` gap (opencode#26855):** `parse_log` scans the *whole* stream and
    never assumes the last line is terminal — cost accrues from every `step_finish` seen, so a
    dropped final event just loses that one step's cost/duration, no crash. Unit-tested.
- **`skill_used` mapping (`part.tool == "skill"`) is structural, not exercised live** — the
  smoke-echo task is trivial and the model wrote the file with the `write` tool without invoking
  the injected (no-op) skill. A Wave-3 case that *forces* a skill call would exercise it.

### The stdin gotcha that cost the most probe time (record for Wave 3/4)

`opencode run` **hangs indefinitely with zero output if stdin is an open pipe.** Every one of my
first probes hung at "init" for minutes — not the sandbox, not auth, not throwaway HOME. The fix:
**close stdin** (`< /dev/null`). The harness core already does this (`stdin=subprocess.DEVNULL`),
so the real harness runs fine (5–30 s) — but any *manual* `opencode run` probe MUST redirect
`< /dev/null` or it will appear to hang. This is the opencode analogue of Wave-1's `--bare`/auth
gotcha.

---

## 3 · Design decisions (judgment calls the brief left open)

- **Model provider-normalization (`_provider_prefixed`).** opencode requires `provider/model`.
  A model id containing `/` passes through; a bare id gets `anthropic/` prepended. This is what
  lets **one bare-id `--model` list span both harnesses** in the grid: claude takes
  `claude-sonnet-4-5` as-is, opencode maps it to `anthropic/claude-sonnet-4-5`. The ledger records
  the **requested** (bare) id as the model dimension, so `claude|claude-sonnet-4-5` and
  `opencode|claude-sonnet-4-5` are a comparable cross-harness pair; `cli_version` distinguishes.
- **Pinned default model = `anthropic/claude-sonnet-4-5`.** A throwaway HOME has no configured
  default model, so `-m` must always be sent; when the run model is `None`/`"default"`, this
  constant is used (`OpencodeAdapter.DEFAULT_MODEL`).
- **Agent injection makes the agent *available*, no `--agent` flag** — mirrors the claude adapter
  (`--agents` defines subagents without forcing the run to *be* one). Translation: CC `name` →
  filename; `description` kept; `mode: subagent` added; bare `model:` gets the provider prefix (or
  is dropped to inherit the run model); CC `tools:` allowlist → opencode `permission:` map, with
  the inversion made explicit (unlisted `edit`/`bash` emitted as `deny`, listed tools as `allow`,
  narrow rules last since opencode evaluates the *last* matching rule). `opencode run --agent
  <name>` exists (confirmed in `--help`) if a future case wants to force the agent as primary.
- **Skill-name regex skip.** opencode's name rule (`^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64) is stricter
  than CC's; a failing name is *silently invisible* to opencode. So an invalid dir basename →
  `Injection([], [], supported=False)` (explicit skip row), never a silently-dead injection.
- **Plugin kind → `supported=False`.** A CC plugin bundle (`.claude-plugin/` + hooks) has no
  mechanical opencode translation (hooks need a bespoke TS plugin — "Hooks → NOT mechanical",
  opencode-expertise). Explicit skip row with that reason; no transpiler built (v1).
- **`preflight` noauth is meaningful for opencode** (unlike claude's PATH-only stub): because every
  trial uses a throwaway HOME, persisted auth is bypassed and the only usable credential is a
  provider env var — so "no provider key in env" (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/… list) is a
  genuine, cheap `noauth` signal.
- **Env hygiene:** `invocation()` pops inherited `OPENCODE_CONFIG`/`OPENCODE_CONFIG_CONTENT`/
  `OPENCODE_CONFIG_DIR` before setting its own, so a stray parent config can't leak into a trial.

---

## 4 · Verification (verbatim)

### 4.1 `make harness-test`
```
Ran 90 tests in 2.109s
OK
```

### 4.2 `make ci`
```
✓ roster<->disk clean — 31 primitives (agent=4, hook=4, skill=23)
✓ skill-catalog clean — 5 standalone skill(s), eligibility + drift + namespacing OK
✓ standalone wrappers OK — 5 one-skill plugin(s), all byte-identical to source
✓ marketplace artifacts match source — no drift
Ran 120 tests in 5.405s
OK
```

### 4.3 CLI grid syntax + unknown-harness exit 3
```
$ uv run --project harness python -m agent_harness --help
  --harness HARNESS  harness(es) to drive — comma-separated for a grid
                     (valid: claude, opencode; e.g. claude,opencode)
  --model MODEL      trial model(s) — comma-separated for a grid … Bare ids are
                     provider-normalized per harness … (e.g. claude-sonnet-4-5,claude-haiku-4-5)

$ uv run --project harness python -m agent_harness foo --harness bogus --candidate-dir /tmp ; echo exit=$?
unknown harness 'bogus'; valid harnesses: claude, opencode
exit=3
```

### 4.4 Live end-to-end grid — ONE command, 4 cells, all PASS (30 s)
`agent-harness smoke-echo --candidate-dir <trivial eval-echo skill> --harness claude,opencode
--model claude-haiku-4-5,claude-sonnet-4-5 --configs with --trials 1` (results → scratchpad, not
the tracked ledger, per Wave-1 judgment #6):
```
harness  model             case         config  n  pass  p@n  p^n   cost μ±σ      ms μ±σ
claude   claude-haiku-4-5  create-file  with    1   1.0   Y    Y   0.0074±0.0    5253±0.0
claude   claude-sonnet-4-5 create-file  with    1   1.0   Y    Y   0.0157±0.0    9383±0.0
opencode claude-haiku-4-5  create-file  with    1   1.0   Y    Y   0.0121±0.0    1430±0.0
opencode claude-sonnet-4-5 create-file  with    1   1.0   Y    Y   0.0365±0.0    4357±0.0
```
**W2 criteria met:** ≥2 opencode model cells + ≥1 claude cell from one command ✓; same-model
cross-harness pair (sonnet AND haiku via both CLIs) ran end-to-end ✓. Unsupported-kind skip rows
are covered by `core.TestUnsupportedSkip` + `test_opencode_adapter` (plugin/bad-name/unknown →
`supported=False`); not shown live because the smoke candidate is a valid skill.

### 4.5 Appended opencode ledger row (haiku cell, verbatim; all 22 DESIGN §7 fields, `harness="opencode"`)
```json
{"candidate":"smoke-echo","case":"create-file","config":"with","trial":0,"harness":"opencode",
 "model":"claude-haiku-4-5","kind":"skill","passed":true,"exit_code":0,"error":null,
 "checks":[{"id":"hello-file-exists","passed":true,"evidence":"HELLO.txt present"},
           {"id":"hello-content","passed":true,"evidence":"HELLO.txt content='harness-ok' (want 'harness-ok')"}],
 "grades":[],"grader_model":null,"skill_used":false,"tool_names":["write"],"plugin_errors":[],
 "cost_usd":0.0121461,"duration_ms":1430,"num_turns":2,"cli_version":"1.18.0",
 "workspace":null,"ts":"2026-07-21T14:54:23"}
```

### 4.6 Raw JSONL first/last events (justifies the parse_log mapping)
```
first: {"type":"step_start","timestamp":1784660071868,"sessionID":"ses_…","part":{…,"type":"step-start"}}
last:  {"type":"step_finish","timestamp":1784660076225,"sessionID":"ses_…","part":{"reason":"stop","type":"step-finish","tokens":{"total":8364,…}}}
seq:   step_start text tool_use step_finish step_start text step_finish
```
→ `num_turns=2` (2×`step_start`), `cost_usd=0.0121461` (Σ `step_finish.part.cost`),
`duration_ms=1430` (max−min `timestamp`), `tool_names=["write"]`. Matches the row above.

---

## 5 · Deferred / notes for later waves

- **`skill_used` live-exercise** — needs a Wave-3 case that forces the model to call the injected
  skill (the trivial smoke case doesn't). The `part.tool == "skill"` mapping is unit-tested but
  unproven against a real skill invocation.
- **`error`-event schema unobserved** — `parse_log._error_message` is a defensive best-effort
  (checks `message`/`error`/`text`/`name`). Load errors on non-zero exit still surface via the
  core's stderr→`error` path regardless. Capture a real `error` event when one occurs.
- **Agent `permission:` mapping is best-effort v1** — covers the consequential surfaces
  (`edit`/`bash` deny + listed-tool allow) via `_TOOL_PERMISSION_MAP`; not every CC tool has an
  opencode permission key. Refine if a Wave-3 agent case needs finer control.
- **opencode throwaway-HOME first-run latency** — a brand-new HOME may fetch the model catalog on
  first use; runs still completed in seconds here, but a cold devcontainer could be slower. The
  core `--timeout` (default 600 s) covers it.
- **grader unchanged** — `grading.run_grader` stays claude + pinned Haiku for every cell (D4); not
  routed through the seam. Confirmed opencode cells with no assertions record `grades:[]`,
  `grader_model:null` (smoke-echo has no assertions). A Wave-3 opencode cell WITH assertions will
  invoke the claude grader — that path is inherited from Wave 1, untouched here.
- **CLI ordering micro-change (noted for completeness):** candidate-dir/kind validation now runs
  *before* preflight in `main()` (was after) so it can be shared across grid cells. Only affects
  the pathological "CLI missing AND bad args" case (now exit 2 not 1); no test pinned the old
  order. Single-cell exit codes are otherwise identical (0/1/2/3 preserved).

## 6 · Housekeeping

- No git mutations (read-only `git status/diff/log` only). No `.claude/agent-memory/` written.
- Live-probe artifacts (trivial candidate, grid ledger, run logs) live in the session scratchpad,
  never the repo — the tracked `harness/results.jsonl` is untouched.
- Untracked `harness/cases/{mermaid,scout,readme-value-and-proof}/` + `handoff-w3-*.md` are the
  parallel Wave-3 case authors' work — not mine, left untouched. `evals/` residue also untouched.
