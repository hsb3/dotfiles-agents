# context-watermark

Watches session context size and nudges toward `/handoff` + `/clear` (or `/compact`)
before an overloaded context window degrades cost and performance. It estimates
context tokens from the last assistant usage block and fires once a watermark crosses.

## When it fires

Fires on every `UserPromptSubmit`, immediately on a fresh crossing, then at most every
5 prompts while still above it (anti-nag state kept per session).

## Configuration

- `CONTEXT_WATERMARK_SOFT` — shipped wiring defaults to 70,000 tokens; your environment wins.
- `CONTEXT_WATERMARK_HARD` — shipped wiring defaults to 100,000 tokens; your environment wins.
- Untouched by wiring: `CONTEXT_WATERMARK_TAIL_BYTES`, `CONTEXT_WATERMARK_REFIRE_EVERY`,
  `CONTEXT_WATERMARK_STATE_DIR`, `CONTEXT_WATERMARK_LOG_PATH`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it nudges toward.
