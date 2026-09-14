# Field notes

Findings from real PocketBase projects that the vendored rule set does not cover, or covers
less precisely. **Where a note here disagrees with `base/`, this file wins** — these came from
running instances, the base came from documentation.

## How to read the confidence tags

| Tag | Means |
|---|---|
| **PROVEN** | The source states it was observed or measured against a running instance, and quotes the observation. Treat as fact. |
| **REPORTED** | Stated as settled knowledge by a project that hit it, without a recorded live check. Usually right; verify before betting a security control on it. |
| **INFERRED** | Read from documentation or reasoned from architecture, not exercised. Verify before relying on it. |

Most notes are single-source. Versions are named where the source named one; nearly all field
work was on the v0.39 line.

---

## Access control and API rules

The base covers rule syntax. These are the ways correct-looking rules fail.

- **An OR-ed rule admits anonymous callers whenever a compared field can be empty.** An
  unauthenticated request has `@request.auth.id = ""`, and PocketBase evaluates `"" = ""` as
  true — so a clause comparing against a possibly-empty field silently makes the rule public.
  The vulnerable clause is visually identical to a safe one. REPORTED (one project reports it
  "hid in plain sight three times").

- **`updateRule` is evaluated against the OLD record and is never re-checked after the write.**
  A field lock must be a top-level conjunct. Nested inside one branch of an OR, it is bypassable.
  REPORTED.

- **Denial status codes are not uniform, and the difference is the test you write:**
  `listRule` denied returns 200 with an empty list; `viewRule` / `updateRule` / `deleteRule`
  denied return 404; `createRule` denied returns 400; a `null` rule hit by a regular user
  returns 403. A denial is therefore not detectable by checking for 403. REPORTED.

- **A denied list is indistinguishable from an empty one.** Following from the above, a
  permissions regression reads as "no records" to every caller and to most tests.

- **`null` and `""` mean opposite things and look nearly identical in a diff.** `null` is
  superuser-only; `""` is public to the internet. Deleting an `&& owner = @request.auth.id`
  fragment hands every record to any signed-in caller. REPORTED.

- **A generated-doc drift check is not a security gate.** Regenerating a rendered rules
  document after a widening still exits 0. PROVEN — one project verified that setting a
  collection's `listRule` to `""` left both of its contract checks at exit 0. Only a
  hand-reviewed snapshot diff catches an authorization widening.

- **`nil` API rule means superuser-only**, measured rather than assumed: every domain
  collection returned 403 unauthenticated. PROVEN.

- **Custom routes bypass collection rules entirely.** A `routerAdd` handler runs on its own
  authority; rules protect collection endpoints, not your whole API surface. Handlers must
  self-authorize from `e.auth`. REPORTED by three independent projects — the most repeated
  finding in this harvest.

- **Answer 404, never 403, from a custom route for a record outside the caller's scope.**
  403 confirms the record exists and is an enumeration oracle. REPORTED.

- **Custom realtime topics are not rule-checked.** `subscriptionsBroker()` topic strings are
  not authorized by PocketBase: any authenticated client can subscribe to any topic unless an
  `onRealtimeSubscribeRequest` hook explicitly authorizes it. A per-tenant topic *name* is not
  enforcement. REPORTED, from a cross-tenant leak caught in review.

- **A role or approval flag flip is not a kill switch.** Auth rules evaluate at token-mint
  time, not per request, so an already-issued token keeps working until it expires. REPORTED.

- **`authRule` gates every auth method identically**, so a locked-out account and a wrong
  password both surface as the same failure. REPORTED.

- **Traversal through an optional relation collapses to empty and silently skips those
  records** in rules and hooks, with no error. REPORTED.

## Filters and queries

- **Filters are raw interpolated strings, not parameterized queries.** Quote every interpolated
  value. Escape backslashes before quotes. `fexpr` has `//` line comments that will swallow a
  trailing quote. `encodeURIComponent` is for URL paths, never for filter expressions.
  REPORTED. Treat filter construction as an injection surface.

- **Hidden fields are excluded from filter matching for non-superuser tokens.** With
  `emailVisibility=false`, `filter=email='x'` returns an empty 200 for every caller —
  *including the record's own owner* — even when list and view rules are wide open. It never
  403s, so the failure reads as "record does not exist". Any lookup by a hidden field needs a
  system-privileged route carrying its own authorization check. **PROVEN** — clean-room proven
  2026-08-14, on v0.39; it had broken an add-member-by-email flow for every user.

