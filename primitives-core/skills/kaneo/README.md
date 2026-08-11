# kaneo

Work a repo's tracked tasks on a live [Kaneo](https://github.com/usekaneo/kaneo) board
instead of in-repo task files. The board is the single copy, so parallel sessions stop
grabbing the same work and stop drifting a `backlog.md` per branch. The skill carries the
claim ritual (the only race protection that exists), the decision convention, and the
level split that keeps claim authority in the root session while subagents read and append.

## When it triggers

Any session working against a Kaneo board: picking up, claiming, or completing a tracked
task; recording a decision; or being asked to write a TODO list in a repo whose work
lives on the board.

## What to read next

- `references/configuration.md` — the five `KANEO_*` env vars, where each comes from, and
  the 30-day token expiry that looks like a broken install.
- `references/api.md` — MCP tool table, REST endpoints, and the gotchas worth knowing before
  the first 400.
- `references/access-model.md` — the level split, what the policy hooks actually guarantee,
  and the enforcement ceiling. Read it before describing this as containment; it is not.

## Install

```
claude plugin install kaneo@dotfiles-agents
```

Needs a reachable Kaneo instance and an agent account on it. Configure the repo before
first use — an unset variable stops work rather than guessing a board.
