# context-watermark

Watches session context size and nudges toward `/handoff` + `/clear` (or `/compact`)
before an overloaded context window degrades cost and performance. It estimates
context tokens from the last assistant usage block and fires once a watermark crosses.

## When it fires

Fires on every `UserPromptSubmit`, immediately on a fresh crossing, then at most every
5 prompts while still above it (anti-nag state kept per session).

## Configuration

- `CONTEXT_WATERMARK_SOFT` — shipped wiring defaults to 120,000 tokens; your environment wins.
- `CONTEXT_WATERMARK_HARD` — shipped wiring defaults to 160,000 tokens; your environment wins.
- Untouched by wiring: `CONTEXT_WATERMARK_TAIL_BYTES`, `CONTEXT_WATERMARK_REFIRE_EVERY`,
  `CONTEXT_WATERMARK_STATE_DIR`, `CONTEXT_WATERMARK_LOG_PATH`.

## Ledger

One row per `UserPromptSubmit` check, appended to the `context-watermark` stream:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/context-watermark.jsonl
```

Each row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`, `project`)
plus `session_id`, `ctx_tokens`, `tier` (`none`, `soft`, or `hard`), and `fired` (bool). A row
written from the fail-open error path carries `null` `ctx_tokens`, `tier: "none"`,
`fired: false`, `error`, and a truncated `traceback` instead.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it nudges toward.
