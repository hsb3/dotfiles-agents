# Extender-DB — Project Charter

_The canonical page for the extender-db mini-project. If anything disagrees with this page,
this page wins; change it only here._
Status: active · 2026-07-20

## Mission

Build a queryable database of the agent extenders this repo distributes or curates — their
content, structure, provenance, and packaging — **joined to the mental models used to compose
and evaluate them**, so that organizing, monitoring, and improving the catalog becomes a
matter of querying and assessing rather than re-reading files.

Two halves, deliberately in one store:

1. **Inventory** — what each extender IS: frontmatter dimensions, file inventory with full
   content, size metrics, roster provenance, distribution membership.
2. **Doctrine** — the frameworks we compose and judge by: published specs (Anthropic Agent
   Skills, Claude Code subagents), internal archetype sets and section taxonomies, this
   repo's own roster schema. Doctrine is data, with provenance and status, so competing
   frameworks can be compared against the same catalog and superseded without loss.

The join is `assessments`: extender × framework-element × assessor verdicts, so "how well
does our catalog conform to X" and "compose a new skill in the shape our best ones share"
are both queries.

## Scope

- **Seed (this phase):** skills and agent personas from `primitives-core/`, the initial seeded
  frameworks, mechanical assessments.
- **Committed expansion:** hooks, MCP servers, commands (`extenders.kind` and vocabularies
  already carry them); externals by reference; judged (non-mechanical) assessment passes;
  **evaluation provenance** (added 2026-07-20: `eval_runs` + `eval_responses` store each
  campaign's method, criteria, exact prompts, and raw agent responses, with every
  assessment row linked to its run). Doctrine has since grown to **9 frameworks** (incl. the
  `hsb3-jobs-to-be-done` taxonomy and the adopted `skillopt` / `closedloop-judges` eval
  methodologies) and a **`sources`** trusted-publisher registry (2026-07-20).
- **Store:** PocketBase, local, single-machine, superuser-only. The database file
  (`pb_data/data.db`) is tracked in git (decision 4, revised 2026-07-20); transient siblings
  (request logs, WAL/SHM, typings) are ignored, and everything needed to rebuild from
  scratch (schema, ingest, seeds) is tracked regardless.

## Non-goals

- **Not a source of truth.** The repo is. The database is a rebuildable projection; content
  is never edited in the DB and never flows back. If a query surfaces a problem, the fix
  lands in `primitives-core/` (or the roster) and gets re-ingested.
- **Not part of the distribution.** No marketplace artifact, no `make ci` lane, no runtime
  dependency of any shipped primitive — until promotion explicitly decides otherwise.
- **Not multi-user / not networked.** No public API rules, no auth story beyond the local
  superuser. Revisit only at promotion.

## Operating model

- **Idempotence is a hard invariant.** `schema.py` and `ingest.py` re-run safely; a re-run
  against an unchanged tree creates zero records. Schema updates merge by field name and
  preserve field ids (a field sent without its id is dropped-and-recreated by PocketBase —
  data loss).
- **Assessor discipline.** `assessor` separates regenerable machine verdicts
  (`mechanical-v1`, owned and rewritten by ingest) from judgment verdicts (humans or review
  agents, any other assessor value, never touched by ingest). Unique index
  (extender, framework, element, assessor) lets them coexist.
- **Doctrine is append-and-supersede.** A framework proven wrong or replaced gets
  `status: superseded` and a successor row with its own citation — never overwritten.
- **Secrets discipline.** Credentials live in `_meta/operations/extender-db.env`
  (untracked). Nothing under `evals/` may contain a plaintext secret. Known
  exception, accepted: the tracked `data.db` contains the bcrypt hash of the superuser
  password (random 32-hex, localhost-only service, private repo). If the repo ever goes
  public, rotate the superuser and strip `data.db` from history first.

## Decisions

