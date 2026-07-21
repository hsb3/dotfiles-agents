# Wave 3 handoff — scout case authoring

_Agent-harness battle-test (DESIGN §6 Wave 3), candidate = the `scout` agent
(`primitives-core/agents/scout.md`, roster id `scout`, `plugins: [foreman-kit]`)._

Status: **1 case delivered**, verified standalone (no live agent runs — none were available/in
scope). **A real blocker for running this case live is flagged in §4** — not fixable inside my
file scope (`harness/cases/scout/**` + this handoff only).

---

## 1 · What was authored

`harness/cases/scout/stale-config-trap/`:

```
case.json                        prompt + 2 rubric assertions
check.py                         6 deterministic checks, stdlib only
fixture/                         13 files, a small "payments-svc" HTTP-client codebase
  README.md                        stale doc claim (says timeout=10s)
  CHANGELOG.md                     corroborates the real config lives in src/config.py,
                                    without giving the number itself (forces an actual read)
  docs/ARCHITECTURE.md             module map, points at validators.py as the "entry point"
  scripts/deploy.sh                noise
  src/__init__.py, logging_setup.py  noise
  src/config.py                    REAL config: REQUEST_TIMEOUT_SECONDS = 45 (line 10)
  src/legacy/settings.py           DECOY: dead, unimported module, REQUEST_TIMEOUT_SECONDS = 15
  src/http_client.py               imports from src.config (proves config.py is live)
  src/validators.py                validate_payload() delegates to schema_utils.check_schema
  src/schema_utils.py              REAL validation logic: check_schema() (line 6)
  tests/fixtures/stub_validators.py  DECOY: validate_payload() that always returns True
  tests/test_http_client.py        imports the decoy stub (realistic — a real test double)
```

