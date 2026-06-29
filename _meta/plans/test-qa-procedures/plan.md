# Test/QA procedures for the translation service

_The repo's only automated checks today are two **drift guards** (`make ci`). They prove the
committed `targets/` equals a fresh rebuild and the roster matches disk -- i.e. **consistency**.
They do **not** prove the rebuild is **correct**: a render bug emits wrong-but-consistent output
that passes `make ci` clean. This plan adds the correctness layer -- unit tests for the pure
render/transform/parse logic, content+schema validation of source primitives and generated
artifacts, and two invariant gates (determinism, secret hygiene) -- all stdlib-only so CI stays
zero-install. Loadability against the real tools is scoped but deferred (D)._

Status: draft
Date: 2026-06-29

## Tracking

No issue yet (origin: Henry, "this repo needs some test/qa procedures -- please plan those out",
2026-06-29). Staged with `issue-body.md` for publication. Suggested labels: `type:harden`,
`area:cli`. Not an epic (single coherent capability), though D could spin into a follow-up.

**Contract impact:** none on a runtime API/DB. Touches the build's *source-of-truth surface* only
by adding gates that read it. The CMA payload shape (D) cites the pinned contract in
`CANON.md` ("Resolved -- managed-agents (CMA) contract") and the OpenAPI spec it was pinned from.

## The problem (grounded in source)

What EXISTS today (the consistency layer):
- `make ci` = `check` + `build-check` (`Makefile:21`). CI runs only `make ci`
  (`.github/workflows/ci.yml`), Python 3.13, **no `pip install`** -- the suite is zero-install by
  design (`scripts/translate.py:14` "Stdlib-only ... so it runs in CI with zero install").
- `scripts/check_roster.py` (roster<->disk): checks required fields present (`REQUIRED`,
  `check_roster.py:25`), `type in {skill,agent,mcp,hook}` (`:23,:98`), `shelf in {core,toggle}`
  (`:24,:100`), each `source` exists on disk (`:97`), and no disk orphans (`disk_primitives`,
  `:55`). It does NOT validate `origin` values, `targets` membership, or any primitive's CONTENT.
- `scripts/translate.py --check` (`main`, `:594`): rebuilds to a temp dir and `diff_trees`
  (`:569`) against committed `targets/`, plus a results-lock equality check. Proves committed ==
  rebuild; says nothing about whether the rebuild is correct.

What is MISSING (the correctness layer):
- **No unit tests of the pure functions.** `translate.py` has highly testable, side-effect-free
  logic with zero coverage: the renderers `mcp_to_claude` (`:242`), `mcp_to_opencode` (`:258`),
  `mcp_to_cma` (`:275`); the transforms `transform_agent_opencode` (`:189`), `agent_system`
  (`:211`), `skill_display_title` (`:220`); the five tailored stdlib parsers `parse_roster`
  (`:54`), `parse_externals` (`:80`), `parse_plugins` (`:107`), `parse_capabilities` (`:122`),
  `parse_cma_options` (`:143`); plus `_list` (`:46`) and `sha256_path` (`:169`). The mcp stdio/http
  branches were checked by hand during the mcp build but that proof is not committed as a test.
- **No content/schema validation of SOURCE primitives.** Nothing asserts a skill has a `SKILL.md`
  at its root with `name`+`description` frontmatter, an agent `.md` has frontmatter, or an mcp spec
  has the required fields per transport (`stdio`=>`command`, `http`=>`url`). `check_roster` only
  checks the `source` path exists, not its shape.
- **No validation that GENERATED artifacts match each target's real schema.** The drift guard
  compares bytes to the committed copy; it never checks that a CMA payload has `name`+`model`
  (the two `BetaManagedAgentsCreateAgentParams` requireds), that a `targets/*/mcp/*.json` matches
  the CC `mcpServers` / opencode `mcp` shape, or that `marketplace.json` carries its required keys.
- **No determinism test as a named assertion.** `--check` covers committed-vs-rebuild; nothing
  asserts rebuild-vs-rebuild byte-identity (true idempotency).
- **No secret-hygiene gate.** Nothing fails the build if a literal token leaks into `targets/`
  instead of a `${VAR}` placeholder. This was verified by hand for the github mcp server during the
  externals work; it is not a standing gate.
