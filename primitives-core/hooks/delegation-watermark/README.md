# delegation-watermark

The companion to `context-watermark`. That hook watches how much context a session is carrying;
this one watches how much labor it is **retaining**.

`PostToolUse` on edit and shell tools. It scans the session transcript, counts delegable tool
calls (`Read`, `Grep`, `Glob`, `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit`) in an unbroken
run with no `Task`/`Agent` dispatch, and once that run crosses the watermark it injects a nudge
naming the number and asking the session to either dispatch the remainder or say which foreman
floor item this stretch is.

Observational only: it never blocks, never edits, and fails open on every error path.

## Why

The source lab's finding F7, the work-list trigger gap. A foreman that never delegates looks, from
the inside, exactly like a foreman doing careful work; the failure is only visible in aggregate.
Transcript
reconstruction of the lab that produced this kit found sessions that ran 6+ hours with 93
self-performed tool calls and zero dispatches, and the operator noticed from the outside, not the
session from the inside.

## Calibration

Measured on the source lab's real transcripts, which is where the default came from:

| Session | Dispatches | Solo runs, in order | Verdict |
|---|---|---|---|
| exp3 rig + judges | 7 | 47, 21, 12, 12 | delegated; the 47 was pre-dispatch grounding by hand |
| exp3 part-2 fix layer | 8 | 36, 34, 69 | delegated, then went solo for the closing stretch |
| EVALS restructure / docs | 0 | 103 / 80 | never delegated |
| publish epilogue | 0 | 93 | never delegated |

`SOFT=25` sits above the typical mid-fan-out run (median ~18 across the delegating sessions' 14
runs) and below every zero-delegation session (80–103). It also fires on the longer solo stretches
inside delegating sessions (36–69 observed) — deliberately: those stretches were grounding and
closing work done by hand, the retained-labor shapes the foreman skill's ceiling names, and the
nudge is answerable by naming a floor item. `REFIRE_EVERY=15` means a session that keeps going
gets reminded roughly every 15 calls rather than on every call.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other four hooks are wired:
   `ln -s ../../../primitives-core/hooks/delegation-watermark plugins/atelier/hooks/delegation-watermark`
3. Add a roster row to `primitives-core.yaml` (id `delegation-watermark`, type `hook`, source
   `primitives-core/hooks/delegation-watermark`, origin `authored`, disposition `qualified`,
   targets `[claude-code]`) — `make ci` reconciles the roster against disk and requires every
   field, `targets` included.
4. Add the `PostToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "hooks": [
          {
            "command": "DELEGATION_WATERMARK_SOFT=\"${DELEGATION_WATERMARK_SOFT:-25}\" DELEGATION_WATERMARK_REFIRE_EVERY=\"${DELEGATION_WATERMARK_REFIRE_EVERY:-15}\" python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/delegation-watermark/hook.py\"",
            "statusMessage": "Checking delegation watermark...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `DELEGATION_WATERMARK_SOFT` | `25` | Solo-run length that triggers the first nudge |
| `DELEGATION_WATERMARK_REFIRE_EVERY` | `15` | Further calls before nudging again |
| `DELEGATION_WATERMARK_MAX_BYTES` | `67108864` | Refuse to scan a transcript larger than this |
| `DELEGATION_WATERMARK_STATE_DIR` | `/tmp/delegation-watermark` | Per-session anti-nag state |
| `DELEGATION_WATERMARK_LOG_PATH` | `$CLAUDE_PROJECT_DIR/logs/delegation-watermark.jsonl` | Ledger |

## Design notes

- **Whole-transcript scan, not a tail window.** The first draft read a 512 KB tail and fired on a
  session that had genuinely delegated eight times, because the window did not reach back to the
  last dispatch. A full scan costs ~4 ms on a 2 MB transcript (~25 ms end-to-end including
  interpreter startup) because a substring test rejects non-tool lines before any JSON parsing. A
  tail window buys nothing and lies.
- **Subagents are skipped.** When the payload carries `agent_id`, the hook exits silently: a
  worker delegating is not the behavior this encourages. Sidechain records in the parent
  transcript are skipped for the same reason.
- **Bookkeeping does not count.** `TodoWrite`, `Skill`, `AskUserQuestion` and similar are session
  overhead, not labor a cheaper agent could have done.
- **The nudge is answerable.** Naming the floor item ("this is final validation") is an accepted
  response, so the hook does not force delegation of work that legitimately belongs to the
  session. That is deliberate: a nudge that can only be obeyed gets muted.

## Ledger

One row per fire check, appended to `logs/delegation-watermark.jsonl`:

```json
{"session_id":"...","tool_name":"Edit","streak":69,"dispatches":8,
 "delegable_total":139,"ratio":17.38,"fired":true}
```

The streak distribution is the input to re-calibrating `SOFT` — see `tier-cutoff.md` for the
sibling protocol on model tiers, and `provenance.md` for what is measured versus assumed.
