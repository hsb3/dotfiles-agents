# Wave 3 handoff — mermaid candidate cases

_Agent-harness build (`feat/agent-harness`). Wave 3 case authoring for the `mermaid` skill
(`primitives-core/skills/mermaid/SKILL.md`). Cases are data only — no live agent runs were
executed; verification is check.py run standalone against hand-assembled mock workspaces plus
`load_cases` parse confirmation.

Status: delivered — 2 cases authored, both check.py scripts verified pass/fail-discriminating
across 4 mock workspaces each (8 total), case loading confirmed via `agent_harness.cases`.

---

## 1 · Cases authored

`harness/cases/mermaid/`

### `add-architecture-diagram/`

**Prompt** (fixture: `services/{api_gateway,auth_service,core_api,worker,queue,datastore}.py`,
each a one-line module docstring with tempting parenthetical technical detail, e.g.
`"""Auth Service (OAuth2 + JWT) - issues and validates access tokens..."""`, plus a starter
`README.md` with no diagram yet): read all six service docstrings, add an `## Architecture`
section to `README.md` with a Mermaid diagram of all six components and their data/request
flow; don't modify `services/`.

This is the brief's own example ("add an architecture diagram of this codebase to README.md")
made concrete, with source content specifically engineered to bait the mistake the skill exists
to prevent: naturally-occurring parenthetical detail in the thing being diagrammed.

