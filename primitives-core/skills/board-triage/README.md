# board-triage

Runs the prioritization pass over a task board: pulls a compact snapshot, finds the items
missing a rank (or carrying a stale one), judges each against the repo's own plan/issue
context, and applies only the diff rather than guessing a rank it can't justify. Turns a
board full of captured-but-unranked items into a workable, ranked backlog.

The judgment is backend-agnostic and lives in `SKILL.md`. The board's I/O lives in a thin
adapter under `references/adapters/` — **GitHub Projects (v2)**, **Kaneo**, and **Kata**
ship, each with its own export/apply script in `scripts/`. A new backend is a new adapter
file: two commands and a field map, no edit to the rubric.

Every adapter writes only on `--apply`. The default run is a preview you read first, and it
refuses the same rows the write would, so an unresolvable changeset is caught before it
touches the board. A refused row is a failure on every adapter alike: it prints as a `SKIP` on
stderr and the run exits non-zero, while the rows that did resolve are still applied. So
`apply || abort` behaves the same whichever board is underneath. Both diagnostics go to
stderr — a `SKIP` for a row the adapter refused, a `FAIL` for one the board rejected — so
stdout is only ever the row log, and piping it into a diff or a counter never has to
filter them out.

## When it triggers

Use it to "run board triage", "triage the backlog", "prioritize the issues", "rank the
unranked issues", "fill in Impact/Effort/Priority", or "do the weekly triage" so the
prioritization and roadmap views become useful instead of drifting into noise.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the `code-desk` bundle. Every adapter is self-contained — no second plugin to
install. What each one needs is the backend's own client: the GitHub Projects adapter wants
`gh` authenticated with `project` scope (`gh auth refresh -s project`), the Kata adapter
wants the `kata` binary pointed at the right daemon, and the Kaneo adapter wants the API
url, key, and project id it already takes from the environment. Each adapter says so at the
top of its own file, and carries its backend's one-time setup (project/board creation, field
provisioning, views and workflows) alongside the day-to-day export/apply commands. Where a
setup step is a board write rather than a read, the adapter says so at that step and names
the legal values, so a snippet is never copied blind.
