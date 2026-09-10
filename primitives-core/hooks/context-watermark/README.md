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
notice = min(tier_notice × complexity, 0.30 × window)
soft = min(tier_soft × complexity, 0.60 × window)
hard = min(tier_hard × complexity, 0.80 × window)
```

`window` and the model tier come from `_lib/model_catalog.json` via the model id on the
transcript's last assistant line (no hook payload carries a `model` field). The tunable,
unmeasured defaults are:

| Tier | Notice | Soft | Hard |
| --- | ---: | ---: | ---: |
| frontier | 60k | 120k | 160k |
| heavy | 96k | 192k | 256k |
| mid | 120k | 240k | 320k |
| light | 160k | 320k | 480k |

**The window caps every stage after complexity and never lifts it.** The 30/60/80 percent caps
protect small windows even when policy complexity is greater than one. An unmapped model uses the
conservative frontier defaults.

The ledger row for a model with no known window carries `window: null`
and `window_fallback: true`, because a check that could not measure must not look identical
to one that measured and found nothing.

`complexity` is a session-level proxy for how expensive each grounding read is: the tracked-file
count, `git ls-files | wc -l`, in three buckets — `< 5,000 → 1.00`, `5,000–20,000 → 0.85`,
`> 20,000 → 0.75`. A bigger repo makes each read cost more, so the nudge comes **earlier**. The
count is computed once per session and cached beside the anti-nag state, since the hook fires on
every prompt and every worker tool call. A non-git tree, or a `git` that fails, is the neutral
factor 1.00. The buckets are `[untested]` calibration, not measurement.

## Advisory actions

Warnings are advisory; they never terminate or discard work, and they grant a worker no new
authority. At notice, reduce further grounding reads. At soft, checkpoint at the next safe
boundary and finish small bounded work. At hard, preserve the branch, worktree, uncommitted
changes, and test proof in a manager-facilitated checkpoint before continuation. A verified
self-handoff may be used where available; it is never assumed.

Workers use the same tier-aware, window-capped budgets as sessions. The hook still names itself
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
  `complexity` here replaces the tracked-file factor. `notice` is clamped to `soft`, so it
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
