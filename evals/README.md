# extender-db — PocketBase inventory of agent extenders

_Internal analysis tool: a queryable database of this repo's agent extenders (their content,
structure, and packaging) plus the mental models used to compose and evaluate them._
Status: active (covers skills, agent personas, hooks, and externals-by-reference).

This is a mini-project — the project docs live in `_structure/`:
[CHARTER.md](_structure/CHARTER.md) is the canonical page (mission, scope, decisions, roadmap,
promotion gate), [PLAN.md](_structure/PLAN.md) carries deliverables/criteria/milestones,
[OPEN-ITEMS.md](_structure/OPEN-ITEMS.md) is the issue tracker, and
[INSIGHTS.md](_structure/INSIGHTS.md) is the running log of learnings feeding the eventual
comprehensive docs. This README is the operator doc; **[PROCEDURES.md](PROCEDURES.md) is
the runbook** — script run order, the evaluated-pass pattern, gates, and the data.db
commit discipline. Read it before running anything beyond serve/schema/ingest.

The repo itself stays the source of truth — this database is a **projection for analysis**,
rebuilt at any time by re-running the ingest. Never edit extender content here and expect it
to flow back; edit `primitives-core/` and re-ingest.

## Run it

```sh
evals/serve.sh             # server + admin UI (env-configured, see below)
python3 evals/schema.py    # create/update collections (idempotent)
python3 evals/ingest.py    # scan repo + seed frameworks (idempotent upserts)
```

Configuration resolves from env vars first, then `_meta/operations/extender-db.env`
(untracked), then defaults: `PB_DATA_DIR` (data directory; default
`evals/pb_data`), `PB_URL` (default `http://127.0.0.1:8090`),
`PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` (superuser, no default). PocketBase itself only
takes the data dir as a `--dir` flag — `serve.sh` is the env-var surface, and forwards any
other subcommand with `--dir` appended (e.g. `serve.sh superuser upsert EMAIL PASS`). The
live database is tracked in git as `pb_data/data.db` (private repo, ~6 MB); the rest of
`pb_data/` — request logs (`auxiliary.db`), WAL/SHM journals, generated typings — is
transient and stays ignored. Stop the server before committing so the WAL is checkpointed
into `data.db`.
Admin UI: <http://127.0.0.1:8090/_/>. All collections are superuser-only (no public API rules).

## Data model

Two halves, joined by `assessments`: the **inventory** (what the extenders ARE) and the
**doctrine** (the mental models we compose and judge them by).

```mermaid
erDiagram
    extenders ||--o{ files : "file inventory"
    sources ||--o{ extenders : publishes
    distributions }o--o{ extenders : members
    frameworks ||--o{ framework_elements : contains
    extenders ||--o{ assessments : "judged by"
    framework_elements ||--o{ assessments : "against"
    frameworks ||--o{ frontmatter_dimensions : "spec source"
```

### Inventory side

| Collection | One row per | Key fields |
|---|---|---|
| `extenders` | extender (skill or agent persona) | `slug` (unique, = roster id), `kind`, `description`, roster provenance (`origin`, `upstream`, `upstream_ref`, `shelf`, `disposition`, `requires`), `frontmatter` (parsed JSON), `body` (entrypoint markdown minus frontmatter), size metrics (`file_count`, `total_bytes`, `word_count`) |
| `files` | file inside an extender | `relpath`, `role` (entrypoint / reference / script / asset / template / eval / doc / license / config / other), full `content` (text files), `sha256`, `size_bytes`, `language`, `is_binary` |
| `distributions` | packaging unit | `slug`, `kind` (bundle / plugin / standalone), `version`, `members` (relation → extenders). From `plugins.yaml` + `skill-catalog.yaml`. |
| `frontmatter_dimensions` | (kind, frontmatter key) pair | `requirement` (required / optional / harness / custom / deprecated), `observed_count` across the catalog, `spec_framework` (which doctrine defines it). The custom rows are the interesting ones — keys we use that no spec defines. |
| `sources` | a trusted **publisher** of extenders | `slug`, `publisher_kind` (first-party / marketplace / individual / research-lab / community-collection), `publishes` (which kinds), `trust_tier` (trusted / provisional / watch / avoid), `publishes_evals`, `maintenance`, `license`, `adoption_signal`, cited `rationale` + `evidence_url`. Curated from research (EDB-15). `extenders.source` links each external to its publisher; the tier decides eligibility to vendor / reference / use as a W8 comparator baseline. |

### Doctrine side (the mental models)

| Collection | One row per | Key fields |
|---|---|---|
| `frameworks` | a named mental model | `kind` (archetype-set / section-taxonomy / authoring-spec / schema-spec / evaluation-rubric / principles), `source_org` + `source_url` (provenance: Anthropic-published vs internal), `applies_to`, `status` (active / candidate / superseded) |
| `framework_elements` | archetype, section, component, rule, or principle within a framework | `element_kind`, `description`, `criteria` (how a judge decides presence), `sort_order` |
| `eval_runs` | one evaluation campaign | `kind` (mechanical / judged / adversarial-review / adjudication / comparative / experiment), `method` (how it was designed and executed), `criteria_text` (the full criteria document), `frameworks`, `status` |
| `eval_responses` | one agent's contribution to a run | `role` (unique per run), `agent_type`, `model`, `prompt` (the exact dispatch text), `response_text` (verbatim final message), `response_json` (parsed verdicts), `extenders` covered, `tokens`, `duration_ms` |
| `assessments` | one verdict: extender × framework element × assessor | `verdict` (present / partial / absent / not-applicable), `evidence`, `score` (optional), `assessor`, `eval_run` (provenance link — every verdict resolves to the run, prompt, and response that produced it) |