- **No test infra at all:** no `tests/`, no `make test`, no framework, no test lane in CI.

## Deliverables

### A -- test harness + unit tests for the pure functions
Stand up `tests/` with a stdlib runner (see Q1), a `make test` target, and a CI step. Unit-test the
side-effect-free logic in both scripts:
- **Renderers** -- `mcp_to_claude` / `mcp_to_opencode` / `mcp_to_cma`, each asserted for BOTH a
  `stdio` spec and an `http` spec (the exact shapes: CC `type:stdio`/`http`; opencode
  `type:local` with `command` as one array / `type:remote`; CMA `mcp_servers[].type:url`).
- **Transforms** -- `transform_agent_opencode` drops `name`/`model`/`color`, adds `mode: subagent`,
  and preserves a multi-line `description` byte-for-byte; `agent_system` strips frontmatter;
  `skill_display_title` extracts `name` and falls back to the dir name.
- **Parsers** -- each of the five parsers round-trips the real repo file (asserts a known entry
  parses) plus synthetic edge cases (empty `primitives: []`, bracketed `targets`, inline-comment
  values, missing optional fields).
- **Primitives** -- `_list` ([], [a, b], single); `sha256_path` is stable for a dir regardless of
  walk order and excludes `.DS_Store`/`__pycache__`.
- **File scope:** `tests/test_translate.py`, `tests/test_check_roster.py`, `tests/README.md`,
  `Makefile` (`test` target), `.github/workflows/ci.yml` (test step). Fixtures live UNDER `tests/`,
  never in `primitives-core/` (or `check_roster` flags them as orphans -- see Gates).
- **Acceptance:** `make test` runs green with zero `pip install`; every renderer has a stdio AND an
  http assertion; a deliberately mutated expectation (e.g. flip opencode `command` to a string)
  makes the suite fail; CI runs `make test`.

### B -- source-primitive content validation (`scripts/validate_primitives.py` + `make validate`)
A new stdlib guard (house style: a `scripts/*.py` with `--json` and a non-zero exit, like
`check_roster`) that validates primitive CONTENT, which the existing guards do not:
- **skill:** `SKILL.md` at the source root with frontmatter `name`+`description`.
- **agent:** `.md` has frontmatter with `name`+`description`.
- **mcp:** spec JSON has `name` and `transport in {stdio,http}`; `stdio`=>`command` present,
  `http`=>`url` present; any `env`/`headers` value that looks secret-bearing is a `${VAR}`
  placeholder, not a literal.
- **roster cross-checks `check_roster` omits:** `origin in {internal,external}`, `targets` is a
  subset of the three real targets, `summary` non-empty.
- **File scope:** `scripts/validate_primitives.py`, `Makefile` (`validate` target + fold into
  `ci`), `tests/test_validate_primitives.py` (drives it over good + broken fixtures).
- **Acceptance:** `validate_primitives.py` exits non-zero on a broken fixture (skill missing
  `description`; mcp spec missing `transport`) and zero on the real tree; `make ci` includes it;
  zero-install.

### C -- generated-artifact schema + invariant gates
The correctness checks the byte-diff guard cannot give, over the OUTPUT:
- **C1 artifact schema:** every `targets/*/mcp/*.json` parses and matches its target shape; every
  `targets/claude-agents/agents/*.json` has `name`+`model`+`system`; every skill `*.upload.json`
  has `endpoint`+`display_title`+`files`; `marketplace.json` and each `plugin.json` have their
  required keys.
- **C2 invariants:** **determinism** -- build to two temp dirs and assert byte-identical (stronger
  than `--check`); **secret hygiene** -- scan all of `targets/` and assert every `env`/`headers`
  secret value is a `${VAR}` placeholder, failing on a literal token.
- **File scope:** `tests/test_targets.py` (reads committed `targets/` + drives `build` into temp
  dirs). No `primitives-core/`/config edits.
- **Acceptance:** the determinism test builds twice and asserts equality; the secret scan passes on
  current `targets/` and fails on a fixture carrying a literal token; CMA `name`+`model` asserted
  across all `agents/*.json`.

