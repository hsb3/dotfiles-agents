# subagent-telemetry

Appends one JSONL row per delegation (agent ID, agent type, model, context tokens) to
a local ledger, so a strategist session's own tier usage can be measured offline — data
that lives only in each subagent's own transcript, not the parent's. Purely
observational: never blocks, never injects context, prints nothing on success.

## When it fires

Fires each time a delegated subagent finishes (`SubagentStop`). Every field comes from
the delegation's own records, never the parent session's: agent type and any dispatch
model override from the sidecar Claude Code writes at
`<session>/subagents/agent-<id>.meta.json`, model and context tokens from that
subagent's own transcript beside it. The payload's `transcript_path` is the parent's
transcript, so it is used only to locate that `subagents/` directory.

`SubagentStop` also fires for agents that never get a `subagents/` entry — writing those
inflated the ledger about tenfold. A row is written only when a readable sidecar yields
an agent type; otherwise the event is dropped and nothing is logged. Row count therefore
equals delegation count.

## Configuration

Env-overridable; shipped wiring leaves all three at hook.py's built-in defaults:
- `SUBAGENT_TELEMETRY_TAIL_BYTES` — default 262,144 (256 KB transcript tail window).
- `SUBAGENT_TELEMETRY_LOG_PATH` — default `<project-root>/logs/delegation.jsonl`.
- `SUBAGENT_TELEMETRY_DEBUG` — off by default. Set it to record an error row when the
  hook itself fails; leave it off so diagnostics cannot distort the row count.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, recording delegation telemetry for the crew.
