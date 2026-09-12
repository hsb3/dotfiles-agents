# extender-db — procedures & script run order

_Operator runbook: which script to run when, and the step-by-step procedures for the
recurring operations. Written 2026-07-20 from the W1 and M1 passes while the context was
hot. Secret-free (supply `PB_URL` / `PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` through the
environment; `.claude/operations/extender-db.env` is an untracked fallback)._
Status: active

## The scripts, in dependency order

Every script is stdlib-only, idempotent, and **session-run only** — subagents produce
JSON/files and never touch the DB (credentials stay with the session; the scout agent has
no shell, which makes the no-DB-access discipline structural, not just briefed).

| Order | Script | Reads | Writes | Run when |
|---|---|---|---|---|
| 0 | `serve.sh` | env / `.claude/operations/extender-db.env` | — | First. Server + admin UI on :8090. Other scripts need it up. |
| 1 | `schema.py` | its own collection specs | all collections (merge-by-name, ids preserved) | After any schema change; safe anytime. **Always before any loader.** |
| 2 | `ingest.py` | repo (`primitives-core/`, rosters, `externals.yaml`) | inventory collections + framework seeds + `mechanical-v1` assessments + the `extenders.retired` flag | After any catalog change. Never touches non-mechanical assessors or `job_coverage`/`relationships`; a slug the tree no longer defines is retired, not deleted — see "Retiring a dropped extender" below. |
| 3 | `load_eval_run.py` | a manifest JSON (run metadata + prompt/response files) | `eval_runs`, `eval_responses` | **Before** loading any judged/coverage assessments — their loader input needs the run id it creates. |
| 4a | `load_assessments.py` | judged-verdict JSON | `assessments` (per-row upsert) | W1-style judged/review passes (`judged-v1`, `review-v1`). |
| 4b | `load_coverage.py` | mapping JSON (see its docstring) | `assessments`, assessor `coverage-v1` — full cross product, or ONLY the named extenders' rows with `--extenders slug1,slug2` (EDB-26 delta mode) | Coverage passes. `--dry-run` first, always. Bulk-diff upsert; re-run must report 0 create. **Delta passes MUST use `--extenders`** so carried extenders' rows and `eval_run` stamps are never touched. |
| 5 | `report.py` | DB (or `--fixtures dir` for credential-free dev) | `coverage-matrix.md` + `analysis.md` (both generated — never hand-edit) | After anything changes coverage/relationship/assessment data. Deterministic; no-op on unchanged data. Supersedes `render_matrix.py` (removed 2026-07-21, W3). |
| 6 | `load_harness_runs.py` | `harness/results.jsonl` + `harness/runs/*.log` | `runs`, `artifacts`, `run_events`, `tool_calls` (harness telemetry, #174) | After a harness campaign, **deliberately, in-session** — `--parse-only` first (no DB), then `--dry-run`, then real. Scoped delta loads use `--campaign LABEL`. NEVER invoked by the scheduled campaign runner. |
| — | `pb.py` | — | — | Shared REST client (auth, `upsert`, `list_all`, `esc`, `create_multipart` for file fields). Import target, not a CLI. |

Cold rebuild: start a private runtime, then 1 → 2, and re-load eval provenance if wanted.
Create a disposable superuser before serving a fresh test instance to avoid the installer
browser. Never copy real authentication state into a fixture.

## Procedure: fresh Railway deployment

The root owner provisions the project and service from `evals/deploy/`; this worker package
does not create cloud resources. Before provisioning, choose a Railway persistent volume mounted
at **`/pb/pb_data`**, set server-only `PB_SUPERUSER_EMAIL` and
`PB_SUPERUSER_PASSWORD` to fresh values, and keep `PB_CORS_ORIGINS` unset until a specific
browser origin is approved. The bundle binds `0.0.0.0:$PORT`, has Railway and image health at
`/api/health`, uses a 0.40.3 binary whose per-architecture release ZIP checksum is verified at
build time, and runs `superuser create` only. A duplicate existing user is accepted without
changing its credentials; other bootstrap failures stop the container.

The deployed service starts empty. Its default collection rules remain restricted, and
`artifacts.blob` is a protected file field. After the fresh client credentials are stored as
`PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` outside the service, run `schema.py` from an authorized
session to apply the schema; do not bake credentials, schema state, `pb_data`, or auth state
into the image.

Before declaring the deployment ready, the root owner records:

1. HTTPS `GET /api/health`, then a service restart and a second health check proving volume-backed
   state persists.
2. Fresh client authentication; schema application; one representative disposable authenticated
   create/read/update/delete; anonymous denial for a domain record and for a protected artifact
   file URL.
3. API backup creation, then an isolated restore into a disposable PocketBase instance and a
   count/hash comparison against the backed-up source.
4. A rollback target (the prior Railway deployment plus its corresponding private backup) and a
   tested rollback command/path.

The root owner has recorded the private whole-directory backup and isolated disposable restore
receipt externally. Historical data upload, source removal, and authentication migration remain
root-owned integration steps; do not upload the repository's existing runtime data as part of
first deployment.

### Retiring a dropped extender

When the tree stops defining a slug, `ingest.py` ends its run by setting `extenders.retired`
on that row. It is never deleted: `assessments.extender` and `files.extender` cascade, so a
delete would take the unit's judged, review and coverage verdicts with it — rows no script
regenerates, since `ingest.py` only ever writes assessor `mechanical-v1`. Retiring is what
keeps step 2's "never touches non-mechanical assessors" invariant true.

Consequences:

- The row, its `files`, its `assessments`, its `relationships` and the `eval_responses`
  naming it all stay exactly as they were.
- The four consumers — `report.py`, `load_coverage.py`, `load_eval_run.py`,
  `load_assessments.py` — drop retired units in plain Python at their reference fetch.
  `report.py` additionally drops assessments and relationships pointing at one, because its
  joins index `ext_by_id` unguarded. Both generated documents report the exact retired-unit
  count and suppressed assessment/relationship counts across all fetched rows, before
  section-specific filtering. Missing extender references are also suppressed; a relationship
  with two excluded endpoints counts once. Eval-run linked-row counts use the active projection.
- A slug that comes back is un-retired automatically: both `extenders` upserts write
  `retired=False`.
- Preview with `ingest.py --retire-dry-run`, which lists what would be flagged and writes
  nothing. It is deliberately not spelled `--dry-run` (only the retire pass is previewed,
  not the whole ingest) and an unrecognised flag is a hard error.
- Hand-run queries over `extenders` need `retired` in the predicate — a retired unit keeps
  the previous pass's rows and will otherwise satisfy a gate on data no consumer reads.

## Procedure: an evaluated pass (the W1/M1 pattern)

The reference implementation is M1 (eval_runs `m1-coverage-{judged,review,adjudication}-2026-07-20`
hold every prompt + verbatim response). The shape:

1. **Dump materials (session).** Query the live DB for the framework elements + extender
   roster into scratchpad JSON. Agents judge from these files + repo bodies, never the DB.
2. **Write every dispatch prompt to a file BEFORE dispatching.** The prompt files become
   the `eval_responses.prompt` provenance (W7 invariant). A shared rubric file + thin
   per-batch pointer prompts works well and keeps the rubric single-sourced.
3. **Fan out judges** — read-only agents (foreman-kit:scout = no shell), batched by kind
   for consistent context, each returning ONE JSON document. Externals get judged by
   `description` only (known-thin; see EDB-23).
4. **Save verbatim responses to files** as they return — they become
   `eval_responses.response_json`.
5. **Merge + validate with a script, not by hand** (M1: `merge_coverage.py` in scratchpad):
   validate slugs/verdicts, reject unknowns/duplicates, emit the loader input + a summary.
   Judge pairwise-hint DIRECTIONS are unreliable (~4/53 inverted in M1) — normalize from
   the hint's own note text, never trust the arrow.
6. **Register the eval_run FIRST** (`load_eval_run.py` with the manifest), query its id,
   put it in the loader input, then load: `--dry-run` → real run → **re-run to prove
   idempotence** (expect 0 create / 0 update).
7. **Blind review** — independent reviewers re-derive a stratified sample under the same
   rubric, explicitly forbidden from reading the judge outputs. Blind review is *recall*,
   not just error-correction (M1: it found coverage the fan-out missed).
8. **Adjudicate (session floor), AFTER loading, not before.** Rule on each disagreement,
   log rulings + boundary rules to a JSON file, register it as an `adjudication` run, then
   PATCH only the changed rows (verdict + evidence + `eval_run` → the adjudication run).
   This ordering keeps provenance honest per pass: untouched rows keep the judged run,
   overridden rows carry the adjudication run. (Patching the loader input before loading
   would forge judge provenance for adjudicated verdicts.)
9. **Synthesis rows** (`relationships`, `job_coverage`) link to the adjudication run.
   Contested duplicative calls get one targeted reviewer check before landing — see the
   composition tells in INSIGHTS §2.
10. **Render** (`report.py`) and run the gates (below).

## Procedure: ingesting a harness campaign (#174)

After `make harness-campaign` (or any `agent-harness` run) produces new ledger rows + logs:

1. Server up (`serve.sh`); after any schema change, `schema.py` first (as always).
2. `python3 evals/load_harness_runs.py --parse-only` — offline sanity: planned counts,
   log linkage, era split, warnings. No DB connection.
3. `--dry-run` (add `--campaign LABEL` to scope a delta load — same EDB-26 discipline as
   coverage: nothing outside the scoped campaign is read, diffed, or restamped).
4. Real run, then **re-run `--dry-run` to prove idempotence** (expect 0 create / 0 update).
5. Retain the database and its artifact storage together in the private runtime/archive.
   Do not commit either; record the ingest commands and verification on the task card.

Gotchas specific to this lane:
- **File fields can't be written via JSON** — `artifacts.blob` goes through
  `pb.create_multipart()` (multipart/form-data with PB's `@jsonPayload` part). A plain
  `pb.create()` on `artifacts` silently leaves `blob` empty.
- **PB `json` fields coerce string input by a first-byte rule**: a string whose
  UNTRIMMED first byte can start a JSON value (`{ [ " -` digit `t f n`) and that then
  parses is stored PARSED (read-back returns the structure); `'     266'` (space
  first) stays a verbatim string while `'7853\n'` comes back as an int — both proven
  on the live corpus. The loader mirrors this at body-build time (`_coerce_json`);
  without it, string-JSON tool outputs (todowrite, Bash JSON prints) diff as
  "changed" forever (bit the first #174 ingest — 91 rows).
- The scheduled weekly campaign runner never auto-ingests: runtime writes require a
  deliberate session with backup and verification.

## Procedure: the gates (before declaring any pass done)

Run all of these yourself; agent self-reports don't count (PLAN "Definition of done"):

| Gate | How |
|---|---|
| 0 unmapped extenders | query: every **non-retired** extender has ≥1 present/partial row (or explicit jobless) for the pass's assessor — a retired unit keeps the last pass's rows and would pass on data no consumer reads |
| every job has a `job_coverage` row | count vs framework elements |
| loader idempotent | `load_coverage.py --dry-run` reports 0 create (post-adjudication it will report N update = exactly the adjudicated rows — expected; do NOT run it for real, it would revert them) |
| ingest discipline | checksum the pass's assessments + `relationships` + `job_coverage` → run `ingest.py` → checksums identical |
| 0 unlinked assessments | query: no row with empty `eval_run` |
| repo gates | `make ci` |

## Procedure: runtime reports and count verification

With `PB_URL` / `PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` pointing at the intended private
runtime (a disposable served instance for implementation proof):

```sh
python3 evals/schema.py
python3 evals/ingest.py
python3 evals/report.py --out /tmp/evals-report
```

For credential-free regression work, pass `--fixtures <temporary-fixture-dir>` as well.
Reports and database/storage bytes are runtime artifacts, never new commits. Existing
tracked-artifact removal and archive retention require a separately approved migration;
this procedure does not authorize untracking or deleting them.

Run these read-only queries against that same runtime's `data.db` (for example,
`sqlite3 -readonly /path/to/private/pb_data/data.db`). Keep writes quiescent while querying
and rendering so both observe the same data. The first result is retired units; the next
two are total, visible and suppressed rows. Their suppressed columns must match both reports.

```sql
SELECT count(*) AS retired_units FROM extenders WHERE retired = 1;

SELECT count(*) AS total, count(e.id) AS visible,
       count(*) - count(e.id) AS suppressed
FROM assessments a
LEFT JOIN extenders e ON e.id = a.extender AND coalesce(e.retired, 0) = 0;

SELECT count(*) AS total,
       count(CASE WHEN a.id IS NOT NULL AND b.id IS NOT NULL THEN 1 END) AS visible,
       count(*) - count(CASE WHEN a.id IS NOT NULL AND b.id IS NOT NULL THEN 1 END) AS suppressed
FROM relationships r
LEFT JOIN extenders a ON a.id = r.extender_a AND coalesce(a.retired, 0) = 0
LEFT JOIN extenders b ON b.id = r.extender_b AND coalesce(b.retired, 0) = 0;
```

Record commands, query results, and output location on the task card; do not attach auth
data. A disposable instance proves the implementation against its seeded corpus, not the
counts or migration safety of a live database.

Before a **live schema change**, additionally: take an API backup
(`POST /api/backups`, lands in `pb_data/backups/`, gitignored) and checksum the rows that
must survive; verify the checksum after (M1 pattern — the EDB-11 lesson is that a
throwaway-instance proof can mask live divergence, so the live proof is mandatory).

## Ordering gotchas (each bit somebody once)

- **eval_run before assessments** — `load_coverage.py`/`load_assessments.py` inputs carry
  the run id; the run must exist first (step 6 above).
- **Load, then adjudicate** — see step 8's provenance rationale.
- **`load_eval_run.py` keys `extenders`/`frameworks` by `slug`**, and batch files may
  carry `name` — currently name == slug for all 37, but don't rely on it.
- **schema.py before any loader** after a schema edit; new collections go at the END of
  its `order` list (two-pass id resolution needs relation targets to exist first).
- **PocketBase PATCH without field ids drops columns** (EDB-1) — schema.py's merge-by-name
  guards this; never write collection PATCHes around it.
- **Text fields cap at 5000 chars by default** (EDB-2) — set explicit `max` on evidence/
  rationale/body-sized fields.
- **Scratchpad artifacts are ephemeral** — prompts/responses/logs must land in
  `eval_responses` (via the manifest) before the session ends; the DB is the only durable
  home for eval provenance.
- **Delta passes: use `--extenders`, never an unscoped full-cross-product input**
  (EDB-26, bit the W2 delta). Unscoped, the loader relinks every carried row's
  `eval_run` to the new run — forged provenance for extenders the pass never judged
  (W2 restored 864 rows from the git-committed pre-pass `data.db`; the pattern lives in
  the W2 adjudication run's notes if it is ever needed again). The scoped mode (W3,
  #162) validates the input against exactly the named set and touches nothing else.
  Post-adjudication scoped dry-runs still report the adjudicated rows as pending
  updates — expected; never run for real.
- **View collections carry no stored fields** (#161) — `coverage_gaps` is defined only
  by its `viewQuery` (PocketBase derives the columns; `id` must alias a real column,
  here `job_coverage.id`). schema.py's merge-by-name guard is a no-op for it, and it
  sits LAST in `order` because its query references `job_coverage` +
  `framework_elements`, which must exist first.
