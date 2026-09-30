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

## Procedure: update the existing Toolbox

Use the existing service and volume. Publishing marketplace plugins through `main` is a
separate operation. Merge through green PR checks into `dev`; retain the exact source SHA,
local gate/build output, package hashes and resulting deployment ID in an external receipt.

1. Verify the project, production environment, service, domain and `/pb/pb_data` volume against
   the current operating record. Authenticate the ordinary user and administrator separately;
   keep credentials outside the package. Capture collection IDs/counts and hashes of existing
   records and protected files. Create a named PocketBase backup through `POST /api/backups`
   and verify its key and nonzero size with `GET /api/backups` before schema or ingestion writes.
2. Test schema/access/loader changes on a disposable PocketBase first. Apply only the reviewed
   schema delta, preserving existing field IDs and all unrelated fields/rules. For the agreed
   content areas, `python3 evals/toolbox_access.py` previews null read rules to be changed;
   `--apply` grants authenticated read only after preflight. Unexpected existing rules stop
   the operation. Users remain self-only, ordinary writes remain locked, and artifact blobs
   remain protected. Read rules and actual ordinary/anonymous behavior back afterward.
3. Run the relevant loader's parse-only/dry-run route before scoped ingestion. Deployment
   does not ingest data. Keep original source hashes, scope, create/update counts and a second
   ingestion receipt showing no duplicates. Missing source logs are a provenance limit, never
   permission to erase previously stored events, tools or artifacts. Never upload synthetic
   fixtures as live evidence or reinterpret historical default zeros as observations.
4. Build and package an exact merged `dev` archive. From the repository root:

   ```sh
   git fetch origin dev
   toolbox_sha=$(git rev-parse origin/dev)
   toolbox_source=$(mktemp -d /tmp/toolbox-source.XXXXXX)
   toolbox_release=$(mktemp -d /tmp/toolbox-release.XXXXXX)
   git archive "$toolbox_sha" | tar -x -C "$toolbox_source"
   bun install --cwd "$toolbox_source/evals/ui" --frozen-lockfile
   bun run --cwd "$toolbox_source/evals/ui" typecheck
   bun run --cwd "$toolbox_source/evals/ui" build
   python3 "$toolbox_source/evals/package_toolbox.py" "$toolbox_release/package" \
     --source-root "$toolbox_source" --ui-build "$toolbox_source/evals/ui/dist"
   ```

   The package inventory hashes UI source/build and catalog inputs; the recorded archive/build
   commands establish their origin. Inspect the package before upload. No credentials,
   database, original runtime artifacts, source maps or dependency trees belong in it.
5. Upload only that package, substituting the verified existing IDs:

   ```sh
   railway up "$toolbox_release/package" --path-as-root \
     --project PROJECT_ID --environment ENVIRONMENT_ID --service SERVICE_ID \
     --detach --json --message "Toolbox dev@$toolbox_sha"
   ```

   Poll the
   returned deployment ID to `SUCCESS`; a successful upload is not a successful deployment.
6. Repeat ordinary-user desktop/mobile find, compare and evidence flows against real records.
   Verify displayed values against their recorded source, missing-value labels, protected-file
   token access, sign-out clearing and anonymous/write denial. Reconcile preexisting record IDs
   and protected-file hashes with the baseline; explain only the intended projection additions
   or updates. Keep fixture checks and hosted checks in separate receipts.

For an application-only rollback, redeploy the previously verified package to the same service
and volume. Additive schema fields need not be removed. Database restore replaces current data:
preserve a current backup and obtain explicit recovery authorization before restoring the named
pre-change backup. Never recreate or remove the volume as a rollback shortcut.

## Procedure: fresh Railway deployment

The root owner alone provisions accounts, rules, cloud state, and deployment after the browser
login email arrives. First create a throwaway package; never deploy the repository directory.

```sh
package_dir=/tmp/evals-toolbox-deploy
bun install --cwd evals/ui --frozen-lockfile
bun run --cwd evals/ui typecheck
bun run --cwd evals/ui build
python3 evals/package_toolbox.py "$package_dir" --ui-build "$PWD/evals/ui/dist"
cd "$package_dir"
railway up --path-as-root
```

In the Railway UI, deploy that package directory, mount the existing persistent volume at
**`/pb/pb_data`**, and set server-only `PB_SUPERUSER_EMAIL` and
`PB_SUPERUSER_PASSWORD`. The package has no `.env`, `pb_data`, raw repository data, or client
credentials. Read back the deployment's `/api/health` response and, with an authenticated
browser token, `GET /api/toolbox/catalog` before treating the package as live. The catalog is
outside `pb_public` and the route uses PocketBase authentication middleware.

For a disposable local loopback Browser check, use the actual packaged PocketBase service with
fresh synthetic credentials and an empty temporary data directory; do not copy a production
database or token into it:

```sh
bun run --cwd evals/ui build
python3 evals/toolbox_fixture.py --pocketbase /opt/homebrew/bin/pocketbase
```

It prints the loopback URL and fixture-only browser email/password, applies the schema and
authenticated read-only rules, seeds 27 synthetic runs plus one protected artifact, and removes its
process and temporary data on Ctrl-C. It reads no credential or configuration environment file. The focused
test runs this actual fixture when PocketBase is present; otherwise it is explicitly skipped.

The root creates the browser `users` account manually after its email is supplied. Public signup
is disabled (`createRule = null`); users list and view are self-only, while
users update and delete are `null`. Configure `runs` and `artifacts` with authenticated read-only list
and view rules, then apply the same `toolbox_access.py` content-area rules used for existing
deployments. All create, update, and delete rules stay `null`. Keep `artifacts.blob` protected and use
PocketBase's authenticated short-lived file token route for it. The browser stores its token only
in memory, clears it on logout, and never receives a superuser credential.

