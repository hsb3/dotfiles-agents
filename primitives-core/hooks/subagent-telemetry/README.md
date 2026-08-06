# subagent-telemetry

Appends one JSONL row per delegation (agent ID, agent type, model, context tokens) to
a local ledger, so a foreman session's own tier usage can be measured offline — data
that lives only in each subagent's own transcript, not the parent's. Purely
observational: never blocks, never injects context, prints nothing on success.

## When it fires

Fires each time a delegated subagent finishes (`SubagentStop`) — model and token usage
come from the subagent's own transcript tail, since the payload carries no model field.

## Configuration

Env-overridable; shipped wiring leaves both at hook.py's built-in defaults:
- `SUBAGENT_TELEMETRY_TAIL_BYTES` — default 262,144 (256 KB transcript tail window).
- `SUBAGENT_TELEMETRY_LOG_PATH` — default `<project-root>/logs/delegation.jsonl`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, recording delegation telemetry for the crew.
