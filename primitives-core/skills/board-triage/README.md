# board-triage

Runs the weekly board-prioritization pass over a GitHub Project (v2): pulls a snapshot,
finds items missing Workstream/Impact/Effort/Priority (or carrying a stale ranking), judges
each against the repo's own plan/issue context, and applies only the diff rather than
guessing a rank it can't justify. Turns a board full of captured-but-unranked items into a
workable, ranked backlog.

## When it triggers

Use it to "run board triage", "triage the backlog", "prioritize the issues", "rank the
unranked issues", "fill in Impact/Effort/Priority", "do the weekly triage", or classify
GitHub Project (v2) items so the Prioritization/Now/Roadmap views become useful.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the code-desk bundle (not standalone).