After schema setup and browser-user creation, authenticate as a superuser and set
`PB_ADMIN_TOKEN` in that root-only shell, then
apply and read back the rules with the following commands. The `users` rules limit a browser user
to its own record; the business rule allows any authenticated browser account to read only.

```sh
auth_header="Authorization: $PB_ADMIN_TOKEN"
users_rule='id = @request.auth.id'
business_rule="@request.auth.id != ''"
curl --fail-with-body -X PATCH "$PB_URL/api/collections/users" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data "{\"listRule\":\"$users_rule\",\"viewRule\":\"$users_rule\",\"createRule\":null,\"updateRule\":null,\"deleteRule\":null}"
for collection in runs artifacts; do
  curl --fail-with-body -X PATCH "$PB_URL/api/collections/$collection" \
    -H "$auth_header" -H 'Content-Type: application/json' \
    --data "{\"listRule\":\"$business_rule\",\"viewRule\":\"$business_rule\",\"createRule\":null,\"updateRule\":null,\"deleteRule\":null}"
  curl --fail-with-body "$PB_URL/api/collections/$collection" -H "$auth_header"
done
curl --fail-with-body "$PB_URL/api/collections/users" -H "$auth_header"
python3 evals/toolbox_access.py
python3 evals/toolbox_access.py --apply
```

The earlier empty-service procedure remains applicable to the resulting package. The root owner
does not create cloud resources from this worker package. Before provisioning, choose a Railway
persistent volume mounted at **`/pb/pb_data`**, set
server-only `PB_SUPERUSER_EMAIL` and
`PB_SUPERUSER_PASSWORD` to fresh values, and keep `PB_CORS_ORIGINS` unset until a specific
browser origin is approved. The bundle binds `0.0.0.0:$PORT`, has Railway and image health at
`/api/health`, uses a 0.40.3 binary whose per-architecture release ZIP checksum is verified at
build time, and runs `superuser create` only. A duplicate existing user is accepted without
changing its credentials; other bootstrap failures stop the container.

The deployed service starts empty. Its default collection rules remain restricted, and
`artifacts.blob` is a protected file field. After the fresh client credentials are stored as
`PB_ADMIN_EMAIL` / `PB_ADMIN_PASSWORD` outside the service, run `schema.py` from an authorized
session to apply the 17 domain collections; do not bake credentials, schema state, `pb_data`, or
auth state into the image. `schema.py` does not manage the default zero-user `users` auth
collection or global settings: apply the read-only rules above, enable built-in `rateLimits`
without replacing those rules, and read both the `users` rules and settings back. Before the
import, also verify PocketBase batch is enabled
with `maxRequests >= 10`. The Railway password is an ordinary service secret supplied through
stdin and retained in the root-only local credential file; Railway does not seal it.

Before declaring the deployment ready, the root owner records:

1. HTTPS `GET /api/health`; authenticate, create an authenticated disposable sentinel with unique
   content, and record its ID and content. Restart or redeploy, authenticate again, read that same
   ID and exact content back, then delete the sentinel. Health checks alone do not prove persistence.
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

### Procedure: private business-data consolidation

The reviewed migration scope is `all`: exactly `frameworks`, `sources`, `extenders`,
`framework_elements`, `files`, `distributions`, `frontmatter_dimensions`, `eval_runs`,
`eval_responses`, `assessments`, `job_coverage`, `relationships`, `runs`, `artifacts`,
`run_events`, and `tool_calls`, in that dependency order. It excludes `coverage_gaps`, every
other table, all system/settings/auth tables, and all historical authentication.

```sh
python3 evals/migrate_business_data.py --source-db /private/pb_data/data.db --scope all
python3 evals/migrate_business_data.py --source-db /private/pb_data/data.db --scope all \
  --receipt /private/reviewed-business-receipt.json
```

The default is an offline immutable SQLite dry-run. Its stdout is counts and SHA256 receipts only;
the optional private receipt is refused if it already exists and contains only record IDs, original
`created`/`updated` values, table digests, and artifact hashes. It never contains business bodies,
prompts, responses, evidence, payloads, tool content, local paths, or credentials. The verified
snapshot receipt is 2,146 core rows plus 6,846 telemetry rows, 8,992 total; 26 verified artifact
blobs total 780,427 bytes. `files` remains database content: 226 rows, 2,230,426 `size_bytes`,
226 distinct stored hashes, and 215 nonempty content rows. The 26 `.attrs` storage sidecars are
not uploads.

Only after the root confirms this content decision and has the private receipt may it add
`--apply`. It first requires every selected destination collection to be empty, sends JSON record
creates in fixed batches of 10 through PocketBase `/api/batch` (and fails if batching is unavailable
or a subresponse fails), uploads the 26 verified blobs separately with multipart, and never cleans
up a destination or remaps IDs. Before success it rereads every collection, requires the exact ID
sets and counts, compares each source field/relation/content value (excluding only audit timestamps
and file transport), verifies fresh protected-file downloads byte-for-byte, and emits a
counts/digest/hash validation receipt. Preserve that validation receipt before untracking the local
data. Explicit 15-character IDs survive PocketBase 0.40.3 creation;
its `created`/`updated` values are ignored and replaced by new-copy audit timestamps. Domain
chronology in `runs.ts`, `run_events.ts`, and `tool_calls.started_ts` is preserved. The private
backup and receipt retain the original PocketBase audit timestamps; no duplicate legacy timestamp
fields are added.

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