I stopped at **one** case rather than two. Rationale: the brief caps at 1–2 and treats them as
independent measurements of the same underlying question (does scout's read-only, path:line-
cited discipline change delegated-recon output quality). A second case would mostly duplicate
that mechanism on a different fixture; I judged one fixture with **two independent traps**
(config-value staleness + function-name decoy), six deterministic checks, and three
hand-verified failure modes (§3) as better return on the wave's effort budget than two shallower
cases. If a second case is wanted later, the natural axis to vary is a *negative* case (a
question scout should report as unanswerable/ambiguous per its "Stop conditions" — "report the
ambiguity instead of resolving it yourself"), which this case doesn't exercise.

---

## 2 · Fixture design — what makes baseline plausibly wrong

Two independent, stackable traps, both regex-checkable because I authored the ground truth:

1. **Stale/duplicated config value.** Three numbers exist for "the request timeout": `README.md`
   says 10s (stale doc, never updated), `src/legacy/settings.py` says 15s (dead code — nothing
   imports it, `CHANGELOG.md` explicitly says it was superseded in v1.2), and `src/config.py`
   says 45s (the value actually imported by `src/http_client.py`, i.e. the real answer). A
   shallow recon (read the README, or grep the first `REQUEST_TIMEOUT_SECONDS` hit without
   checking what's actually imported) lands on 10 or 15, not 45.
2. **Decoy function definition.** `validate_payload` is defined in **two** places:
   `tests/fixtures/stub_validators.py` (an always-`True` test stub, imported only by
   `tests/test_http_client.py`) and `src/validators.py` (the real entry point, which delegates to
   `check_schema` in `src/schema_utils.py`). A grep for `def validate_payload` without tracing
   imports surfaces the stub as if it were production logic.

The prompt (`case.json`) explicitly warns that "the docs, a deprecated settings module, and a
test-only stub all disagree... trace imports rather than trusting any single file" — this is
deliberate: the case measures *evidence discipline under a fixture designed to punish
citation-without-verification*, not "can the model find any file containing the word timeout."
Scout's own definition (`primitives-core/agents/scout.md`) names exactly this move as its value:
"Cross-file reconciliation... does the validation in A match the schema in B... weighing partial
matches," and its Evidence-format section mandates `path:line` citation and an
observed-vs-inferred flag. The baseline (no scout injected) is not blocked from succeeding — it
can self-recon with the same Read/Grep/Glob tools — but has no external discipline forcing it to
cite `path:line` or to trace the import graph before concluding.

---

## 3 · Correct answers + how checks encode them

Ground truth, hardcoded in `check.py` as constants (not re-derived from the live workspace —
see the guard below for why):

| Fact | Correct answer | Evidence location |
|---|---|---|
| Production request timeout | **45** seconds | `src/config.py:10` |
| Real `validate_payload` logic | `check_schema()` | `src/schema_utils.py:6` |

`check.py` checks (all stdlib, JSON list of `{id, passed, evidence}`):

1. `findings-exists` — `FINDINGS.md` was written.
2. `findings-has-both-sections` — has `## Timeout` and `## Validation` headers (the prompt's
   requested structure).
3. `timeout-value` — the literal token `45` (word-boundary) appears anywhere.
4. `timeout-citation` — a tolerant `path:line` pattern (optional `./` prefix, optional
   surrounding punctuation/backticks) matching `src/config.py:10` appears.
5. `validation-citation` — same pattern matching `src/schema_utils.py:6`.
6. `fixture-not-mutated` — `src/legacy/settings.py` still contains
   `REQUEST_TIMEOUT_SECONDS = 15` unchanged. Guards against a trial "fixing" the decoy file in
   place (which the prompt explicitly forbids — "Do not modify any other file") instead of
   reporting on it; also means the check can safely hardcode line numbers rather than re-deriving
   them from a workspace an agent might have edited.

`case.json` assertions (LLM-rubric tier, 2, both narrow/binary/evidence-checkable): one per fact,
each phrased as "states X, does not present the stale/decoy value as production truth" — this is
the nuance regex can't fully capture (e.g. a FINDINGS.md that quotes the stale value *and labels
it stale* should pass; one that states it as the answer should not), left to the grader.

---

## 4 · Verification

### 4a — `check.py` standalone: hand-built PASS workspace

```
$ cd $SCRATCH/mock-ws-pass && python3 check.py | python3 -m json.tool
[
    {"id": "findings-exists", "passed": true, "evidence": "FINDINGS.md present"},
    {"id": "findings-has-both-sections", "passed": true, "evidence": "FINDINGS.md has '## Timeout' and '## Validation' headers"},
    {"id": "timeout-value", "passed": true, "evidence": "FINDINGS.md contains the correct timeout value '45'"},
    {"id": "timeout-citation", "passed": true, "evidence": "FINDINGS.md cites src/config.py:10"},
    {"id": "validation-citation", "passed": true, "evidence": "FINDINGS.md cites src/schema_utils.py:6"},
    {"id": "fixture-not-mutated", "passed": true, "evidence": "src/legacy/settings.py content unchanged"}
]
```

### 4b — three hand-built FAIL workspaces

**Fail 1 — shallow recon takes the README + stub at face value** (states 10s, cites the stub as
production validation, no `path:line` citations at all):
```
[
    {"id": "findings-exists", "passed": true, ...},
    {"id": "findings-has-both-sections", "passed": true, ...},
    {"id": "timeout-value", "passed": false, "evidence": "FINDINGS.md does not contain '45'"},
    {"id": "timeout-citation", "passed": false, "evidence": "FINDINGS.md does not cite src/config.py:10 (the real source of REQUEST_TIMEOUT_SECONDS)"},
    {"id": "validation-citation", "passed": false, "evidence": "FINDINGS.md does not cite src/schema_utils.py:6 (the real check_schema implementation)"},
    {"id": "fixture-not-mutated", "passed": true, ...}
]
```

**Fail 2 — `FINDINGS.md` never written:**
```
[
    {"id": "findings-exists", "passed": false, "evidence": "FINDINGS.md missing in workspace"},
    {"id": "findings-has-both-sections", "passed": false, ...},
    {"id": "timeout-value", "passed": false, ...},
    {"id": "timeout-citation", "passed": false, ...},
    {"id": "validation-citation", "passed": false, ...},
    {"id": "fixture-not-mutated", "passed": true, ...}
]
```

**Fail 3 — correct answers, but the decoy file was edited in place instead of reported on**
(everything else right):
```
[
    {"id": "findings-exists", "passed": true, ...},
    {"id": "findings-has-both-sections", "passed": true, ...},
    {"id": "timeout-value", "passed": true, ...},
    {"id": "timeout-citation", "passed": true, ...},
    {"id": "validation-citation", "passed": true, ...},
    {"id": "fixture-not-mutated", "passed": false, "evidence": "src/legacy/settings.py missing or modified — task asked to only write FINDINGS.md"}
]
```

Each failure mode trips exactly the check(s) it should and nothing else — confirms the checks
are discriminating, not just "always green."

### 4c — case loads via `agent_harness.cases.load_cases`

```
$ cd harness && python3 -c "
from agent_harness.cases import load_cases
cases = load_cases('scout', 'cases')
for c in cases:
    print(c['id'], '->', c['dir'])
    print('  prompt len:', len(c['prompt']))
    print('  assertions:', [a['id'] for a in c.get('assertions', [])])
"
stale-config-trap -> cases/scout/stale-config-trap
  prompt len: 1125
  assertions: ['a1-timeout-not-stale', 'a2-validation-not-stub']
OK: loaded 1 case(s)
```

Also confirmed the existing `harness/tests/test_cases.py` (independent of my case) still passes
(`Ran 6 tests ... OK`) and `python3 -m py_compile` on `check.py` + every fixture `.py` file
succeeds (syntax-clean); `__pycache__` litter produced by that compile check was removed before
finishing (fixture is back to exactly 13 tracked files, confirmed via `find fixture -type f`).

**Not verified (explicitly out of scope per the brief — "no live agent runs"):** an actual
`with`/`baseline` trial pair. See §4d for what blocks running one at all right now.

### 4d — feasibility: no case-format blocker, but a real candidate-injection blocker exists

The brief's STOP condition is about the case being workspace-checkable — it is (§3/§4a/§4b prove
it deterministically). But I found a **separate, real blocker** to actually running this (or any
`agent`-kind) case live, in `Makefile`'s `harness-eval` target (not in my file scope, flagged
here per "required out-of-scope changes for other owners"):

