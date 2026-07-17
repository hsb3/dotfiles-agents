# project-workflow

The session-discipline loop for a software project: plan the work, keep sessions clearable
while you build, and report out — as five skills plus two nudge hooks that keep the loop
running without you having to remember it.

## What you get

| Skill | What it does |
|---|---|
| `handoff` | Maintains a session-handoff file so a brand-new session can pick up work cold, in under ~10k tokens of reading. |
| `planning-desk` | Stands up a source-grounded planning desk — write conformant issue bodies and deep build plans, driven through a draft → review → fix → reconcile loop. |
| `comms` | Produces recurring status deliverables — a morning briefing, end-of-day wrap-up, weekly planning briefing, board readout, or product overview — as a deck, to one consistent standard. |
| `github-project-board` | Stands up and operates a single GitHub Project (v2) board serving timeline, prioritization, and day-to-day task tracking from one item set. |
| `board-triage` | The weekly routine that fills in Impact/Effort/Priority on a board so its prioritization and roadmap views stay useful instead of drifting into noise. |

Plus two nudge hooks that run automatically, not on request:

| Hook | Event | What it nudges |
|---|---|---|
| `context-watermark` | every prompt | Watches the running session's context size and, once it crosses a soft or hard token watermark, adds a one-line reminder to run `/handoff` and then `/clear` or `/compact`. Fails open — a hook error or missing data never blocks the prompt. |
| `handoff-freshness-guard` | before compaction | Blocks a **manual** `/compact` if the handoff file is stale or missing, so context isn't discarded before it's captured. Never blocks **automatic** compaction — an auto-compact near a full context window has no fallback, so it only logs and nudges instead of blocking. |

## A worked example

```
You: "wrap up"
→ handoff writes/updates the project's handoff file: current state, in-flight work,
  decisions made and pending, gotchas — a cold session can read it in one pass.

...session continues, context grows...

Context crosses the soft watermark (~70k tokens):
→ context-watermark injects: "run /handoff, then /clear (preferred) or /compact."

You run /compact without having run /handoff first:
→ handoff-freshness-guard blocks the MANUAL compact and tells you to run /handoff first.
  (An automatic compaction never blocks this way — it logs and nudges instead, so a
  long-running session can't get stuck with no way to free context.)

Later: "run board triage"
→ board-triage exports the board snapshot, finds the un-ranked/blank/stale items, sets
  Workstream/Impact/Effort/Priority by the standing rubric, and applies only the diffs.

End of week: "produce the weekly planning briefing"
→ comms assembles the deck from the same sources the planning desk and board already
  track, to the standard's format — no one-off slide deck from scratch.
```

## Honest scope

This is a workflow discipline, not a project-management platform: it assumes you already
have a GitHub repo and (for `github-project-board`/`board-triage`) a GitHub Project (v2)
board, and it operates on those directly rather than replacing them. The nudge hooks are
deliberately conservative — every failure mode they can hit resolves to "do nothing and let
the session continue," never to blocking real work.
