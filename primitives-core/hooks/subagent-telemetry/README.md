# subagent-telemetry

Appends one JSONL row per delegation (agent ID, agent type, model, context tokens, start
time, duration) to a local ledger, so a strategist session's own tier usage and per-agent
wall clock can be measured offline — data that lives only in each subagent's own sidecar
and transcript, not the parent's. It also appends a `stall` row naming delegations that
started and never settled. Purely observational: never blocks, never injects context,
prints nothing.

## When it fires

**`SubagentStop`** — each time a delegated subagent finishes. Every field comes from the
delegation's own records, never the parent session's: agent type and any dispatch model
override from the sidecar Claude Code writes at
`<session>/subagents/agent-<id>.meta.json`, model and context tokens from that subagent's
own transcript beside it. The payload's `transcript_path` is the parent's transcript, so
it is used only to locate that `subagents/` directory.

`SubagentStop` also fires for agents that never get a `subagents/` entry — writing those
inflated the ledger about tenfold. A row is written only when a readable sidecar yields
an agent type; otherwise the event is dropped and nothing is logged. Delegation row count
therefore equals delegation count.

### When a `/clear` splits a delegation from its sidecar

Clearing the session mid-delegation re-homes the still-running agent's transcript under a
new session id and leaves its sidecar behind under the old one — measured on a live pair:
one agent, two session directories under one slug, exactly one `.meta.json`. Looking the
sidecar up only in the payload's own directory therefore drops the row for the delegation
with the longest wall clock, the one most worth measuring.

So on a miss — and only on a miss — the lookup probes sibling session directories under
the same slug for that one exact filename, most recently modified first, stopping after
`SIBLING_PROBE_LIMIT` of them (12; the two halves of a re-home are adjacent in time, while
a slug can hold hundreds of sessions). It never leaves the slug and never looks for
anything but that filename. Past the cap the row is dropped exactly as it was before.

When the two halves are split they answer different questions. `started_at` comes from the
**sidecar's** half, which holds the true beginning: the re-homed transcript is only the
resumed tail, so reading it would restart the clock at the `/clear`. `duration_ms`
therefore spans the clear, which is the honest wall clock for an agent that kept running
through it. Context tokens come the other way round, from the **payload's** half, which is
the live one carrying the delegation's final context.

**`Stop`** — when the session's own turn ends. No delegation row is possible (a `Stop`
payload carries no `agent_id`); it only runs the stall scan below, which the
`SubagentStop` path also runs after writing its row.

## Wall clock

`started_at` comes from the first line of the subagent's own transcript that carries a
`timestamp`, read from a bounded 64 KB head. Walking forward matters: 4 of 44 real
transcripts open with a `fork-context-ref` line that has no timestamp. Measured against
11 real delegations that source lands +0.04–0.06s after true dispatch. The fallback, used
only when no line in that window yields a timestamp, is the sidecar's mtime — accurate to
+0.1s in 9 of those 11 cases but adrift by 409s and 664s in the other two, which is why it
is the fallback and not the primary. `duration_ms` is `now − started_at` at hook run time,
directly comparable with the row's own `ts`. When the start time is unknown both keys are
null and the row is still written; losing a delegation record over a missing timestamp
would be the worse outcome.

## Stall rows

A delegation that started but has not settled for `SUBAGENT_TELEMETRY_STALL_SECONDS`
produces one `stall` row per settle event, at most:

```
{"event": "stall", "session_id": "…",
 "pending": [{"agent_id": "…", "agent_type": "…", "started_at": "…", "pending_ms": 1234}]}
```

What counts as started is the set of `agent-*.meta.json` sidecars in the session's
`subagents/` directory — the same predicate that gates a delegation row, so an event for
an agent that never got a sidecar can neither produce a row nor be reported pending. What
counts as settled comes from a bounded 256 KB tail of the ledger: delegation rows, plus
every agent already named in a `stall` row, which is what keeps a stalled agent named once
per window rather than at every subsequent settle. Entries are sorted by `agent_id`.

Settled matches on `agent_id` alone, ignoring which session recorded the row. That is what
closes the other half of the re-homing defect: the stop row lands under the new session id
while the orphaned sidecar sits under the old one, so a session-filtered settled set could
never see it and the agent would be reported pending past every threshold, forever. Agent
IDs are globally unique, and the worst a collision could cost is one missed stall row,
never a false one.

**The started set stays in the current session's directory, and that asymmetry with the
sidecar fallback is the design.** Every historical session under the slug holds sidecars
whose delegation rows aged out of the 256 KB window long ago; sweeping them in would
report every delegation the project has ever run as stalled, at every `Stop`.

The scope is the whole session's `subagents/` directory, not just the delegations the
settling agent itself started, so a `SubagentStop` can name a sibling's pending work.
That widening is deliberate: narrowing it by `parentAgentId` would hide a stalled
grandchild from the main agent's `Stop`, which is the case most worth catching.

