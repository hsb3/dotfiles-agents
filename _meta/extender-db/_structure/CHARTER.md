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

- **Seed (this phase):** skills and agent personas from `primitives-core/`, the five seeded
  frameworks, mechanical assessments.
- **Committed expansion:** hooks, MCP servers, commands (`extenders.kind` and vocabularies
  already carry them); externals by reference; judged (non-mechanical) assessment passes.
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
  (untracked). Nothing under `_meta/extender-db/` may contain a plaintext secret. Known
  exception, accepted: the tracked `data.db` contains the bcrypt hash of the superuser
  password (random 32-hex, localhost-only service, private repo). If the repo ever goes
  public, rotate the superuser and strip `data.db` from history first.

## Decisions

| # | Decision | Why |
|---|---|---|
| 1 | PocketBase as the store | Single binary, zero-infra, admin UI for browsing, REST API scriptable from stdlib Python — matches the repo's zero-install posture. |
| 2 | Projection, not source of truth | The repo already has manifest + drift-guard machinery; duplicating authority would create a second truth to reconcile. |
| 3 | Doctrine modeled as data (frameworks/elements), not code | The point is analyzing the catalog BY competing mental models; models must be comparable, citable, and supersedable. |
| 4 | Lives under `_meta/extender-db/`; `pb_data/data.db` tracked, transient siblings ignored | Desk tooling (ADR-0006 track-by-default), not a shipped artifact. _Revised 2026-07-20: originally the whole `pb_data/` was gitignored as machine-local; small size (~6 MB) and a private repo make committing the live DB worth it so state travels with the repo. `auxiliary.db` (request logs), WAL/SHM, and typings stay ignored._ |
| 5 | Mechanical vs judged assessments split by `assessor` | Regeneration must never destroy judgment; judgment must never block re-ingest. |

## Promotion gate

"Satisfied" means all of the following, checked against the database itself:

- [ ] A judged assessment pass exists for every skill (primary archetype + section-taxonomy
      coverage) and survived spot verification.
- [ ] At least one expansion kind (hooks) is ingested end-to-end with its own framework and
      mechanical checks.
- [ ] The database has answered ≥3 real curation questions that changed something in the
      repo (recorded in OPEN-ITEMS.md as findings → actions).
- [ ] Re-ingest after a real catalog change (new/edited skill) proved the update path, not
      just the create path.

Promotion itself is a separate decision with its own options (stay a `_meta` desk tool ·
graduate scripts into `scripts/` with a make lane · extract to its own repo) — recorded here
when made, not presumed now.

## Where things are

| File | Role |
|---|---|
| `_structure/CHARTER.md` | This page — canonical; precedence over all other project docs. |
| `_structure/PLAN.md` | Deliverables · acceptance criteria · parallelism (no timelines). |
| `_structure/OPEN-ITEMS.md` | The project's issue tracker — open items, findings, resolved log. |
| `README.md` | Operator doc: data model reference + how to run (folder root). |
| `pb.py` / `schema.py` / `ingest.py` / `serve.sh` | The tool (folder root). |
