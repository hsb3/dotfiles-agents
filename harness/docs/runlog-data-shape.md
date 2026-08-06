*Empirical shape of the agent-harness run-log corpus, to inform durable PocketBase collection designs (GitHub #174).*

Status: implemented — 2026-07-21. Schema + ingester landed (`evals/schema.py`, `evals/load_harness_runs.py`); the §5 owner decisions and the verified ingest counts are recorded on #174. Implementation deviations from §4: the `artifacts.event` relation was dropped (relation cycle with `run_events.artifact`; the rel lives on the many side only, creation order `runs → artifacts → run_events → tool_calls`); `runs.ts` is text, not date (naive local ISO stamps); the `session_id` unique index is partial (`WHERE session_id != ''`); write/edit content is externalized only above `ARTIFACT_TEXT_THRESHOLD = 5000` chars.

Every number below is computed by the scripts in `scratchpad/logshape/` (filenames in the footer); nothing is hand-transcribed. The PocketBase (extender-db) instance is **not touched** — this is a shape proposal only.

---

## §1 Corpus summary

| Corpus | Files | Events | Bytes |
|---|---|---|---|
| `harness/runs/*.log` | 72 | 3,688 | 5,242,094 (5,119 KiB) |
| `harness/results.jsonl` | 72 rows | — | 142,375 |
| `foreman-smoke/runs/*.log` (extra) | 2 | 18 | 15,427 |

**Two vendor formats × (claude only) two eras.** Split confirmed empirically from the `system/init` event:

| Group | Files | Discriminator (init event) | events/trial min/med/p95/max | bytes/trial min/med/p95/max |
|---|---|---|---|---|
| claude / **legacy** | 24 | 3 tools, `apiKeySource=ANTHROPIC_API_KEY`, `plugins` populated | 15 / 42 / 88 / 88 | 14.5K / 42K / 110K / 116K |
| claude / **post** | 24 | 25 tools, `apiKeySource=apiKeyHelper`, `plugins=[]` in 15/24 | 17 / 68 / 140 / 151 | 14.8K / 58K / **552K** / **727K** |
| opencode | 24 | (JSONL, no init event) | 12 / 22 / 93 / 105 | 10.3K / 28.5K / 201K / 221K |

- The legacy vs post pairing is per-trial: each of the 24 claude trials was run once in the ~15:00 (legacy) block and once in the ~16:45 (post / Option-Z) block. `init_tools<=5` is the robust discriminator (`plugins==[]` alone is not — 9 post-era inits still carry inline plugins).
- The **post-era p95/max byte explosion** is base64 screenshot payloads (browser/skill tool output), not more events — see §3/§4.
- Smoke corpus contributes one **auth-failure** error sample: `result` event with `is_error=true`, `subtype="success"` (subtype is *not* the error signal), `terminal_reason="api_error"`, `result="Not logged in · Please run /login"`, all token/cost fields 0.

Ledger cross-tab (all 72 rows):

| harness × campaign | rows | | harness × kind | rows |
|---|---|---|---|---|
| claude / (legacy, no `campaign`) | 24 | | claude / skill | 36 |
| claude / `skillfix` | 24 | | claude / agent | 12 |
| opencode / (legacy) | 24 | | opencode / skill | 18 |
| | | | opencode / agent | 6 |

The 48 "legacy" ledger rows = 24 claude-legacy + 24 opencode (both lack the newer fields); the 24 `skillfix` rows are all claude-post.

---

## §2 Empirical schema per vendor format

Event-type inventories are exhaustive across all 24 files per group. Field tables list the load-bearing paths with **presence %** (fraction of events of that type carrying the path); the full per-path dump (every path incl. the <5% tail, value types, nesting depth, examples) is in `out_02_events.txt`.

### 2a. claude stream-json — event-type inventory

| type/subtype | legacy events (ev/trial) | post events (ev/trial) | bytes min/med/p95/max (post) | notes |
|---|---|---|---|---|
| `assistant` | 568 (23.7) | 597 (24.9) | 722/928/2880/**12729** | message + content blocks (thinking/text/tool_use) |
| `system/thinking_tokens` | 143 (6.0) | 500 (20.8) | 191/194/194/196 | running token estimate; pure noise for storage |
| `user` | 355 (14.8) | 385 (16.0) | 408/807/9753/**149746** | tool_result blocks + `tool_use_result` mirror |
| `system/init` | 24 (1.0) | 27 (1.1) | 1926/1957/2308/2308 | run provenance |
| `result/success` | 24 (1.0) | 27 (1.1) | 1349/1610/2163/2478 | run summary (tokens, cost, timing) |
| `system/task_progress` | 0 | 113 (4.7) | 362/380/407/420 | post-era only (subagent progress) |
| `system/task_started` \| `task_updated` \| `task_notification` \| `background_tasks_changed` | 8/8/8/16 | 21/14/21/22 | 163–4093 | background-task lifecycle (bash servers, subagents) |

(Global counts across all 48 claude files: assistant 1165, thinking_tokens 643, user 740, init 51, result 51, task_progress 113, background_tasks_changed 38, task_started 29, task_notification 29, task_updated 22. `result` subtype is **always** `success`, even on error.)

### 2b. claude — field inventory (key paths, presence %)

`system/init` (n=51):

| path | present% | type | notes |
|---|---|---|---|
| `session_id` | 100 | str | run key (stable per trial) |
| `model` | 100 | str | e.g. `claude-sonnet-4-5` |
| `cwd` | 100 | str | ephemeral workspace path |
| `apiKeySource` | 100 | str | era discriminator |
| `claude_code_version` | 100 | str | `2.1.206` |
| `permissionMode` | 100 | str | `acceptEdits` |
| `mcp_servers` | 100 | arr(empty) | always [] here |
| `tools[]` | 100 | str[] | 3 (legacy) vs 25 (post) |
| `agents[]` | 100 | str[] | 6 |
| `slash_commands[]` | 100 | str[] | ~40 (biggest init path, 25–30% of bytes) |
| `skills[]`, `capabilities[]`, `memory_paths.auto` | 100 (post only) | str[]/str | post-era additions |
| `plugins[].{name,path,source}` | 33–100 | str | inline eval plugin(s); empty in most post |

`assistant` (n=1165) — envelope + `message.*`:

| path | present% | type | notes |
|---|---|---|---|
| `type`,`uuid`,`session_id`,`request_id` | 100 | str | `parent_tool_use_id` null (legacy) / str when subagent (post) |
| `subagent_type`, `task_description` | 0 / 27 | str | **post-era only** (Task fan-out) |
| `message.id`,`message.model`,`message.role` | 100 | str | model = dated id `…-20250929` |
| `message.usage.input_tokens` / `output_tokens` | 100 | int | per-message |
| `message.usage.cache_creation_input_tokens` / `cache_read_input_tokens` | 100 | int | per-message cache |
| `message.usage.cache_creation.ephemeral_{5m,1h}_input_tokens` | 100 | int | cache TTL split |
| `message.content[].type` | 100 | str | `thinking`\|`text`\|`tool_use` |
| `message.content[].thinking` (+`.signature`) | ~7 | str | reasoning; signature is opaque bulk |
| `message.content[].text` | 30–33 | str | assistant prose (max 3451 chars) |
| `message.content[].id`,`.name` | 62 | str | tool-call id + tool name |
| `message.content[].input.*` | varies | mixed | **tool arguments** — union of ~20 keys (command, file_path, old/new_string, content, prompt, subagent_type, skill, …) |

`user` (n=740) — tool results, two mirrored representations:

| path | present% | type | notes |
|---|---|---|---|
| `type`,`uuid`,`session_id`,`timestamp` | 100 | str | `timestamp` = only per-tool wall-clock claude gives |
| `message.content[].type` | 100 | str | `tool_result` |
| `message.content[].tool_use_id` | ~97–100 | str | joins to the assistant tool-call id |
| `message.content[].content` | 90–100 | str | tool result text (max 5262 chars) |
| `message.content[].is_error` | 27–51 | bool | per-result error flag |
| `message.content[].content[].source.{type,media_type,data}` | ~3.6 (post) | str | **base64 image** (screenshots) |
| `tool_use_result.*` (mirror) | varies | mixed | structured twin: `.file.content`, `.file.base64`, `.stdout`/`.stderr`, `.structuredPatch[]`, `.toolStats.*`, `.usage.*` (subagent) — **duplicates** the content block |

`result/success` (n=51) — the run summary:

| path | present% | type | notes |
|---|---|---|---|
| `is_error` | 100 | bool | **the** error signal (subtype stays `success`) |
| `duration_ms`,`duration_api_ms`,`ttft_ms`,`ttft_stream_ms`,`time_to_request_ms` | 100 | int | timing (post has all; legacy has duration+ttft) |
| `num_turns` | 100 | int | |
| `total_cost_usd` | 100 | float | run cost |
| `result` | 100 | str | final assistant text (max 1570 chars) |
| `stop_reason`,`terminal_reason` | 100 | str | `end_turn`/`completed`; `api_error` on failure |
| `usage.{input,output,cache_creation,cache_read}_*` | 100 | int | run token totals |
| `modelUsage.<model>.{inputTokens,outputTokens,cacheReadInputTokens,cacheCreationInputTokens,costUSD,contextWindow,maxOutputTokens,webSearchRequests}` | 100 | mixed | **per-model breakdown** (sonnet + haiku grader) |
| `permission_denials` | 100 | arr | usually [] |

### 2c. opencode JSONL — event-type inventory (n across 24 files)

| type (== `part.type`) | events | ev/trial | bytes min/med/p95/max | carries |
|---|---|---|---|---|
| `tool_use` | 275 | 11.5 | 498/1944/9240/**38711** | tool call **and** result in one event |
| `step_start` | 192 | 8.0 | 249 (fixed) | step boundary, ids only |
| `step_finish` | 192 | 8.0 | 379/387/389 | **tokens + cost per step** |
| `text` | 148 | 6.2 | 330/403/1208/1686 | assistant prose (max 1355) |

No init event, no run-level result/summary event, no top-level model field. Tool `status ∈ {completed:266, error:9}`. Tools: read 130, bash 47, todowrite 33, write 16, edit 13, task 13, skill 9, glob 11, grep 1, invalid 2.

### 2d. opencode — field inventory (key paths, presence %)

`tool_use` (n=275):

| path | present% | type | notes |
|---|---|---|---|
| `sessionID` | 100 | str | run key |
| `timestamp` | 100 | int (ms epoch) | event time |
| `part.callID` | 100 | str | tool-call id (`toolu_…`) |
| `part.tool` | 100 | str | tool name (lowercase) |
| `part.state.status` | 100 | str | `completed`\|`error` |
| `part.state.time.{start,end}` | 100 | int (ms) | **per-tool wall-clock** (claude lacks this) |
| `part.state.input.*` | varies | mixed | tool args (filePath, command, content, newString/oldString, prompt, subagent_type, todos[], …) |
| `part.state.output` | 97 | str | tool result text (max 6010 chars → **can exceed 5000**) |
| `part.state.error` | 3.3 | str | error message |
| `part.state.metadata.diff` **and** `.metadata.filediff.patch` | 4.7 | str | **exact duplicate** (13/13 edits) |
| `part.state.metadata.model.{modelID,providerID}` | 4.7 | str | only present on subagent/task calls |
| `part.state.attachments[].url` | 2.2 | str | **`data:image/png;base64,…`** screenshot |
| `part.metadata.anthropic.caller.type` | 100 | str | `direct` |

`step_finish` (n=192) — where opencode puts usage:

| path | present% | type | notes |
|---|---|---|---|
| `part.cost` | 100 | float | **per-step** cost (sum for run total) |
| `part.reason` | 100 | str | `tool-calls`\|`stop` |
| `part.tokens.{input,output,reasoning,total}` | 100 | int | per-step |
| `part.tokens.cache.{read,write}` | 100 | int | per-step cache |

---

## §3 Proposed normalized event model

Derived from the cross-vendor mapping below. **Legend:** ✓ native, ∑ derivable by summing step/message rows, ✗ absent.

| Normalized fact | Type | claude path | opencode path | both? |
|---|---|---|---|---|
| run/session id | text | `session_id` (all events) | `sessionID` (all events) | ✓/✓ |
| tool-call id | text | `content[].id` / `tool_use_id` | `part.callID` | ✓/✓ |
| tool name | text | `content[].name` | `part.tool` (lowercase) | ✓/✓ |
| tool input (args) | json | `content[].input` | `part.state.input` | ✓/✓ |
| tool output/result | json/file | `user content[].content` / `tool_use_result` | `part.state.output` | ✓/✓ |
| tool status/error | text | `content[].is_error` + `result.is_error` | `part.state.status` / `.error` | ✓/✓ |
| **per-tool wall-clock** | number | ✗ (only `user.timestamp`) | `part.state.time.{start,end}` | ✗/✓ |
| assistant text | text | `content[].text` | `text` event `part.text` | ✓/✓ |
| reasoning/thinking | text | `content[].thinking`(+signature) | `part.tokens.reasoning` (count only) | ✓/partial |
| per-step tokens | number | `assistant.message.usage.*` | `step_finish.part.tokens.*` | ✓/✓ |
| cache tokens (create/read) | number | `usage.cache_{creation,read}_input_tokens` | `part.tokens.cache.{write,read}` | ✓/✓ |
| **cost** | number | `result.total_cost_usd` (run) + `modelUsage.*.costUSD` | `step_finish.part.cost` (∑ per run) | run/∑ |
| model | text | `init.model` + `assistant.message.model` + `modelUsage` keys | `part.state.metadata.model.modelID` (subagent only) | ✓/partial |
| run duration/timing | number | `result.{duration_ms,ttft_ms,…}` | ∑ `time.end-start` / last−first ts | ✓/∑ |
| run token/cost totals | number | `result.usage.*` + `modelUsage.*` | ∑ `step_finish` | ✓/∑ |
| workspace cwd | text | `init.cwd` | ✗ (in tool paths only) | ✓/✗ |
| provenance (version, apiKeySource, tools, plugins) | json | `init.*` | ✗ | ✓/✗ |
| base64 image artifact | file | `content[].source.data` + `tool_use_result.file.base64` | `part.state.attachments[].url` | ✓/✓ |
| written-file content | file/json | `input.content`/`new_string` + `structuredPatch` | `input.content`/`newString` + `metadata.diff` | ✓/✓ |

**Proposed `run_event` normalized record** (one row per meaningful step; drop `thinking_tokens` noise):

```
run_event { run(rel), seq(int), ts(ms), vendor, era, role,        # role: assistant|tool_call|tool_result|system|result
            tool_name?, tool_call_id?, status?, is_error(bool),
            input_tokens?, output_tokens?, cache_read_tokens?, cache_write_tokens?, cost_usd?,
            wallclock_ms?,                                          # opencode only
            text?(<=5000), payload(json),                          # payload = raw event body
            artifact(rel?) }                                       # set when a large blob is externalized
```

- **Vendor reconciliation:** claude emits *separate* `assistant`(tool_use) and `user`(tool_result) events joined by tool-call id; opencode fuses call+result into one `tool_use` event. Normalize both to a `tool_call` row (input) + `tool_result` row (output), or a single fused row keyed by `tool_call_id` — the id join works in both formats.
- **Cost/timing granularity differs:** claude gives a run-level `result` summary; opencode gives none (sum `step_finish`). Store both raw and a derived run rollup on `runs` (§4).

---

## §4 Proposed PocketBase collections

Sizing basis (measured): 1,003 tool calls / 72 trials, 3,688 events, tool input+output median **154 B** / p95 **2,705 B** / max **7,374 B**; write/edit content max **5,076 B** (1/70 > 5000); **20** base64 images median **37 KB** / max **75 KB** (total 834 KB). Raw-log-equivalent projection: **24-trial campaign ≈ 1,229 event rows / 1.7 MiB; 100 campaigns (2,400 trials) ≈ 122,933 event rows / 166.6 MiB.**

**PB constraint applied throughout:** text fields default-cap at 5,000 chars. Any field measured able to exceed that (tool output/result, written-file content, base64 images) is a `json` field (higher cap) or a `file` field — never plain `text`. Small bounded strings stay `text`.

### `runs` — one row per trial (≈ ledger row + log provenance)

| field | PB type | source | notes |
|---|---|---|---|
| `harness` | select(claude,opencode) | ledger `harness` | |
| `era` | select(legacy,post,na) | derived (init tools) | |
| `campaign` | text | ledger `campaign` | null on legacy |
| `candidate`,`case`,`config`,`kind` | text | ledger | config∈{with,baseline} |
| `trial` | number | ledger | |
| `model`,`grader_model`,`cli_version` | text | ledger / init | |
| `session_id` | text | log `session_id`/`sessionID` | **index**; the log↔run join key |
| `passed`,`skill_used` | bool | ledger | |
| `exit_code`,`num_turns` | number | ledger | |
| `cost_usd`,`duration_ms` | number | ledger / result | ranges: cost 0.016–0.736, dur 5.9K–284K ms |
| `input_tokens`,`output_tokens`,`cache_creation_tokens`,`cache_read_tokens` | number | ledger (skillfix) / result.usage | null on 48 legacy rows |
| `error` | text (max 2000) | ledger `error` / result | always null in corpus; auth-fail sample shows short strings |
| `workspace` | text | ledger `workspace` | ephemeral; 30/72 populated |
| `checks` | json | ledger `checks[]` | uniform `{id,evidence,passed}`; 4–6/row |
| `grades` | json | ledger `grades[]` | uniform `{id,evidence,passed}`; 1–4/row |
| `tool_names` | json | ledger `tool_names[]` | 3–38/row; redundant with `tool_calls` rel |
| `model_usage` | json | result `modelUsage` | per-model token/cost map |
| `provenance` | json | init (`tools`,`plugins`,`slash_commands`,`apiKeySource`,`permissionMode`,`capabilities`,`memory_paths`) | claude only |
| `log_path` | text | ledger `log_path` | index; null on 48 legacy (see §6) |
| `ts` | date | ledger `ts` | |

Indexes: `session_id` (unique), `(harness,campaign,candidate,case,config,trial)` composite, `log_path`. Volume: **24 rows/campaign (~2 KB each), 2,400 rows / ~4.7 MB at 100 campaigns.**

### `run_events` — normalized event stream

| field | PB type | notes |
|---|---|---|
| `run` | relation → runs | cascade delete; **index** |
| `seq` | number | line order within log |
| `ts` | number | ms epoch (opencode native; claude from `user.timestamp`/order) |
| `vendor`,`role` | select | role∈{assistant,tool_call,tool_result,system,result} |
| `event_type` | text | raw type/subtype (`system/init`, `tool_use`, …) |
| `tool_name`,`tool_call_id`,`status` | text | index `tool_call_id` |
| `is_error` | bool | |
| `input_tokens`,`output_tokens`,`cache_read_tokens`,`cache_write_tokens`,`cost_usd`,`wallclock_ms` | number | per-step; sparse |
| `text` | text (max 5000) | assistant/result prose (measured max 3451) |
| `payload` | json | raw event body (tool input/output live here; p95 2.7 KB, occasional >5 KB) |
| `artifact` | relation → artifacts | set when a blob is externalized |

Indexes: `run`, `tool_call_id`, `(run,seq)`. **Exclude `system/thinking_tokens`** (643 rows, pure running-counter noise) to cut ~17% of rows. Volume including them: **1,229 rows/campaign, 122,933 / 100 campaigns**; excluding thinking_tokens ≈ **1,015 rows/campaign, ~101K / 100 campaigns.**

### `tool_calls` — optional denormalized convenience (1 row per call)

Joins the claude call+result pair (or the fused opencode event) into one queryable row: `run(rel)`, `tool_call_id`, `tool_name`, `input(json)`, `output(json ≤ cap else artifact rel)`, `status`, `is_error`, `wallclock_ms`, `started_ts`. Volume: **1,003/72 → ~334/campaign, ~33,400 / 100 campaigns.** Justified because tool-level analytics (which tools, how often, error rate) is the primary eval question; without it every query re-parses `payload`.

### `artifacts` — large blobs out of the row body (justified by size)

Written-file contents and base64 screenshots dwarf everything else (images 24–75 KB each; the post-era p95 727 KB/trial is almost entirely these) and **cannot** live in a 5,000-char text field.

| field | PB type | notes |
|---|---|---|
| `run` | relation → runs | index |
| `event` | relation → run_events | |
| `kind` | select(write_content,edit_diff,screenshot,tool_output) | |
| `mime` | text | e.g. `image/png` |
| `blob` | **file** | the decoded PNG / raw content on PB disk |
| `sha256` | text | dedup key (see §5) |
| `byte_size` | number | |
| `text_ref` | text (max 5000) | short preview only |

Volume: writes ~23/campaign (median 625 B), images ~7/campaign (median 37 KB) → **~30 artifact rows/campaign; 100 campaigns ≈ 3,000 rows, ~28 MB base64 (~20 MB decoded).** Storing these as `file` (or on-disk with a pointer, §5) keeps `run_events.payload` small.

### Integration notes (do not implement here)

- **Schema lands via the extender-db `schema.py` merge-by-name path** — define these as full collection specs and let merge-by-name reconcile them; do not hand-author PATCH payloads. PB matches/updates fields by name there.
- **Avoid PATCHing collections with field defs that lack `id`s** — PB will drop-and-recreate idless fields, losing data. Create collections whole (all fields at once) or add fields through the merge path that assigns ids, never via a raw idless PATCH.
- `payload`/`input`/`output` as `json` sidesteps the 5,000-char text cap for the 2.1 % of tool payloads and the tool outputs (max 6 KB) that exceed it; `blob` as `file` for the images that exceed it by 10×.

---

## §5 Open questions for the owner

1. **Retention.** 100 campaigns ≈ 123K event rows / 167 MB raw. Keep every `run_event` forever, or keep `runs`+`tool_calls` durably and age out raw `run_events`/`artifacts` after N days? `thinking_tokens` (17% of rows) is proposed dropped at ingest — confirm nothing downstream needs the running counter.
2. **Write-event file contents: in PB or on disk with pointers?** Contents are small (median 625 B, max 5 KB) but base64 screenshots are 24–75 KB and would be the bulk of PB storage. Options: (a) `file` field in `artifacts` (self-contained, backed up with PB); (b) store on disk next to the `.log`, keep only `sha256`+path in PB. Recommend (a) for writes, and the owner's call on (b) for images given the size.
3. **Dedup of fixture-copy / mirror noise.** Measured duplication to collapse: (i) claude mirrors every tool result as **both** `message.content[].content` **and** `tool_use_result.*` — store one, keep the other in raw `payload`; (ii) opencode stores every edit diff **twice** (`metadata.diff` == `metadata.filediff.patch`, 13/13 exact) — store once; (iii) each base64 image appears in **two** claude paths in the same event. A `sha256` on `artifacts` also dedups identical fixture files read across the many trials of one case. Confirm the dedup key and which mirror is canonical.
4. **Two claude eras in one table?** `era` select + nullable post-only fields (`subagent_type`, `task_*`, `skills`, `memory_paths`) keeps one schema; alternatively version the provenance json. Recommend one table + `era`.
5. **opencode has no run-level summary.** Run cost/tokens/duration for opencode must be **derived** (sum `step_finish`, last−first timestamp) at ingest and written to `runs`. Confirm the ingester owns that rollup rather than storing nulls.

---

## Footer — re-runnable analysis

Scripts (stdlib-only) in `scratchpad/logshape/`, re-run from that dir:

| script | produces |
|---|---|
| `common.py` | shared corpus walker / flattener / percentile helpers |
| `01_corpus.py` | §1 file counts, era split, bytes/events per trial → `out_01` (stdout) |
| `02_events.py` | §2 per-vendor/era event inventory + field presence + bulk paths → `out_02_events.txt` |
| `03_ledger.py` | §5 ledger field presence (48/24 split), value ranges, checks/grades sub-shapes; §6 linkage → `out_03_ledger.txt` |
| `04_sizes.py` | §3/§4 normalized granularity counts, artifact/image sizing, volume projection → `out_04_sizes.txt` |

**Key computed numbers (verbatim stdout):**

- Corpus: 72 logs, **3,688 events, 5,242,094 bytes**; era split 24 legacy (3-tool init) / 24 post (25-tool init) / 24 opencode.
- Event counts (global): claude assistant 1,165 · thinking_tokens 643 · user 740 · init 51 · result 51 · task_progress 113 · (task_started/updated/notification/background 29/22/29/38). opencode tool_use 275 · step_start 192 · step_finish 192 · text 148.
- Tool calls: **1,003** (log-derived) == ledger `tool_names` sum (cross-validated); input+output bytes med **154** / p95 **2,705** / max **7,374**; 2.1 % > 5,000 chars.
- Write/edit content: 70 payloads, median **625 B**, max **5,076 B**, 1/70 > 5,000.
- Base64 images: **20** payloads, median **37,488 B**, max **74,588 B**, total **834,404 B**.
- Ledger: 48 legacy + 24 skillfix; fields only-in-skillfix = `campaign, log_path, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens`; cost 0.0158–0.736, duration 5,874–284,392 ms, num_turns 1–40; checks 4–6/row (uniform `{id,evidence,passed}`), grades 1–4/row; 312/342 check assertions passed (91.2 %).
- **§6 linkage:** skillfix `log_path` resolves **24/24** on disk, all point to **post-era** logs; legacy rows carry `log_path` **0/48** (no linkage — the 24 claude-legacy logs are unreferenced by the ledger).
- Projection: 24-trial campaign ≈ **1,229 event rows / 1.7 MiB**; 100 campaigns ≈ **122,933 rows / 166.6 MiB**.