```
$ find primitives-core -mindepth 2 -maxdepth 2 -type d -name "scout"
(no output)
```

`harness-eval`'s candidate-dir resolution (`Makefile:50`) is
`find primitives-core -mindepth 2 -maxdepth 2 -type d -name "$(ITEM)"` — it only matches a
**directory** named `scout` under `primitives-core/<type>/`. But scout's actual roster source
(`primitives-core.yaml`) is `primitives-core/agents/scout.md` — a **flat file**, not a directory.
The same is true of every other agent candidate (`builder.md`, `lead.md`, `reviewer.md` — all
flat files in `primitives-core/agents/`). So `make harness-eval ITEM=scout` currently exits
`no primitive named 'scout' under primitives-core/` before it ever reaches the harness. This is
systemic to *all four* agent-kind candidates, not scout-specific.

Two follow-ups for whoever owns the Makefile / runs the live grid:
1. **Candidate-dir resolution needs an agent-kind path**, e.g. matching `primitives-core/agents/*.md`
   by stem instead of requiring a directory.
2. **A judgment call once that's fixed**: `ClaudeAdapter._agent_definitions()`
   (`harness/agent_harness/adapters/claude.py`) reads *every* `.md` file in the given
   `candidate_dir` and injects all of them as separate subagent types. If `--candidate-dir` is
   pointed at `primitives-core/agents/` (the only real directory), the `--agents` payload will
   register **all four** of scout/builder/reviewer/lead simultaneously — not an isolated
   single-candidate injection. Whoever runs the grid needs to either (a) materialize a synthetic
   per-agent temp directory containing only `scout.md` (mirroring how `skill` candidates already
   get a synthetic single-item plugin wrapper), or (b) accept that the "candidate" being measured
   is really "the foreman-kit agent quartet," which changes what the case's delta means. I did not
   resolve this — it's runner/adapter plumbing, out of my `harness/cases/scout/**` scope.

### 4e — a second, pre-existing risk to this case's measurement validity (not mine to fix)

Wave 1's handoff (`handoff-w1.md` §8b) already flagged: even under `--bare`, the init event shows
the *user's own enabled plugins/skills* (including `foreman-kit`, which owns scout) loading into
every trial session alongside whatever the harness injects. If this case is run on a machine
where `foreman-kit` is enabled as a user plugin, the **baseline** config may *already* have a
`scout` subagent type available from the user's own Claude Code config, contaminating the
with-vs-baseline delta this case is designed to measure. Wave 1 records a Wave-4 follow-up
(throwaway `HOME`/`CLAUDE_CONFIG_DIR`) to fix this; I'm surfacing it again here because it
directly threatens *this* case's validity, not just abstract hermeticity.

I confirmed the `--agents` JSON schema itself only carries `description` + `prompt`
(`claude --help` --agents example: `{"reviewer": {"description": ..., "prompt": ...}}`) — no
`tools`/`model`/`maxTurns` fields. So scout's `tools: Read, Grep, Glob` restriction from its
frontmatter is **not enforced by the CLI when injected via `--agents`**; it lives only as a
prompted instruction in the body ("You must NOT edit or create files, run commands, touch git").
This doesn't affect my case (the check grades the final `FINDINGS.md`, not tool usage), but it
means "read-only" is a behavioral claim under this injection path, not a sandboxed guarantee —
worth knowing when interpreting `with`-config results across any agent-kind case.

---

## 5 · File ownership / housekeeping

- Touched only `harness/cases/scout/**` (new) and this handoff. No other file read for editing.
- No git mutations (only read-only `git status`/`find`/`grep`).
- No `.claude/agent-memory/` written.
- Scratch mock workspaces for §4a/§4b verification live in the session scratchpad
  (`/private/tmp/claude-501/.../scratchpad/mock-ws-*`), not in the repo.
- `__pycache__` dirs created transiently by my own `py_compile` verification runs were removed
  before finishing; `harness/cases/scout/stale-config-trap/fixture/` contains exactly the 13
  intended files (confirmed via `find fixture -type f | wc -l`).
