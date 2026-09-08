# context-watermark

Watches context size and nudges toward `/handoff` + `/clear` (or `/compact`) before an
overloaded window degrades cost and performance. It estimates context tokens from the last
assistant usage block in the transcript and fires once a watermark crosses. Both the session
and its delegated workers are watched.

## When it fires

- **`UserPromptSubmit`** — the session's own context, against a soft and a hard tier.
- **`PostToolUse`** — a delegated worker's context, against a soft tier only. This event
  fires in the parent too, and only a worker's payload carries `agent_id`; that presence is
  the whole test, and a payload without it produces no output and no ledger row. The wiring
  uses the same matcher `delegation-watermark` uses
  (`Edit|Write|MultiEdit|NotebookEdit|Bash`) rather than `*`, so the cost is bounded to the
  tool calls that actually accumulate context.

Either way: immediately on a fresh crossing, then at most every 5 events while still above it
(anti-nag state kept per session, and separately per worker).

## The thresholds

```
soft = min(120_000, 0.60 × window) × complexity
hard = min(160_000, 0.80 × window) × complexity
```

`window` is the lead model's context window, read from `_lib/model_catalog.json` via the model
id on the transcript's last assistant line (no hook payload carries a `model` field).

**The window caps the threshold and never lifts it.** `delegation/references/provenance.md`'s
`[cost]` row anchors the measured degradation band to an ABSOLUTE token count, so a pure
fraction of a 1M-token window would overturn a measurement rather than scale it. At a 200k
window the formula reproduces the previously shipped 120k/160k exactly; at 1M it stays at
120k/160k; at 64k it drops to 38.4k/51.2k.

**Unknown model, or a model the catalog has no window for: the absolute pair, 120k/160k** —
never a fraction of an assumed window. The ledger row for that check carries `window: null`
and `window_fallback: true`, because a check that could not measure must not look identical
to one that measured and found nothing.

`complexity` is a session-level proxy for how expensive each grounding read is: the tracked-file
count, `git ls-files | wc -l`, in three buckets — `< 5,000 → 1.00`, `5,000–20,000 → 0.85`,
`> 20,000 → 0.75`. A bigger repo makes each read cost more, so the nudge comes **earlier**. The
count is computed once per session and cached beside the anti-nag state, since the hook fires on
every prompt and every worker tool call. A non-git tree, or a `git` that fails, is the neutral
factor 1.00. The buckets are `[untested]` calibration, not measurement.

## The subagent tier

A worker gets **soft only, at 0.5× the session's soft line, and no hard tier**. It cannot hand
off, compact, or start a fresh session — the only move it has is to finish — so the nudge names
that move ("wrap up and report now") instead of offering commands it does not have. A bare
"you are at 60% of context" is the unactionable message this deliberately avoids.

Three properties of that text are load-bearing, and a live worker's refusal (2026-09-08) is why.
It **names its sender** (`atelier context-watermark:`), because an unattributed instruction to
truncate a task is indistinguishable from prompt injection and the worker said so. It states the
number as a **quality line from a measured degradation band, explicitly not the model's context
limit**, because a worker can see its own remaining budget — millions of tokens, in the probe —
and reads any smaller threshold as a false claim of exhaustion. And it grants that **finishing
genuinely small remaining work first is an acceptable answer**, so a worker that is right to keep
going has somewhere to go that is not a fight with the hook.

Its context is read from the worker's OWN transcript. **Inside a worker, `transcript_path`
names the MAIN SESSION transcript** (measured 2026-09-08); the worker's is at
`<transcript_path minus .jsonl>/subagents/agent-<agent_id>.jsonl`. Measuring the payload's path
would silently report the parent's size. A derived path that does not exist logs and exits 0.

The nudge reaches the worker as
`{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}` —
the shape a subagent acts on. `UserPromptSubmit` keeps its TOP-LEVEL `additionalContext`.

## Configuration

Precedence, highest first, applied per value: **environment variable → the `watermark:` key in
`.claude/atelier.local.md` → the computed default**. Absent, blank, or unparseable at either
level falls through to the next and never errors.

- `CONTEXT_WATERMARK_SOFT`, `CONTEXT_WATERMARK_HARD` — absolute token counts. **The wiring
  supplies no default for these**, deliberately: a shell-expanded `${VAR:-120000}` always sets
  the variable, and since env is the top tier the computed default could never apply.
- `watermark:` in the activation file, every sub-key optional:

  ```yaml
  watermark:
    soft: 90000
    hard: 130000
    complexity: 0.9
  ```

  A sub-key that is missing, blank, or not a positive number leaves that one computed;
  `complexity` here replaces the tracked-file factor. `activation.py check` reports the key
  through this hook's own loader.
- Untouched by wiring: `CONTEXT_WATERMARK_TAIL_BYTES`, `CONTEXT_WATERMARK_REFIRE_EVERY`,
  `CONTEXT_WATERMARK_STATE_DIR`, `CONTEXT_WATERMARK_LOG_PATH`, `ATELIER_ACTIVATION_FILE`.

## Ledger

One row per check, appended to the `context-watermark` stream:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/context-watermark.jsonl
```

Each row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`, `project`)
plus `scope` (`session` or `subagent`), `session_id`, `ctx_tokens`, `tier` (`none`, `soft`, or
`hard`), `fired`, `model`, `window`, `window_fallback`, `complexity`, `soft`, `hard` (null for a
worker), and `sources` naming which tier of the precedence chain supplied each value.

`sources` describes the **session's** resolution, and it carries no `hard` key on a worker row,
where there is no hard tier to resolve. A worker's `soft` is that resolved session line multiplied
by `subagent_soft_ratio`, and the row carries both terms (`session_soft`, `subagent_soft_ratio`)
so `sources.soft: "env"` beside `soft: 60000` is readable rather than contradictory. A subagent
row also carries `agent_id`.

Two row shapes are narrower than that. A row from a handled error path (no transcript, no usage
block, no worker transcript) carries `null` `ctx_tokens`, `tier: "none"`, `fired: false` and an
`error`, with `window`/`complexity`/`soft`/`hard` null and no `sources`. A row from the outer
fail-open handler is narrower still — `session_id`, `ctx_tokens`, `tier`, `fired`, `error` and a
truncated `traceback`, and **none** of `scope`, `model`, `window`, `window_fallback`,
`complexity`, `soft` or `hard` — because by then the payload itself may be what failed.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships only in the atelier bundle, alongside the handoff skill it nudges toward.