Edge cost of that 256 KB window (roughly 800 rows), stated rather than hidden: a
delegation whose stop row has scrolled out of it looks un-stopped, so if its sidecar is
still in the session directory and it is past the threshold it is named pending once more
before the fresh stall row suppresses it again.

## Reading the ledger

**A row with neither an `event` key nor an `error` key is a delegation row.** Stall rows
carry `event`; the opt-in `SUBAGENT_TELEMETRY_DEBUG` rows carry `error` and no `event`, so
the `event` key alone does not separate them. That rule is exact for every row written
before stall rows existed — those rows additionally lack `started_at` and `duration_ms`,
which reads as an unknown start time, because it was never recorded.

## Configuration

Env-overridable; shipped wiring leaves all four at hook.py's built-in defaults
(`SIBLING_PROBE_LIMIT` is a module constant, not an env knob):
- `SUBAGENT_TELEMETRY_STALL_SECONDS` — default 900 (15 minutes) before a still-pending
  delegation is reported as stalled.
- `SUBAGENT_TELEMETRY_TAIL_BYTES` — default 262,144 (256 KB), the window for both the
  transcript usage read and the ledger settled-set read.
- `SUBAGENT_TELEMETRY_LOG_PATH` — default `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/delegation.jsonl` (stream name
  `delegation`, kept from the ledger's original filename so old and new rows read as
  one series).
- `SUBAGENT_TELEMETRY_DEBUG` — off by default. Set it to record an error row when the
  hook itself fails; leave it off so diagnostics cannot distort the row count.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, recording delegation telemetry for the crew.

## Codex

Codex rows use the shared native worker registry and each worker rollout for identity, model, context, start time, and duration. SubagentStop marks the registry stopped without deleting the checkout; validated resumed tool activity marks it running again in the worker router. Registry entries also supply pending workers for stall reports. Missing usage is recorded and surfaced, never silently reported as zero.

Codex SubagentStop names the parent in `transcript_path`. Measurements use the child transcript validated and stored at SubagentStart, so parent tokens, model and start time cannot be attributed to the worker. Before an initialized child rollout emits usable usage, telemetry records null context with `pending: true`; malformed or unavailable child usage remains an explicit measurement error.
# Codex usage stream

Codex stop observations also append codex-usage.jsonl. Rows use envelope
v 2, schema codex-usage, and schema_version 2. Each token_count contributes
one deterministic delta row: tokens holds input, cached_input, output,
reasoning, and total increments, while cumulative_tokens holds the observed
runtime counter. Cached input is a subset of input; reasoning is a subset of
output. A total-counter reset emits an unknown reset marker plus an observed
initial delta for the new segment. A category decrease without a total decrease
emits only the unknown marker and establishes a new baseline; unchanged lifetime
counters are never billed again. Counters are segmented on a reset, so a digest must sum tokens within
each segment instead of summing cumulative_tokens.

Every row includes observation_id, segment, counter_state, lifecycle_id,
native_id, parent_id, role, model, effort, requested_model, requested_tier,
package_path, package_name, package_version, profile_path, profile_hash,
host, source_repo, effective_cwd, started_at, timing, and tokens. package_path
is the actual directory containing the helper; name/version are read only from
an adjacent plugin manifest when present. profile_path/hash are emitted only
for an explicit readable payload path. These values describe files, not proof
that a package or profile was loaded at runtime. Requested model/tier remain
null unless the native payload supplied them. The stable id hashes host, native identity, source occurrence, model,
and counter data; a digest may deduplicate it but the hook deliberately keeps
durable JSONL append-only. Root rows use the session_meta id; child rows use
the native child id and parent_thread_id. Active, tool, and wait timing remain
null when the runtime does not measure them; lifetime_ms is populated when
both transcript timestamps exist.

counter_state is observed, reset, pending, missing, malformed-delta,
malformed-json, unsupported-future-schema, error, or
inherited-baseline-unknown. Each non-observed state has null counters and
must remain visible to import/export consumers; no state means zero usage.
Rows exclude prompts, transcripts, secrets, and message content. Exporters
should preserve complete rows and importers must retain unknown states and
deduplicate only exact observation_id values.

Example observed row:

    {"v":2,"schema":"codex-usage","schema_version":2,"kind":"delta",
     "counter_state":"observed","segment":0,"native_id":"child",
     "package_path":"/path/primitives-core","package_name":null,
     "package_version":null,"profile_path":null,"profile_hash":null,
     "tokens":{"input":12,
     "cached_input":8,"output":4,"reasoning":1,"total":16},
     "cumulative_tokens":{"input":100,"cached_input":80,"output":20,
     "reasoning":2,"total":120}}
