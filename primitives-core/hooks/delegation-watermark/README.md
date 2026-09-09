# delegation-watermark

The companion to `context-watermark`. That hook watches how much context a session is carrying;
this one watches how much labor it is **retaining**.

`PostToolUse` on edit and shell tools. It scans the session transcript, counts delegable tool
calls (`Read`, `Grep`, `Glob`, `Bash`, `Edit`, `Write`, `MultiEdit`, `NotebookEdit`) in an unbroken
run with no `Task`/`Agent` dispatch, and once that run crosses the watermark it injects a nudge
naming the number and asking the session to either dispatch the remainder or say which strategy
layer floor item this stretch is.

Observational only: it never blocks, never edits, and fails open on every error path.

## Why

The source lab's finding F7, the work-list trigger gap. A strategist that never delegates looks,
from the inside, exactly like a strategist doing careful work; the failure is only visible in
aggregate.
Transcript
reconstruction of the lab that produced this kit found sessions that ran 6+ hours with 93
self-performed tool calls and zero dispatches, and the operator noticed from the outside, not the
session from the inside.

## Calibration

Measured on the source lab's real transcripts, which is where the default came from:

| Session | Dispatches | Solo runs, in order | Verdict | Under the floor rule |
|---|---|---|---|---|
| exp3 rig + judges | 7 | 47, 21, 12, 12 | delegated; the 47 was pre-dispatch grounding by hand | **still nudges** — grounding is `Read`/`Grep` of the tree, which is exactly the delegable labor the hook is for |
| exp3 part-2 fix layer | 8 | 36, 34, 69 | delegated, then went solo for the closing stretch | **unreclassified** — a closing stretch made of `gh`/`git` review shell now shrinks below the line; one made of hand edits still fires, and the recorded counts do not say which |
| EVALS restructure / docs | 0 | 103 / 80 | never delegated | **still nudges** — hand-editing docs is not floor work under any reading |
| publish epilogue | 0 | 93 | never delegated | **unreclassified**, and the row most reduced by the rule: the `gh`/`git` publish shell around the release no longer counts, though a publish done by hand-editing files still does |

The recorded data is per-run counts, not per-call tool names, so the two "unreclassified" rows
cannot be re-measured — they are marked, not guessed.

`SOFT=25` sits above the typical mid-fan-out run (median ~18 across the delegating sessions' 14
runs) and below every zero-delegation session (80–103). It still fires on longer solo stretches
inside delegating sessions when those stretches are hand labor — deliberately: the retained-labor
shapes are the delegation skill's ceiling names, and the nudge is answerable by naming a floor
item. What changed is that the floor no longer has to be named by hand when it is visible in the
transcript (see **The floor is detected, not declared** below). `REFIRE_EVERY=15` means a session
that keeps going gets reminded roughly every 15 calls rather than on every call.

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
            "command": "DELEGATION_WATERMARK_SOFT=\"${DELEGATION_WATERMARK_SOFT:-25}\" DELEGATION_WATERMARK_REFIRE_EVERY=\"${DELEGATION_WATERMARK_REFIRE_EVERY:-15}\" DELEGATION_WATERMARK_FLOOR_COMMANDS=\"${DELEGATION_WATERMARK_FLOOR_COMMANDS:-kata,gh,make,git}\" python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/delegation-watermark/hook.py\"",
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
| `DELEGATION_WATERMARK_FLOOR_COMMANDS` | `kata,gh,make,git` | Command heads eligible to be floor, comma-separated. `kata` is this repo's tracker; a consuming repo with a different one overrides the list. Setting it **replaces** the default rather than extending it, and an empty value means no floor commands at all. A head listed here that has no subcommand allowlist (see Design notes) is floor for any subcommand |
| `DELEGATION_WATERMARK_MAX_BYTES` | `67108864` | Refuse to scan a transcript larger than this |
| `DELEGATION_WATERMARK_STATE_DIR` | `/tmp/delegation-watermark` | Per-session anti-nag state |
| `DELEGATION_WATERMARK_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/delegation-watermark.jsonl` | Ledger |

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
- **The floor is detected, not declared.** Work the delegation doctrine assigns to the
  never-delegated floor does not raise the count: a `Bash` call whose every segment is
  coordination or review shell is not counted. The rejected alternative was an acknowledgement
  that suppresses the nudge for a phase, which requires the model to declare which phase it
  believes it is in — the same self-report the hook exists to work around. The classifier reads
  only the tool name and that call's own input, and keeps no new state.