| # | Decision | Why |
|---|---|---|
| 1 | PocketBase as the store | Single binary, zero-infra, admin UI for browsing, REST API scriptable from stdlib Python — matches the repo's zero-install posture. |
| 2 | Projection, not source of truth | The repo already has manifest + drift-guard machinery; duplicating authority would create a second truth to reconcile. |
| 3 | Doctrine modeled as data (frameworks/elements), not code | The point is analyzing the catalog BY competing mental models; models must be comparable, citable, and supersedable. |
| 4 | Lives at root `evals/`; `pb_data/data.db` tracked, transient siblings ignored | _Revised 2026-07-21 (owner decision): re-housed from `_meta/extender-db/` to root `evals/` — promoted from desk tooling to a first-class home for the eval infrastructure._ _Revised 2026-07-20: originally the whole `pb_data/` was gitignored as machine-local; small size (~6 MB) and a private repo make committing the live DB worth it so state travels with the repo. `auxiliary.db` (request logs), WAL/SHM, and typings stay ignored._ Originally desk tooling (ADR-0006 track-by-default), not a shipped artifact. |
| 5 | Mechanical vs judged assessments split by `assessor` | Regeneration must never destroy judgment; judgment must never block re-ingest. |
| 6 | **Adopt external eval methodology, don't build a bespoke harness** (2026-07-20) | Mature, permissively-licensed frameworks now exist (SkillOpt MIT, ClosedLoop Apache-2.0). Extends "don't author each extender from scratch" up to the eval harness itself; reserves our build for the IP only we have (job taxonomy, coverage, curation decisions). Defers EDB-14 bespoke agents further. |
| 7 | **Two complementary adopted methodologies, by eval question** (2026-07-20) | Qualitative "does extender X meet the bar" → the ClosedLoop judges+CaseScore rubric pattern (maps onto our `assessments`; W1 is a lighter version). Quantitative "how good is skill X / can we improve it" → SkillOpt (authored task set + checkable reward + validation-gated edit). Recorded as frameworks `closedloop-judges` / `skillopt`. |
| 8 | **Cheap-model substrate + reused harness for evals** (2026-07-20) | Comparative + improvement evals run on inexpensive/free models. Layers: *methodology* is adopted (SkillOpt scoring/gating + ClosedLoop judges); *execution* is **reused — Henry already has a meta-harness for testing across opencode + other coding-agent harnesses, so we do NOT build one** (decision 6 applies to the harness too; ~~likely the EDB-14 code~~). Any CC extender ports to opencode (hooks the main translation gap — covered by our `opencode-expertise`), enabling faithful *agentic* eval of CC skills on cheap/free models through that harness. _**Resolved 2026-07-22 (owner ruling):** the reused meta-harness is the root **`harness/`** in THIS repo (delivered PR #169) — realized in-repo, not a separate repo. It drives Claude Code or opencode headlessly against fixtures, the exact EDB-14/19 execution layer. M5/#165 now routes through it (EDB-14 resolved; EDB-19's wiring is #165)._ |
| 9 | **Per-job disposition lives in a new `job_coverage` collection** (2026-07-20, Henry signed off) | The EDB-13 deferred decision. Disposition (`author/vendor/reference/compare`) + coverage status + chosen `sources` link is per-JOB, not per (extender × job), so it doesn't fit `assessments`. A first-class collection stays queryable, carries its own provenance, and can be re-decided without disturbing the candidate taxonomy — the "doctrine/curation as data" spirit. M3 combine/coalesce reads it directly. Rejected: fields on `framework_elements` (mixes mutable curation into candidate doctrine) and a field on `assessments` (wrong granularity — duplicated ~37×). |
| 10 | **Pairwise relationships live in a new `relationships` collection** (2026-07-20, Henry signed off; extended for direction) | Links between two extenders had no home. A pair collection (`extender_a`, `extender_b`, `kind`, overlap `job`, `evidence`, `assessor`, `eval_run`) keeps them queryable so M3 can select "all duplicative pairs" as data. `kind` carries symmetric values (duplicative/conflicting/complementary) **and directional ones (`precedes`/`feeds-into`, read A→B)** — directed compositions (lifecycle ambition) need ordering, so the hand-off links are the planner's raw material. Rejected: encoding pairs in assessment evidence/notes (prose, not queryable). |

## Lifecycle ambition (added 2026-07-20)

The retrofit (evaluating the existing collection) is the seed of a larger loop. The target
is three workflows, each ending in the same evaluate→use tail:

1. **Create → evaluate → use** — author a new extender against the frameworks, evaluate it
   before it ships, track it in use.
2. **Curate → evaluate → use** — bring an external extender in by reference, evaluate it
   against the same bar as authored ones.
3. **Combine/coalesce → evaluate → use** — merge overlapping extenders or compose
   complementary ones, and prove the composite earns its place.

Two standing questions those workflows must answer, both as data in this database:

- **Quality evidence** — "how good is this skill, and why use it over the first search hit
  on skills.sh?" Answered by (a) experimental/comparative data (`eval_runs` of kind
  `comparative`/`experiment`: same job, our skill vs baseline vs external alternative) and
  (b) adherence evidence — conformance to frameworks that carry their own citations.
- **Portfolio analysis** — do we have coverage for the jobs we need done? Which extenders
  are duplicative, conflicting, or deliberately complementary? Modeled as a
  jobs-to-be-done framework plus pairwise relationship data, so coverage gaps and overlaps
  are queries, not impressions.

