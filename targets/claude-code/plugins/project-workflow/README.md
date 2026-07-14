# project-workflow

Run a software project through the **session-discipline loop** — the working rhythm
this plugin exists to support:

1. **Plan the work** — turn intent into conformant GitHub issues and source-grounded
   plans, and stand up a board that holds the single work-state truth.
2. **Keep sessions clearable** — externalize everything load-bearing into a durable
   handoff and a known repo structure, so a brand-new session picks up cold with nothing
   lost.
3. **Delegate down-tier** — plan and hand off in a shape a cheaper agent can execute
   against, keeping expensive context for judgment.
4. **Report out** — produce the status briefing, board digest, and honest README that
   tell a human what actually changed.

## Why this exists

Long-running project work leaks state into the context window: the plan lives in one
session's head, "what's done" drifts from the tracker, and the next session (or the next
agent) restarts from guesswork. The cost shows up as re-derived context, stale boards, and
handoffs that omit the one fact that mattered. This plugin packages the loop that keeps a
project legible across sessions and across agents — plan it, write the plan down where the
next session will find it, and report out from the tracker rather than from memory.

## What you get today

Eleven skills, grouped by the loop beat they serve:

| Beat | Skills | What they do |
|---|---|---|
| Plan | `planning-desk`, `github-project-board`, `board-triage` | Author conformant issue bodies and deep build plans; stand up and operate a GitHub Project (v2) board; rank the backlog by Impact × Effort. |
| Keep clearable | `handoff`, `mise-en-place-scaffold`, `repo-compliance-audit`, `repo-meta-structure`, `memory-taxonomy` | Maintain a cold-start handoff file; scaffold and audit the `_meta/`/`.claude/` structure a session expects; the meta-structure and memory-taxonomy standards the audit/scaffold read. |
| Report out | `comms`, `readme-value-and-proof` | Produce status briefings and board digests; turn a README into an honest value proposition backed by real proof. |
| Adjacent | `private-fork` | Stand up and run a private mirror of an upstream repo, with a recurring upstream-review cadence. |

Invoke any of them by name; they trigger on natural requests too ("wrap up the session",
"write me an issue", "run board triage"). A few terminal examples — the visual proof for a
process plugin is the invocation itself, not a screenshot:

```
# Plan: draft a real issue body (deliverables · acceptance criteria · parallelism)
/project-workflow:planning-desk

# Keep clearable: externalize session state before you clear or compact
/project-workflow:handoff

# Plan: rank the unranked items so the board's prioritization views become useful
/project-workflow:board-triage

# Report out: produce a status briefing deck (+ optional audio)
/project-workflow:comms

# Keep clearable: pass/gap verdict on the repo's structure against the standard
/project-workflow:repo-compliance-audit
```

```
$ /project-workflow:repo-compliance-audit
ID       | Area                | Verdict | Detail
---------+---------------------+---------+---------------------------------
META-01  | _meta/ taxonomy     | pass    | _archive, plans, research present
HANDOFF  | _meta/HANDOFF.md    | gap     | missing — run mise-en-place-scaffold
...
12 pass / 3 gap
```

## What it is not (yet)

- **Harness-agnostic in intent, but the skills are authored against Claude Code
  conventions.** The process SOPs live in `docs/sops/`; a non-Claude-Code harness gets the
  SOPs and the reasoning, not turnkey slash-commands.
- **"Delegate down-tier" is doctrine, not a skill.** The plugin makes delegation *possible*
  (a good plan + a clean handoff are what a cheaper agent needs), but the tier-routing
  itself is your orchestration, not an automated step here.
- **`memory-taxonomy` and `repo-meta-structure` are reference content**, read by the audit
  and scaffold scripts — they answer "what is the standard", they don't *do* anything when
  invoked directly.
- **The board skills assume GitHub Projects (v2).** Other trackers aren't covered.

## Roadmap

Scope and open work are tracked on the product's issue tracker rather than duplicated here:
<https://github.com/hsb3/dotfiles-agents/issues>. This re-scope trimmed the plugin to the
proven loop; members that had no evidenced use were moved to the incubation workbench and
can re-promote once a real use case pulls them back.
