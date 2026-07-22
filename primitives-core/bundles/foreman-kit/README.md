# foreman-kit

A context-and-cost optimization kit for multi-agent work: size a task, pick a delegation
architecture, dispatch to the right model tier, and keep every session clearable instead of
letting context quietly run out. Three skills, four hooks, and four agents across model tiers,
all wired to the same handoff file and the same session-discipline loop.

## What you get

| Primitive | Type | What it does |
|---|---|---|
| `foreman` | skill | Size a substantial task and run the session as a foreman: pick a delegation architecture (five options), bind slices to model-tiered agents, hold the never-delegated floor, and apply the findings-backed context-hygiene defaults. Two-level effort calibration — standard for an Opus-led session, deep for a Fable-led one. |
| `handoff` | skill | Maintain the project's session-handoff file so a brand-new session can pick up work cold — the externalization pass that makes a session clearable. |
| `waves` | skill | Drive a repo's issue backlog to closed with near-zero owner input: refresh a pinned triage issue (the living, ranked plan), group buildable issues into branch-sized waves, launch isolated crews via `foreman`, verify and merge each PR in declared order, reconcile, and externalize. Owner-gated decisions are queued and batched, never delegated. |
| `scout` | agent | Read-only recon — locate definitions, confirm presence/absence, inventory a scope, or reconcile evidence across files; returns a conclusion with path:line evidence, never a file dump. Defaults to the cheapest model tier. |
| `builder` | agent | Scoped implementation working inside an owned file list against explicit acceptance criteria. Defaults to a mid tier; dispatched at a higher tier for coupled or costly-to-unwind slices. |
| `reviewer` | agent | Adversarial, report-only verification — re-derives each claim from its cited source and re-runs its commands; never edits or fixes. |
| `lead` | agent | Drives a coupled dependent chain, spawns its own bounded-link workers, and verifies before reporting a proof package — for chains too coupled to parallelize. |
| `context-watermark` | hook (`UserPromptSubmit`) | Warns when session context crosses the soft (70k) / hard (100k) token watermarks and nudges toward `/handoff` then `/clear` or `/compact`. Fails open; never blocks a prompt. |
| `handoff-freshness-guard` | hook (`PreCompact`) | Blocks a **manual** `/compact` when the project's handoff is stale or missing (run `/handoff` first); never blocks auto-compaction — fails open with non-blocking guidance instead. |
| `session-handoff-surfacer` | hook (`SessionStart`) | On a genuine cold start (startup or `/clear`), surfaces the existing handoff as a pointer plus a capped excerpt so a fresh session picks up prior work. Silent no-op on resume/compact or when no handoff exists. |
| `subagent-telemetry` | hook (`SubagentStop`) | Appends one row per delegation (agent id, agent type, model, context tokens) to a local ledger, so tier usage can be measured offline. Silent — no stdout, never blocks. |

## A worked example

```
You: "build the export feature — plan it out"
→ foreman sizes the job, picks a delegation architecture, and dispatches scoped slices to
  builder agents at the right model tier, holding verification for itself.

Context creeps past 70k tokens
→ context-watermark nudges: run /handoff, then /clear or /compact.

You: "/handoff"
→ handoff externalizes everything load-bearing into the project's HANDOFF.md.

You try a manual /compact with a stale handoff
→ handoff-freshness-guard blocks it and tells you to run /handoff first.

You /clear and start a new session
→ session-handoff-surfacer greets the fresh session with the handoff's pointer + excerpt,
  so it picks up cold without re-deriving prior state.

Meanwhile, every delegation
→ subagent-telemetry quietly logs agent/model/token usage for later review.
```

## Honest scope

The hooks are nudges and guards, not enforcement of correctness: `context-watermark` and
`handoff-freshness-guard` fail open on any error rather than risk wedging a session, and
neither blocks automatic compaction. `subagent-telemetry` only records what a subagent's own
transcript reports — it cannot see or influence the parent session. The delegation agents
(`scout`/`builder`/`reviewer`/`lead`) are personas for `foreman` to dispatch; they don't run
unless something explicitly delegates to them.