**Directed compositions — the "use" surface (emerging 2026-07-20).** The three workflows
compose *individual* extenders; the payoff is composing them into **directed
compositions** — an ordered, branching set of extenders for a given goal *and context*
(making a deck may also pull in research and disambiguation, or not — it depends what you
start with). These are **not static recipes**: a **grounded planner** (a smart model —
Fable/Opus — reasoning over this DB's coverage map, directional `relationships`, and each
tool's trigger/output) assembles the composition at request time, and the planner is
itself an extender (its job is *pick the extenders*). Compositions are **living** —
periodically tested against outcomes and updated, the evaluate→improve loop one level up
from a single extender. **Future direction, deferred (EDB-22):** the testing/update
infrastructure for directed compositions is out of scope until the coverage substrate (M1)
and eval milestones (M4–M6) are solid; noted so it isn't lost. Near-term enabler: M1
captures what a planner needs — coverage, directional hand-off links, per-tool
trigger/output.

Applies to all extender kinds, not just skills. Related but deferred: Henry has built-in
agent code in another repo that could power the evaluation harness — integration is out of
scope until the retrofit is solid (EDB-14).

**Strategy for the "evaluate" half (2026-07-20, decisions 6–8):** we do NOT build a bespoke
eval harness. We **adopt** two external, permissively-licensed methodologies — the ClosedLoop
judges+CaseScore rubric pattern for qualitative conformance (it maps onto our `assessments`)
and Microsoft SkillOpt for quantitative "how good / can we improve," run on cheap/free models.
Both were read at source before adoption. Our build stays on the IP only we have: the job
taxonomy, coverage/portfolio analysis, and the curation decisions.

## Roadmap (2026-07-20)

Two tracks; milestones (deliverables + acceptance, no timelines) detailed in
[PLAN.md](PLAN.md). Track I is our IP; Track II adopts external machinery.

**Track I — Portfolio & curation (our IP):**
- **M1** — W9 mapping body: 37 extenders → 24 jobs, pairwise relationships, coverage matrix, per-job dispositions.
- **M2** — W4 analysis surface: `report.py` + canned queries/views.
- **M3** — Combine/coalesce: act on the overlaps/gaps the matrix surfaces (first real curation actions).

**Track II — Evaluation & improvement (adopt external):**
- **M4** — Doctrine: `skillopt` + `closedloop-judges` frameworks loaded (done); formalize our judge+rubric+CaseScore conformance pattern.
- **M5** — W8 first comparative eval on ONE skill: authored SkillOpt benchmark (task set + checkable reward), with-skill vs without vs a skills.sh / trusted-publisher alternative, on cheap models, executed through Henry's existing meta-harness (reuse, not build).
- **M6** — Self-improvement loop prototype (create→evaluate→improve→use) on one skill, using SkillOpt's gated edit / `skillopt_sleep` + ClosedLoop `self-learning` as references. Acceptance: a measured before/after eval delta, human-in-the-loop adopt. Gated behind M4+M5.

**External references (inspiration, not DB rows):** microsoft/hve-core (rigorous CI/CD
validation-standards process, though for GitHub Copilot — an adjacent ecosystem) and
karpathy/autoresearch (the canonical closed-loop self-improvement pattern: modify → evaluate →
keep/discard → repeat) inform M4/M6 without being extender publishers we'd vendor from.

## Promotion gate

"Satisfied" means all of the following, checked against the database itself:

- [x] A judged assessment pass exists for every skill (primary archetype + section-taxonomy
      coverage) and survived spot verification. _(W1, 2026-07-20 — 6 judges + 2 blind
      reviewers + session adjudication; see PLAN W1 DONE.)_
- [x] At least one expansion kind (hooks) is ingested end-to-end with its own framework and
      mechanical checks. _(W2, 2026-07-20 — see PLAN W2 DONE.)_
- [x] The database has answered ≥3 real curation questions that changed something in the
      repo (recorded in OPEN-ITEMS.md as findings → actions). _(6 landed by 2026-07-21:
      EDB-9 → obsidian-cli fix (#160); M1 gap research-question → deep-research authored
      + rostered (#155); M1 gap produce-dataviz → dataviz (#156); M1 partial
      configure-harness → update-config (#157); M1 partial migrate-at-scale → foreman
      playbook (#158); M1 duplicative relationship → coleam00 dropped from externals.yaml
      (#159, EDB-16b). See OPEN-ITEMS EDB-9/EDB-16/EDB-25.)_
- [x] Re-ingest after a real catalog change (new/edited skill) proved the update path, not
      just the create path. _(2026-07-21, #160 — obsidian-cli EDB-9 fix re-ingested:
      `extender updated: skill/obsidian-cli`, row id unchanged (`hbt6ac5r9sjkoji`),
      count 37→37, judgment rows untouched; see OPEN-ITEMS EDB-9 Resolved entry.)_

Promotion itself is a separate decision with its own options (stay a `_meta` desk tool ·
graduate scripts into `scripts/` with a make lane · extract to its own repo) — recorded here
when made, not presumed now.

## Where things are

| File | Role |
|---|---|
| `_structure/CHARTER.md` | This page — canonical; precedence over all other project docs. |
| `_structure/PLAN.md` | Deliverables · acceptance criteria · parallelism (no timelines). |
| `_structure/OPEN-ITEMS.md` | The project's issue tracker — open items, findings, resolved log. |
| `_structure/INSIGHTS.md` | Running log of insights/observations — feeder material for the comprehensive docs. |
| `README.md` | Operator doc: data model reference + how to run (folder root). |
| `pb.py` / `schema.py` / `ingest.py` / `load_*.py` / `serve.sh` | The tool (folder root). |
