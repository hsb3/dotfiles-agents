# context-watermark

Watches session context size and nudges toward `/handoff` + `/clear` (or `/compact`)
before an overloaded context window degrades cost and performance. It estimates
context tokens from the last assistant usage block and fires once a watermark crosses.

## When it fires

Fires on every `UserPromptSubmit`, immediately on a fresh crossing, then at most every
5 prompts while still above it (anti-nag state kept per session).

## Configuration

- `CONTEXT_WATERMARK_SOFT` — default 100,000 tokens; shipped wiring sets 70,000.
- `CONTEXT_WATERMARK_HARD` — default 140,000 tokens; shipped wiring sets 100,000.
- Untouched by wiring: `CONTEXT_WATERMARK_TAIL_BYTES`, `CONTEXT_WATERMARK_REFIRE_EVERY`,
  `CONTEXT_WATERMARK_STATE_DIR`, `CONTEXT_WATERMARK_LOG_PATH`.

## Install

```
claude plugin install foreman-kit@dotfiles-agents
```

Ships only in the foreman-kit bundle, alongside the handoff skill it nudges toward.