- **Floor work never resets the streak, it only fails to count.** Nothing but a real dispatch
  resets. This is what bounds the hook: 25 non-floor calls fire regardless of how much floor work
  is interleaved with them. An earlier draft treated a floor `Skill` call as a phase boundary that
  reset the streak, and a reviewer broke it in one line — 24 edits, touch the board, repeat: 288
  genuine labor calls, zero dispatches, silent forever. Touching the tracker every twenty-odd
  calls is exactly what a working session does, so that mechanism is gone rather than tuned.
- **A floor head is not enough; the subcommand has to be floor too.** `kata create`,
  `gh workflow run`, `gh secret set` and `make deploy` are substantial undelegated work wearing a
  coordination head, so each head carries an allowlist:

  | Head | Floor subcommands |
  |---|---|
  | `git` | `status`, `log`, `diff`, `show`, `fetch`, `branch`, `worktree`, `rev-list`, `rev-parse`, `merge`, `push` |
  | `gh` | `view`, `list`, `checks`, `diff`, `status`, `watch` — matched on the **second** non-flag token, since `gh` is noun-verb (`gh pr view`) |
  | `make` | no target, `ci`, `test`, `check`, `help`, `lint` |
  | `kata` | `list`, `show`, `ready`, `next`, `board`, `search`, `comment`, `meta`, `label`, `schedule`, `deadline` |

  `git rebase`, `checkout` and `switch` are absent deliberately: a long hand-driven rebase is
  labor, not review. `merge` and `push` stay, because the merge decision is floor work by
  doctrine. **A head added through the override with no entry in this table is floor for any
  subcommand** — you added the head, you own it; that is what keeps the knob usable for a repo
  whose tracker is not `kata`.
- **Mixed commands count as labor.** `git status && python3 build.py`, anything with a command
  substitution, an env-var prefix, or a path-qualified head is not floor. The nudge is worth more
  kept honest than kept quiet, so the ambiguous direction is the counting one.
- **The nudge is answerable.** Naming the floor item ("this is final validation") is an accepted
  response, so the hook does not force delegation of work that legitimately belongs to the
  session. That is deliberate: a nudge that can only be obeyed gets muted.

## Ledger

One row per fire check, appended to the `delegation-watermark` stream:

Ledgers live outside the project, in one partitioned root shared with every other hook in
this plugin (and with the opencode mirror, which writes under its own `<harness>` segment):

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl
```

Every row carries an identity envelope — `v`, `plugin`, `harness`, `stream`, `ts`
(ISO-8601 UTC), `project` — so a row stays attributable after the files are concatenated.
The append path is `hooks/_lib/agentlog.py`; no hook writes its own rows.


```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"delegation-watermark",
 "ts":"2026-08-20T15:37:08.666Z","project":"/repo/x",
 "session_id":"...","tool_name":"Edit","streak":69,"dispatches":8,
 "delegable_total":139,"ratio":17.38,"fired":true}
```

The streak distribution is the input to re-calibrating `SOFT` — see `tier-cutoff.md` for the
sibling protocol on model tiers, and `provenance.md` for what is measured versus assumed.

## Codex

Codex rollout function/custom calls are counted directly. Both native spawn spellings reset the retained-work streak; shell and patch calls count, with the existing coordination-command exemptions. Worker calls are skipped by native agent_id. A missing rollout is reported explicitly.