**Why baseline plausibly fails:** SKILL.md L10–24 states the house rule ("No parentheses or
special characters in node labels — they break rendering") and gives the skill's own WRONG
example: `B[Auth Service (JWT)]`. Without the skill loaded, a model summarizing
`"""Auth Service (OAuth2 + JWT) - ..."""` into a node label has every reason to carry the
parenthetical straight through (it's literally the concise service description) — that is
exactly `B[Auth Service (JWT)]` reproduced with real content. This is a genuine, observed-shape
mistake (GitHub-rendered Mermaid silently blanking on a special character), not a contrived
one.

**Deterministic checks** (`check.py`), each traced to skill source:
- `c1-mermaid-fence-in-readme` — a ` ```mermaid ` fence exists in README.md at all.
- `c2-diagram-type-declared` — the block opens with a recognized diagram-type keyword
  (SKILL.md L30–38 diagram-type table: `flowchart`/`graph` + direction, or
  `sequenceDiagram`/`erDiagram`/`stateDiagram`/`classDiagram`).
- `c3-house-rule-no-special-chars-in-labels` — no `(){}[]#;"<>&` inside node-label text,
  edge-pipe-label text (`|label|`), or subgraph-title text (SKILL.md L10–24, L58 edge-label
  note, L59 subgraph-title note). **Shape-aware**: node-shape delimiters
  (`[box]`, `(rounded)`, `{diamond}`, `[(database)]`, `((circle))` — SKILL.md L57, and the
  skill's own `DB[(Postgres)]` example at L47) are peeled off *before* checking label content,
  so legitimate mermaid syntax isn't misflagged (see §3 below — this was a real bug I found and
  fixed during verification).
- `c4-services-untouched` — `services/auth_service.py` byte-identical to the fixture (spot-check
  for the prompt's explicit "do not modify" instruction).

**LLM-rubric assertion** (non-deterministic — completeness/relevance, not syntax):
`a1-diagram-covers-all-services` — diagram has a distinct node for each of the six components,
not a generic/partial placeholder.

### `avoid-reserved-node-id/`

**Prompt** (fixture: `pipeline.py` with five stage functions `start`, `extract`, `transform`,
`load`, `end`; starter `PIPELINE.md` stub): read `pipeline.py`, add a `## Pipeline Flow` section
to `PIPELINE.md` with a Mermaid flowchart of the five stages in order, **using each function's
exact name as that node's identifier**; don't modify `pipeline.py`.

**Why baseline plausibly fails:** SKILL.md's Pitfalls table (L146) names this exact trap:
"Reserved word as bare node id (`end`, `class`)" → symptom "`Syntax error in text`" → fix
"Rename the id (`fin`, `cls`)". The prompt explicitly instructs the model to use the literal
function name as the node id, and one of those names is `end` — mermaid's own bare-`end` is a
grammar keyword (closes `subgraph` blocks), so a flowchart node literally wired as
`load --> end` breaks the parser. A baseline model has direct instruction pressure to do exactly
this; the skill is what tells it to recognize the trap and rename the id while keeping `end` as
the *label* if it wants (`fin[end]`), which is what the "pass" mock workspace below does.

**Deterministic checks** (`check.py`):
- `c1-mermaid-fence-in-pipeline-md` — fence exists in PIPELINE.md.
- `c2-diagram-type-declared` — recognized opening line (flowchart/graph or state/sequence).
- `c3-no-bare-reserved-end-node-id` — heuristic regex family that flags `end` only when it's in
  *identifier* position (immediately adjacent to a shape delimiter `end[`/`end(`/`end{`, or
  adjacent to an arrow token `--> end` / `end -->`, or a class-assignment `end:::`) — not when
  `end` merely appears as label text (`fin[end]` or `[the end]` both pass). Directly encodes
  SKILL.md L146.
- `c4-nontrivial-chain` — ≥4 arrow connections (sanity check the 5-stage chain isn't degenerate).
- `c5-pipeline-source-untouched` — `pipeline.py` byte-identical to the fixture (full-content
  equality, not prefix — see §3, this was also a bug I found and fixed).

**LLM-rubric assertion**: `a1-stages-in-correct-order` — the five stages appear in correct
execution order, not reordered/generic.

---

## 2 · Verification — check.py run standalone against mock workspaces

No live agent runs (cases are data per the brief). For each case I hand-assembled 4 mock trial
workspaces (fixture + hand-written "what the agent might have produced" README/PIPELINE.md +
optional tamper) in the scratchpad, then ran `check.py` with that workspace as cwd. All 8 runs
below are the verbatim outputs (post-fix — two real bugs found and fixed mid-verification, see
§3).

### `add-architecture-diagram` (4 workspaces)

**Pass** (clean diagram, all 6 nodes, uses the `[(database)]` cylinder shape legitimately):
```json
[{"id": "c1-mermaid-fence-in-readme", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-house-rule-no-special-chars-in-labels", "passed": true,
  "evidence": "no forbidden characters found in node/edge/subgraph labels"},
 {"id": "c4-services-untouched", "passed": true, "evidence": "services/auth_service.py unchanged"}]
```

**Fail — parens copied from docstrings verbatim** (the realistic baseline mistake):
```json
[{"id": "c1-mermaid-fence-in-readme", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-house-rule-no-special-chars-in-labels", "passed": false,
  "evidence": "5 house-rule violation(s): box-shape label 'Auth Service (OAuth2 + JWT)' contains ['(', ')']; box-shape label 'Core API (Django)' contains ['(', ')']; box-shape label '(Primary Datastore (PostgreSQL))' contains ['(', ')']; box-shape label 'Job Queue (Redis)' contains ['(', ')']; box-shape label 'Background Worker (Celery)' contains ['(', ')']"},
 {"id": "c4-services-untouched", "passed": true, ...}]
```

**Fail — no mermaid fence at all** (prose-only "architecture" description):
```json
[{"id": "c1-mermaid-fence-in-readme", "passed": false, "evidence": "no ```mermaid fenced block found in README.md"},
 {"id": "c2-diagram-type-declared", "passed": false, ...},
 {"id": "c3-house-rule-no-special-chars-in-labels", "passed": false, "evidence": "no mermaid block to check (c1 failed)"},
 {"id": "c4-services-untouched", "passed": true, ...}]
```

**Fail — services/ modified** (appended a line to `auth_service.py`):
```json
[{"id": "c1-mermaid-fence-in-readme", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-house-rule-no-special-chars-in-labels", "passed": true, ...},
 {"id": "c4-services-untouched", "passed": false,
  "evidence": "services/auth_service.py missing or modified (got '\"\"\"Auth Service (OAuth2 + JWT) - issues and validates access tokens for the plat')"}]
```

Also separately verified a 5th "shapes" workspace using `(rounded)`, `{diamond}`, `((circle))`,
`([stadium])` node shapes (no forbidden content) — `c3` correctly passes, confirming the
shape-aware peeling doesn't over-flag legitimate mermaid syntax.

### `avoid-reserved-node-id` (4 workspaces)

**Pass** (renamed id to `fin`, kept `end` as display label — the skill's own suggested fix):
```json
[{"id": "c1-mermaid-fence-in-pipeline-md", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-no-bare-reserved-end-node-id", "passed": true, "evidence": "no bare `end` node identifier found"},
 {"id": "c4-nontrivial-chain", "passed": true, "evidence": "found 4 arrow connection(s) in the diagram (want >= 4)"},
 {"id": "c5-pipeline-source-untouched", "passed": true, "evidence": "pipeline.py unchanged"}]
```

**Fail — bare `end` used as literal node id** (the realistic baseline mistake, following the
"use exact function name" instruction literally):
```json
[{"id": "c1-mermaid-fence-in-pipeline-md", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-no-bare-reserved-end-node-id", "passed": false,
  "evidence": "2 reserved-word violation(s): pattern '\\\\bend\\\\s*[\\\\[({]' matched 'end['; pattern '(?:-->|---|-\\\\.->|==>)\\\\s*end\\\\b(?!\\\\w)' matched '--> end'"},
 {"id": "c4-nontrivial-chain", "passed": true, ...},
 {"id": "c5-pipeline-source-untouched", "passed": true, ...}]
```

**Fail — no mermaid fence** (prose-only pipeline description):
```json
[{"id": "c1-mermaid-fence-in-pipeline-md", "passed": false, ...},
 {"id": "c2-diagram-type-declared", "passed": false, ...},
 {"id": "c3-no-bare-reserved-end-node-id", "passed": false, "evidence": "no bare `end` node identifier found"},
 {"id": "c4-nontrivial-chain", "passed": false, "evidence": "found 0 arrow connection(s) in the diagram (want >= 4)"},
 {"id": "c5-pipeline-source-untouched", "passed": true, ...}]
```

**Fail — pipeline.py modified** (appended a comment line):
```json
[{"id": "c1-mermaid-fence-in-pipeline-md", "passed": true, ...},
 {"id": "c2-diagram-type-declared", "passed": true, ...},
 {"id": "c3-no-bare-reserved-end-node-id", "passed": true, ...},
 {"id": "c4-nontrivial-chain", "passed": true, ...},
 {"id": "c5-pipeline-source-untouched", "passed": false,
  "evidence": "pipeline.py missing or modified (got '\"\"\"Simple ETL pipeline stages, executed in order: start, extract, transform, loa')"}]
```

Both check.py files also `python3 -m py_compile` cleanly.

## 3 · Two real bugs found and fixed during verification (not hypothetical — caught by running
against actual mock output)

1. **False positive on legitimate mermaid syntax.** My first version of the `c3` house-rule
   check in `add-architecture-diagram` used a flat `\[([^\]]*)\]` regex to extract "node label"
   content, which mis-captured the skill's own documented `[(database)]` cylinder shape (e.g.
   `DB[(Primary Datastore)]`, straight from SKILL.md L47's `DB[(Postgres)]` example) as if the
   structural `(` `)` were forbidden label content. Fixed by peeling shape delimiters
   (database/circle/stadium/subroutine/diamond/box/rounded, longest-first) out of a working
   copy before checking residual content for forbidden chars, so only genuine label text is
   checked, not shape syntax. Verified with a dedicated "shapes" mock workspace (§2).
2. **False negative on tampered source.** `avoid-reserved-node-id`'s `c5` sentinel check
   originally used `str.startswith(expected_docstring_prefix)` against `pipeline.py`, which is
   blind to any tamper appended *after* the docstring (e.g. `echo "# tampered" >> pipeline.py`
   still starts with the expected prefix). Fixed by comparing full-file content equality against
   the exact fixture bytes (verified byte-for-byte match against the actual fixture file before
   using it as the hardcoded expected string).

Both fixes are already applied in the committed check.py files above — the pass/fail outputs in
§2 are post-fix.

## 4 · Case loading verified

```
$ uv run --project harness python3 -c "
from agent_harness.cases import load_cases
cases = load_cases('mermaid', 'harness/cases')
print([c['id'] for c in cases])"
['add-architecture-diagram', 'avoid-reserved-node-id']
```

Note: `agent_harness.cases.load_cases` signature is `load_cases(candidate, cases_dir,
only=None)` (candidate first, cases_dir second) — the brief's illustrative call order
(`load_cases('harness/cases', 'mermaid')`) doesn't match `cases.py`'s actual signature; I used
the real one. Both `case.json` files also parse standalone via `json.load`.

## 5 · Scope discipline

Touched only `harness/cases/mermaid/**` and this handoff file. Did not touch adapters, core,
other candidates' case dirs (`harness/cases/readme-value-and-proof/`, `harness/cases/scout/` —
both present as untracked siblings, not mine), `primitives-core/` (read-only), or `evals/`
(untracked residue, pre-existing, not mine). No git mutations. No `.claude/agent-memory/`
writes — I found a pre-existing `.claude/agent-memory/` directory with content from other
sessions; I did not add to it. Cleaned up `__pycache__` litter that `python3 -m py_compile` /
direct execution left inside my own case dirs during verification before finishing.

## 6 · Deferred / out of scope

- No live grid run (`with` vs `baseline` × trials) — Wave 3 criteria call for this at the
  reconciliation/full-grid stage once Wave 2 (opencode adapter) lands; case authoring here is
  data-only per the brief.
- The `c3-no-bare-reserved-end-node-id` regex family in `avoid-reserved-node-id` is a heuristic,
  not a real mermaid parser. It's deliberately narrow (only flags `end` in identifier position:
  adjacent to shape delimiters or arrows) to avoid false-flagging `end` as ordinary label text,
  and was verified against both the "pass" (renamed-id) and "fail" (bare-id) constructed
  outputs, but a sufficiently adversarial diagram (e.g. one that uses `subgraph ... end` to
  legitimately close a subgraph block immediately adjacent to an arrow on the same line) could
  in principle evade or false-positive it. Not exercised by either fixture since neither prompt
  invites subgraphs.
- Did not add a third case (brief allows 1–2); two was judged sufficient coverage of the skill's
  two most concretely-testable, most consequential rules (house rule + reserved-word pitfall).
  The skill's other content (light/dark theming, mermaid-cli rendering, diagram-type selection)
  is either not deterministically checkable from a single trial workspace (theming is a
  stylistic preference, not a hard syntax rule) or already indirectly exercised (`c2` in both
  cases checks diagram-type declaration).
