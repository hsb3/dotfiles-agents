# board-triage

Runs the prioritization pass over a task board: pulls a compact snapshot, finds the items
missing a rank (or carrying a stale one), judges each against the repo's own plan/issue
context, and applies only the diff rather than guessing a rank it can't justify. Turns a
board full of captured-but-unranked items into a workable, ranked backlog.

The judgment is backend-agnostic and lives in `SKILL.md`. The board's I/O lives in a thin
adapter under `references/adapters/` — **GitHub Projects (v2)** and **Kaneo** ship. A new
backend is a new adapter file: two commands and a field map, no edit to the rubric.

## When it triggers

Use it to "run board triage", "triage the backlog", "prioritize the issues", "rank the
unranked issues", "fill in Impact/Effort/Priority", or "do the weekly triage" so the
prioritization and roadmap views become useful instead of drifting into noise.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the code-desk bundle (not standalone). The GitHub Projects adapter additionally
needs the `solo-skills` bundle, which is where its export/apply scripts live; the Kaneo
adapter is self-contained.