- **`expand` silently omits records the caller cannot view**, rather than erroring or
  including them. REPORTED, v0.39.

- **`field = ""` matches nothing on a bool column.** The empty-string idiom that works
  elsewhere fails on bools; use `field = false`. REPORTED.

- **Use `?=` (any-of) for `@collection.*` lookups when multiple related rows are possible** —
  plain `=` silently under-matches. REPORTED.

## Hooks

- **Hooks run before `pb_migrations/` is applied.** A seed hook writing on the first
  empty-`pb_data` boot runs against PocketBase's stock schema, before your migration's fields
  exist, and silently drops every custom field. Have the hook stand down on that boot and let a
  migration do the first seed. REPORTED.

- **`e.next()` must be the first statement in `onBootstrap`, or PocketBase segfaults.**
  REPORTED.

- **`e.auth` is undefined inside `After*Success` hooks.** Capture the actor in the `*Request`
  hook before `e.next()`. REPORTED.

- **`onRecord*Request` hooks are request-scoped only.** They do not fire for programmatic
  `$app.delete()` / `e.app.save()` from cron or from a custom route calling the API directly.
  Logic that must cover both paths belongs on the universal `AfterSuccess` hook. REPORTED,
  from a real caught bug.

- **`deleteRule` is evaluated before a delete-request hook fires, and delete-request hooks fire
  for superusers too** — usable as a deliberate hard-purge escape hatch by checking
  `isSuperuser` inside the hook. REPORTED.

- **Hook error messages are normalized on the wire** — capitalized, trailing period added.
  Client code must match server strings case-insensitively on a substring, never against the
  hook's source literal. PROVEN (a bug traced to exactly this).

- **Read-then-write in a hook races under parallel requests.** SQLite serializes the COMMIT,
  not the read. Use one atomic `UPDATE … RETURNING` plus a UNIQUE index, never
  read-max-then-increment. **PROVEN** — a naive counter collided 9 times in 20 under
  concurrency.

- **The JSVM is pooled: hooks cannot share top-level functions or constants across callbacks.**
  Inline per call site. REPORTED.

- **The JS hooks engine (goja) is ES5-only** — no event loop, no `setTimeout`, no async, no
  Node or npm APIs, each handler isolated. Async JS-SDK-shaped code cannot run inside a hook.
  INFERRED (documentation-sourced).

## Schema and migrations

- **A field's type cannot be changed in place by a migration.** The migration applies and
  changes nothing. Add a new field, copy the rows, detach any views, then drop or rename the
  old one. REPORTED.

- **Never edit an already-applied migration.** A fresh store would see only the edit; existing
  stores need a new forward migration. REPORTED.

- **Self-relations need their own migration file** — a same-file self-referencing
  `collectionId` is rejected. REPORTED.

- **`id` is reserved** for the record's own primary key; a domain "id" needs a different column
  name. REPORTED.

- **Relation fields target the system 15-character record id, never a human-readable label
  field.** Getting this backwards breaks the relation silently. REPORTED.

- **A bare `TextField` silently caps at 5000 characters** unless `Max` is set. Content-bearing
  fields must set it explicitly. REPORTED.

- **A hidden `TextField` is structurally absent from API responses** — the correct way to keep
  a secret out of REST output, rather than filtering in application code. REPORTED.

- **`autodate` fields (`created` / `updated`) cannot be set by an importer.** Historical
  backfill needs separate settable columns. REPORTED.

- **A collection's OAuth `providers[]` is stripped from a migration's auto-diff** — only
  `oauth2.enabled` persists. Client id and secret must be set at runtime by a boot hook.
  REPORTED.

- **View collections: `UNION` is rejected** (the column parser reads straight through the
  boundary) — use `LEFT JOIN` with `COALESCE`. **A view whose rows could share an `id` is
  rejected** — `DISTINCT` is required. PROVEN ("both found by trying").

- **View collections get no realtime events**, and their `_clone_*` column ids regenerate on
  every boot — never diff or reference them. REPORTED.

- **`migrate down` and `migrate collections` prompt interactively.** Pipe `printf 'y\n' |` in
  automation. REPORTED.