**Assessor discipline:** `assessor` distinguishes who judged. `mechanical-v1` rows are
regenerated by `ingest.py` (checkable-by-code rules only: frontmatter presence/length,
SKILL.md line counts, bundled-resource dirs). Judgment calls — archetype tagging, section
taxonomy, "is this single-responsibility" — are written by humans or review agents under a
different assessor value and are never touched by the ingest. The unique index is
(extender, framework, element, assessor), so mechanical and judged verdicts coexist per element.

### Seeded frameworks

| Slug | Kind | Source | What it captures |
|---|---|---|---|
| `anthropic-agent-skills` | authoring-spec | Anthropic docs | SKILL.md entrypoint, name/description rules, progressive disclosure, references/scripts/assets, concise-body guideline |
| `claude-code-subagents` | schema-spec | Anthropic docs | Persona frontmatter (name/description/tools/model), system-prompt body, single responsibility |
| `hsb3-skill-archetypes` | archetype-set | internal (candidate) | What a skill fundamentally is: workflow-procedure, domain-expertise, deliverable-producer, guardrail-override, orchestration-delegation, scaffold-auditor |
| `skill-section-taxonomy` | section-taxonomy | internal (candidate) | Recurring SKILL.md section types (trigger, prerequisites, workflow steps, anti-patterns, output contract, integration partners, …) |
| `hook-dir-layout` | schema-spec | this repo | The ratified `hooks/<name>/hook.py` layout (`scripts/check_hook_layout.py`): Python-only handler, stdlib-only imports, co-located config |
| `dotfiles-agents-roster-schema` | schema-spec | this repo | The `primitives-core.yaml` entry schema (shelf, origin/provenance rule, disposition, membership, requires) |
| `hsb3-jobs-to-be-done` | job-taxonomy | internal (candidate) | The jobs Henry's agent work needs done (deliverable altitude, all-work scope), grouped by `category` into 7 families; 24 solution-agnostic job elements. W9 maps every extender to the jobs it serves |
| `skillopt` | evaluation-methodology | Microsoft (candidate) | Adopted quantitative eval+improvement method: skill-as-trainable-state, scored rollouts, validation-gated edits, cheap-model substrate, transcript-mined improvement. For W8/M5/M6 |
| `closedloop-judges` | evaluation-methodology | ClosedLoop.AI (candidate) | Adopted qualitative conformance pattern: judge-as-prompt-with-rubric emitting a CaseScore verdict, lightweight `{id,input,expected_outcome}` eval cases, a self-learning feedback loop. Maps onto our `assessments` |

If Anthropic later publishes a canonical archetype set, add it as a NEW framework row with
its citation and mark the internal one `superseded` — don't overwrite; comparing frameworks
against the same catalog is the point of the model.

## Example questions it answers

- Which skills exceed the concise-body guideline? → `assessments` where element
  `concise-body` and verdict ≠ present (currently: diagrams 653 lines, obsidian-cli 753 lines).
- What frontmatter keys do we use that no spec defines? → `frontmatter_dimensions` where
  `requirement = custom` (currently: skill `metadata`/`version`, agent `memory`).
- Which skills ship scripts vs pure-prose? → `files` grouped by `role`.
- Coverage of a bundle: `distributions.members` expanded against assessments.

## Expansion path

- **Kinds:** `extenders.kind` and the dimension/framework vocabularies already carry
  `hook`, `mcp`, `command` — adding hooks/MCP servers is an ingest pass, not a schema change.
- **Externals:** third-party references in `externals.yaml` fit `extenders` with
  `origin = external` (no files ingested, upstream URL only).
- **Versioning over time:** if trend analysis is wanted later, snapshot `sha256`/metrics
  per git ref into a new `snapshots` collection rather than mutating rows.

## Files

- `pb.py` — minimal stdlib REST client (superuser auth, upsert helpers)
- `schema.py` — collection definitions; safe to re-run (merges by field name, preserves ids)
- `ingest.py` — repo scan + framework seeds + mechanical assessments; safe to re-run
- `load_eval_run.py` — manifest-driven loader for evaluation provenance (runs, prompts, responses)
- `load_assessments.py` — judged/review verdict loader (W1-style passes)
- `load_coverage.py` — coverage-mapping loader: full extender × job cross product, assessor `coverage-v1`
- `render_matrix.py` — regenerates `coverage-matrix.md` from the DB (generated file — never hand-edit)
- `serve.sh` — env-configured server wrapper (`PB_DATA_DIR`, `PB_URL`)
- `PROCEDURES.md` — the runbook: run order, evaluated-pass pattern, gates, commit discipline
- `DECISIONS-NEEDED.md` — open owner-decision batch (tracked as issue #153)
- `_structure/` — project docs: CHARTER, PLAN, OPEN-ITEMS, INSIGHTS
- `pb_data/` — the live database; only `data.db` is tracked (logs/journals/typings ignored)
