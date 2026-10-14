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
  the whole test. A payload without it is the main session's own tool call (next bullet). The
  wiring uses the same matcher `delegation-watermark` uses
  (`Edit|Write|MultiEdit|NotebookEdit|Bash`) rather than `*`, so the cost is bounded to the
  tool calls that actually accumulate context.
- **`PostToolUse` in the main session** — the mid-turn nudge (below).

Either way: immediately on a fresh crossing, then at most every 5 events while still above it
(anti-nag state kept per session, and separately per worker). The mid-turn nudge is the
exception: it fires at most once per session.

### The mid-turn nudge

A long autonomous turn would otherwise cross hard without a word until the next prompt, and an
auto-compaction near the window is never blocked by the handoff guard. So a main-session
`PostToolUse` measures the session with the same session stages as the prompt path and, at the
first call where the tier reaches **hard**, tells the model to update the handoff at the next
safe boundary with the handoff step of `/atelier:prepare-compact` (the `atelier:compact-handoff`
skill), then continue the task. It never asks the model to stop or compact. A `systemMessage`
tells the owner. It is suppressed:

- when `CONTEXT_WATERMARK_CYCLE_OWNER` is non-blank, since the coordinator already reads the
  session mid-turn;
- when the prompt path has already reported hard for this session (its state's `last_tier`);
- after it has fired once for this session (its own flag, in `<session>-midturn.json` beside
  the prompt path's state, so the prompt path's refire every 5 prompts is unchanged);
- on Codex, until a live probe shows Codex delivers a main-session `PostToolUse`
  `additionalContext` to the model; on Codex it neither measures nor writes a row;
- in any subagent, which takes the worker path above.

A turn of only read-only tools (`Read`, `Grep`, `Agent` and the like) is not seen, because the
matcher is `Edit|Write|MultiEdit|NotebookEdit|Bash`.

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
which outrank the activation file, and marks the session as coordinated through
`CONTEXT_WATERMARK_CYCLE_OWNER` (below).

The ledger row for a model with no known window carries `window: null`
and `window_fallback: true`, because a check that could not measure must not look identical
to one that measured and found nothing.

`complexity` is 1.0 unless the activation file's `watermark.complexity` sets it. It multiplies
every stage before the window cap applies.

## Advisory actions

Warnings are advisory; they never terminate or discard work, and they grant a worker no new
authority. At notice, reduce further grounding reads. At soft, finish the slice or dispatch in
hand and start no new one. At hard, at the next safe boundary commit or list uncommitted changes,
bring the handoff note or plan file current with test proof, and return; the dispatcher decides
continuation. A worker acts on the message as written and takes no context action on its own
estimate.

The session soft and hard texts come in two variants, and the hook picks one; the model is
never asked whether a coordinator exists. `CONTEXT_WATERMARK_CYCLE_OWNER` in the session's
environment selects it:

| `CONTEXT_WATERMARK_CYCLE_OWNER` | Session text |
| --- | --- |
| absent or blank (the default) | Run the `atelier:compact-handoff` skill, naming `/atelier:prepare-compact` as its Claude Code command (Codex ships only the skill): at soft at the next safe boundary, to update the handoff and prepare compaction; at hard now. |
| any non-blank value (wave-lanes writes `coordinator`) | Update the handoff, touch its freshness stamp last, then stop and wait for the coordinator; do not compact. At soft at the next safe boundary, at hard now. |

The worker texts do not read the marker.

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
subagent row also carries `agent_id`. A main-session `PostToolUse` row is a session row plus
`event: "PostToolUse"`, written on every check, and a hard row the nudge did not fire on also
carries `suppressed` (`cycle-owner`, `prompt-reported-hard` or `already-fired`).

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