- **Auto-written `pb_migrations/` collide with a wiped `pb_data` on rerun** ("model id is
  invalid or already exists"). Delete or ignore them alongside `pb_data`, and keep a single
  authored schema source. PROVEN, v0.39.9.

- **`Automigrate: true` captures GUI-made schema edits as new migration files**, which is how
  schema drift becomes reviewable. REPORTED.

## Auth and superusers

- **Bootstrap a superuser with `superuser create`, never `upsert`.** `create` is an idempotent
  no-op if the account exists; `upsert` resets the password on every boot, which rotates
  PocketBase's `tokenKey` and invalidates every live session. REPORTED by two projects, one
  citing a real incident.

- **Setting only one of the superuser bootstrap env vars is a loud fatal error; setting
  neither is a silent no-op.** REPORTED.

- **A non-fatal superuser bootstrap can fail silently** — for example a password rejected by
  validation — landing as a database log row rather than on stderr, without stopping boot. A
  fail-closed gate must re-count administrable superusers rather than trust that the env vars
  worked. REPORTED.

- **The first-run installer writes a placeholder superuser row with no usable password**, purely
  to mint a setup link. A naive "does a superuser exist" check is satisfied by a row nobody can
  log in as. REPORTED, as a discovered and fixed bypass.

- **The stock auth collection allows open signup with immediate login** — no email-verification
  gate by default. PROVEN, measured on an unmodified binary: signup 200, login 200. Do not
  assume the default auth collection is safe to expose publicly.

- **A superuser with MFA and OTP can still be authenticated headlessly**, no inbox needed: mint
  the OTP inside the server process with `pocketbase superuser otp <email>`, which prints an id
  and pass valid for 300 seconds, then `auth-with-password` returns 401 with an `mfaId`, and
  `auth-with-otp` completes it. PROVEN live 2026-08-17.

- **Token revocation is coarse** — rotating `tokenKey` ends every session for that user, not one.
  INFERRED (flagged low-confidence by its source).

- **The auth rate limiter's state is in server memory only.** Resetting it requires a restart;
  re-running a suite against a still-live server returns 429. REPORTED.

- **Rate-limit rules need method-qualified complete paths.** A generated tag such as `*:list`
  outranks a path-prefix rule, and superusers bypass the limiter entirely. REPORTED.

## Files

- **A protected-file token is reusable for its full lifetime (about 2 minutes), not
  single-use.** PROVEN on v0.39.9: the same token fetched the same protected file repeatedly,
  200 every time. Fetch one token per burst and reuse it; code written defensively against a
  single-use assumption is doing needless work. This corrects a claim carried by an earlier
  version of the operational skill.

- **Protected downloads use `POST /api/files/token` then `?token=` on the URL** — not an
  `Authorization` header on the file request. REPORTED.

- **PocketBase renames stored files on upload.** Build download URLs from the stored field
  value, not the original filename; keep your own display-name field. REPORTED.

- **A fetch wrapper that always JSON-stringifies silently destroys file uploads.** Forcing
  `Content-Type: application/json` drops the multipart body; on a collection whose other fields
  are optional this *succeeds* and creates an empty record — silent data loss, not an error.
  PROVEN, v0.39.9.

- **The same wrapper mangles downloads.** `res.text()` plus `JSON.parse` replaces invalid UTF-8
  with U+FFFD and destroys the round trip with no error. Binary responses need an explicit
  `arrayBuffer` or `blob` mode. PROVEN, v0.39.9.

- **The auth token goes in the `Authorization` header with no `Bearer` prefix.** REPORTED.

## Realtime

- **SSE is at-most-once with no replay of missed events on reconnect.** Treat a realtime event
  purely as a wake signal and reconcile against your own durable cursor on every connect. Never
  treat SSE delivery as correctness. INFERRED (documentation-sourced).

## Operations and deployment

- **`serve` and `superuser` RunE errors exit 0.** PocketBase runs `RootCmd.Execute()` in a
  goroutine and discards the RunE error by design, and registers those commands *inside*
  `Start()` — so a wrapper installed on `app.RootCmd.Commands()` beforehand never sees them.
  **PROVEN**: a guard returned an error, the server never bound, and the process still exited 0.
  Any supervisor or CI step that trusts the exit code will read a dead server as a healthy one.

- **`Bootstrap()` creates the data directory before any RunE or PreRunE fires.** A guard that
  must prevent store creation has to run in `main()` before `Start()`, not in a cobra hook.
  REPORTED.

- **One-shot CLI commands do not share the `serve` process's hooks or realtime**, so event hooks
  registered under `serve` do not fire for them. REPORTED.

- **SQLite is single-writer**: a one-shot command and `serve` must not run against the same
  store concurrently. REPORTED. PocketBase is single-server by design — vertical scaling only,
  and streaming replication is disaster recovery, not high availability. INFERRED.

- **`/api/logs` entries are held about 3 seconds before they are queryable.** A check that reads
  logs immediately after a request sees zero errors on a broken run. **PROVEN** — measured
  2026-08-17 across three trials and two event kinds: 3.02 to 3.05 seconds. Poll with a cap
  rather than reading once. Default retention is 5 days.

- **`s3.enabled=true` routes all backup operations to S3** and the local `pb_data/backups` path
  is then ignored entirely. PROVEN.

- **An S3 key beginning with `@`** — which is PocketBase's own auto-backup naming — **breaks
  AWS SigV4 signing on DELETE**, returning 403 `SignatureDoesNotMatch`. It looks like a
  permissions problem and is not; percent-encode the key. PROVEN.

- **`restoreBackup` is point-in-time and restarts the process in place**, and PocketBase
  documents it as UNIX-only and experimental. REPORTED.

- **CORS is not a settings field** (v0.39.9) — it is the `serve --origins` flag only. REPORTED.

- **The default CORS middleware can survive app-level hardening unnoticed.** It comes from
  PocketBase's own default middleware rather than your code, so a wildcard
  `Access-Control-Allow-Origin` will not appear in a diff or code review. Unbinding it also
  removes its `OPTIONS` handler, after which preflight answers 404 instead of 204. PROVEN —
  it shipped on a public path until caught. Verify security headers against a live response.

- **Derive auth posture from the resolved bind address, never a separate `--public` flag.** A
  flag can be forgotten while a wildcard bind still ships, failing open. Classify both the HTTP
  and HTTPS listeners: the serve-start event surfaces only one. REPORTED.

- **A persistent volume must be attached before the first deploy.** SQLite is the entire
  database; without it every redeploy starts empty, superuser included. REPORTED.

- **Deploy the backend and the web app as separate services** so a frontend push never restarts
  the data plane. REPORTED.

## Go package mode

- **Use the v0.23+ `core.Collection` / `core.*Field` API, not the legacy `models` / `schema`
  API.** Model priors trained on older examples get this wrong. REPORTED.

- **PocketBase's `go.mod` floors the whole binary's Go toolchain version** — v0.39.6 requires
  Go 1.25.0, which can be stricter than every other dependency. VERIFIED against the actual
  `go.mod`.

- **Custom routes registered in `OnServe` can be superuser-gated** with
  `apis.RequireSuperuserAuth()` bound via `.Bind(...)`. REPORTED.

- **`RequireAuth` distinguishes wrong-auth-collection from no-token**: a valid token from an
  unexpected auth collection is 403, not 401. REPORTED.

## Model priors that are wrong for v0.23 and later

Stated in the base and worth repeating, because these are the errors a model makes unprompted:
`_superusers` not `_admins`; collection `fields` not `schema`; flat field properties with no
`options` wrapper; typed field constructors in migrations; `{param}` route syntax, not `:param`.

## Architecture judgment

- **Do not adopt PocketBase as a system-of-record replacement for a codebase already built on
  synchronous transactional storage.** Its REST surface offers no client-controlled transactions
  or compare-and-swap, forcing atomicity to be rebuilt as optimistic retry — strictly weaker
  than what such a codebase already has. INFERRED (an architecture judgment, not a bug).

## Patterns worth copying

- **Treat migration replay as the schema source of truth.** Author only `pb_migrations/`, then
  derive schema docs, OpenAPI, test fixtures, and client types by replaying migrations into a
  throwaway instance — each behind a drift gate in CI. Hand-written schema docs go stale; a
  derived artifact cannot.

- **Wire every secret-bearing setting through env-driven boot hooks, never migrations.** A
  migration bakes the secret into git history and cannot pick up a rotated key. Applies to
  object storage, SMTP, OAuth client secrets, and alert addresses.

- **Never expose the backend URL or token to the browser.** Route through a server-only proxy
  with centralized error normalization and path-injection safety.

- **Require a hand-written, dated justification for any public (`""`) rule**, recorded outside
  the migration. An automated tool that invents the reason defeats the review.

- **Prefer grant-style rules over deny-plus-hook.** Keeping the whole access decision in the
  rule string keeps it in a snapshot-diffable artifact; a hook that owns mutation authorization
  is invisible to every rule-level gate.