### D -- loadability smoke tests (DEFERRED -- environment-dependent, opt-in)
Validate bundles against the ACTUAL tools where feasible, behind a `make smoke` that is NOT in the
required CI lane (it needs tools/network):
- **CMA:** validate `agents/*.json` against `BetaManagedAgentsCreateAgentParams` from the pinned
  OpenAPI spec (schema-level, no network) -- cite `CANON.md` CMA contract.
- **opencode / CC:** if the tool is installed, a config-parse / marketplace-schema smoke; **skip
  (not fail)** when absent, logging what was skipped (no silent caps).
- **Acceptance:** `make smoke` runs available checks and clearly skips the rest; never fails purely
  because a tool is missing. **Recommend deferring D to a follow-up issue** (Q4).

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (`make ci`) | YES | the plan ADDS lanes into it (`test`, `validate`); the point is they run on every PR |
| Roster drift guard (`make check`) | NO | no primitive added/removed -- PROVIDED fixtures live under `tests/`, not `primitives-core/` (else flagged as on-disk orphans, `check_roster.py:55`) |
| Targets drift guard (`make build-check`) | NO | no edit to `primitives-core/`, the roster, `plugins.yaml`, or the config; tests only READ `targets/` |
| YAML / workflow lint (`actionlint`/`yamllint`) | YES | editing `.github/workflows/ci.yml` to add the test/validate lane |
| Naming taxonomy (`manifests/naming.md`) | NO | adds no primitive/plugin (only `scripts/` + `tests/`) |
| CMA contract in `CANON.md` | KEEP IN SYNC (D only) | D validates against the pinned `BetaManagedAgentsCreateAgentParams`; amend the note if the asserted shape deviates |

## Parallelism + landing order

| Unit | Parallel with | Serializes on | Order |
| ---- | ------------- | ------------- | ----- |
| A unit tests | B, C (disjoint test files) | shared `Makefile` + `ci.yml` edits | 1 (establishes `tests/` + `make test`) |
| B validate guard | A, C | shared `Makefile` + `ci.yml` | 2 |
| C artifact/invariant | A, B | none beyond shared Makefile | 2 |
| Makefile + ci.yml wiring | none | the one shared pair of files | 3 (single owner integrates `test`+`validate` into `ci`) |
| D smoke (deferred) | independent | follows A-C | deferred / follow-up |

A establishes the harness first; B and C then build in parallel on disjoint files. The `Makefile`
and `.github/workflows/ci.yml` are the only SHARED files -- one owner makes the `test`+`validate`
wiring edits as the integration step, not parallel writers. D lands separately (or as a follow-up).

## Open questions / owner decisions

1. **Test framework.** Stdlib **`unittest`** (recommended -- preserves the zero-install CI;
   `python3 -m unittest`) vs **pytest via `uv`** (nicer DX, parametrization, but adds an install
   step to a suite that is deliberately install-free). *Default: `unittest`.*
2. **Gate shape.** Separate `make test` (unit/correctness) + `make validate` (source/artifact
   schema), BOTH folded into `make ci`; vs one combined target. *Default: separate, both in `ci`.*
3. **Validation as guard-script vs test.** Source/artifact VALIDATION as a `scripts/*.py` guard
   (matches `check_roster`'s house style, usable standalone, gates CI) while pure-logic UNIT tests
   live in `tests/`. *Default: split as described (B is a script; A and C are tests).*
4. **Scope D now or defer?** D (loadability) is environment-dependent and lower ROI than A-C.
   *Default: defer D to a follow-up issue; ship A-C.*
5. **New `gate:` label / required check?** Add a `gate:tested` label and/or a separate required
   check, or let the existing CI aggregate absorb the new lanes. *Default: no new gate; the `make
   ci` aggregate runs them.*

## Notes / flagged assumptions

- The "consistency vs correctness" framing is the load-bearing diagnosis -- verified against
  `Makefile:21`, `check_roster.py:55-100`, and `translate.py:594` (`--check` diffs committed vs
  rebuild). No guess.
- Whether `opencode`/`claude` expose a non-interactive config-validate command (D) is UNVERIFIED;
  treat D's tool-level checks as best-effort and skip-on-absent until confirmed.
