# context-watermark

Activation location follows the [shared selection rules](../../skills/activation/SKILL.md):
fresh Codex projects use `.codex/atelier.local.md`; Claude Code and Codex legacy fallback
use `.claude/atelier.local.md`. Explicit overrides win; policies are never merged.

Watches context size and issues an advisory before a session gets difficult to continue. It
estimates context tokens from the last assistant usage block in the transcript and fires once a
watermark crosses. Both the session and its delegated workers are watched.

## When it fires

- **`UserPromptSubmit`** — the session's own context, against notice, soft, and hard stages.
- **`PostToolUse`** — a delegated worker's context, against those same stages. This event
  fires in the parent too, and only a worker's payload carries `agent_id`; that presence is
  the whole test, and a payload without it produces no output and no ledger row. The wiring
  uses the same matcher `delegation-watermark` uses
  (`Edit|Write|MultiEdit|NotebookEdit|Bash`) rather than `*`, so the cost is bounded to the
  tool calls that actually accumulate context.

Either way: immediately on a fresh crossing, then at most every 5 events while still above it
(anti-nag state kept per session, and separately per worker).

## The stages

```
notice = min(layer_notice × complexity, 0.30 × window)
soft = min(layer_soft × complexity, 0.60 × window)
hard = min(layer_hard × complexity, 0.80 × window)
```

The layer is `worker` when the payload carries `agent_id`, `session` otherwise. `window` comes
from `_lib/model_catalog.json` via the model id on the transcript's last assistant line (no
hook payload carries a `model` field). The tunable defaults are:

| Layer | Notice | Soft | Hard |
| --- | ---: | ---: | ---: |
| worker | 100k | 160k | 250k |
| session | 150k | 250k | 400k |

**The window caps every stage after complexity and never lifts it.** The 30/60/80 percent caps
protect small windows even when complexity is greater than one; an unmapped model gets the layer
values uncapped. Complexity is 1.0 unless the activation file sets it. Under `watermark:`, a
`worker:` or `session:` sub-mapping overrides the flat keys for that layer, in either nested or
flow form (`session: {soft: 200000}`). An external coordinator such as wave-lanes sets the
session numbers through `CONTEXT_WATERMARK_NOTICE/_SOFT/_HARD` in the session's environment,
which outrank the activation file.

The ledger row for a model with no known window carries `window: null`
and `window_fallback: true`, because a check that could not measure must not look identical
to one that measured and found nothing.

`complexity` is 1.0 unless the activation file's `watermark.complexity` sets it. It multiplies
every stage before the window cap applies.

## Advisory actions

Warnings are advisory; they never terminate or discard work, and they grant a worker no new
authority. At notice, reduce further grounding reads. At soft, checkpoint at the next safe
boundary and finish small bounded work. At hard, preserve the branch, worktree, uncommitted
changes, and test proof in a manager-facilitated checkpoint before continuation. A verified
self-handoff may be used where available; it is never assumed.

Workers use the worker band, window-capped the same way as sessions. The hook still names itself
(`atelier context-watermark:`), so the advisory is attributable rather than an untrusted task
instruction.

Its context is read from the worker's OWN transcript. **Inside a worker, `transcript_path`
names the MAIN SESSION transcript** (measured 2026-09-08); the worker's is at
`<transcript_path minus .jsonl>/subagents/agent-<agent_id>.jsonl`. Measuring the payload's path
would silently report the parent's size. A derived path that does not exist logs and exits 0.

The nudge reaches the worker as
`{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}` —
the shape a subagent acts on. `UserPromptSubmit` keeps its TOP-LEVEL `additionalContext`.

## Configuration

Precedence, highest first, applied per value: **environment variable → the `watermark:` key in
the selected `atelier.local.md` → the computed default**. Absent, blank, or unparseable at either
level falls through to the next and never errors.

- `CONTEXT_WATERMARK_NOTICE`, `CONTEXT_WATERMARK_SOFT`, `CONTEXT_WATERMARK_HARD` — absolute
  token counts. **The wiring
  supplies no default for these**, deliberately: a shell-expanded `${VAR:-120000}` always sets
  the variable, and since env is the top tier the computed default could never apply.
- `watermark:` in the activation file, every sub-key optional:

  ```yaml
  watermark:
    notice: 45000
    soft: 90000
    hard: 130000
    complexity: 0.9
  ```

  A sub-key that is missing, blank, or not a positive number leaves that one computed;
  `complexity` here overrides the computed default of 1.0. `notice` is clamped to `soft`, so it
  cannot become a later stage. `activation.py check` reports the key through this hook's own
  loader.
- Untouched by wiring: `CONTEXT_WATERMARK_TAIL_BYTES`, `CONTEXT_WATERMARK_REFIRE_EVERY`,
  `CONTEXT_WATERMARK_STATE_DIR`, `CONTEXT_WATERMARK_LOG_PATH`, `ATELIER_ACTIVATION_FILE`.

## Ledger

One row per check, appended to the `context-watermark` stream:

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/context-watermark.jsonl
```

Each measured row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`,
`project`) plus `scope` (`session` or `subagent`), `session_id`, `ctx_tokens`, `tier` (`none`,
`notice`, `soft`, or `hard`), `fired`, `model`, `window`, `window_fallback`, `complexity`,
`notice`, `soft`, `hard`, and `sources` naming which precedence tier supplied each value. A
subagent row also carries `agent_id`.

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

## Codex

With `ATELIER_HARNESS=codex`, occupancy comes from the latest rollout `token_count.info.last_token_usage.total_tokens`; cached input is not counted twice. The effective runtime `model_context_window` supplies the denominator (258,400 in the measured 0.153.4 run). Cumulative billing totals and the API model maximum are not occupancy. Post-compaction estimates replace earlier measurements. Before an initialized rollout emits usable usage, the ledger records `ctx_tokens: null` and `pending: true`; malformed or unavailable data still produces an explicit diagnostic, never a zero or a passing verdict.
