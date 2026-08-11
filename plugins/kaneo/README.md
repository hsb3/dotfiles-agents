# kaneo

Track a repo's work on a live [Kaneo](https://github.com/usekaneo/kaneo) board instead of
in-repo task files. Parallel agent sessions and a `TODO.md` do not mix: the list drifts per
branch, two sessions grab the same work, and nothing records who did what. A shared board
fixes the drift — but a root session spawning managers spawning workers creates two new
problems, because every level shares one process environment and therefore holds the same
credentials, and parallel subagents sharing one identity break the board's only race
protection.

This plugin is the answer to both: per-level tool grants, a policy hook that enforces the
floor rather than trusting an agent's own `tools:` list, and automatic attribution on
everything that lands.

Install it in any repo whose work is tracked on a Kaneo project. Nothing about an instance
is baked in — all five instance values arrive as `KANEO_*` env vars.

## How it fits together

```mermaid
flowchart TD
    session[Root session picks up work] --> claim[Claim ritual on REST]
    claim -->|assign then re-read| race{Still yours}
    race -->|no| back[Back off and take another task]
    race -->|yes| work[Work the task]
    work --> finish[Status done plus a closing comment]
    finish --> session
    work -.->|dispatches| mgr[kaneo-manager subagent]

    claim --> board[(Kaneo board)]
    finish --> board
    mgr -->|reads and appends only| board

    kaneo[kaneo skill] -.->|governs the ritual| claim
    policy[kaneo-mcp-policy] -.->|denies claim tools and stamps agent plus session| mgr
    tripwire[kaneo-bash-tripwire] -.->|denies subagent Bash aimed at the host| mgr
```

The claim ritual is the load-bearing part: there is no atomic claim, so assign-then-re-read
is the entire race protection. It runs on REST from the root session only, because MCP's
lone assignee path is a full-object read-merge-write that can silently revert the GitHub
integration's push-driven status transition.

## What you get

| Path | What it does |
|---|---|
| `skills/kaneo/` | The contract: claim ritual, levels, decision convention, plus configuration, API, and access-model references |
| `.mcp.json` | The board's MCP server, registered by installing the plugin — no hand-written config in the consuming repo |
| `agents/kaneo-manager.md` | Reference L2 manager; its `tools:` list *is* the append-only allowlist |
| `hooks/kaneo-mcp-policy/` | Floor-deny for subagents, plus attribution stamping on comments and task creation |
| `hooks/kaneo-bash-tripwire/` | Advisory deny on subagent Bash that reaches the board host directly |

## Levels, and the ceiling

Board authority narrows down the delegation chain: the root session claims and mutates,
L2 managers read and append but never claim or change status, L3 workers get no board tools.
The hook enforces the L2 floor rather than trusting an agent's `tools:` list, so a
misconfigured agent fails closed.

**Enforcement is sound for MCP calls only.** Both credentials live in the shared process
environment, so any subagent holding Bash can reach the board over REST regardless — the
tripwire catches the naive path and leaves a trail, nothing more. For a single-owner
self-hosted instance that ceiling is accepted; do not describe this plugin as containment.
`skills/kaneo/references/access-model.md` states the limit precisely.

## Install

```
claude plugin install kaneo@dotfiles-agents
```

Then configure the repo — `skills/kaneo/references/configuration.md` lists the five
variables, where each comes from, and the 30-day token expiry that later looks like a
broken install. A missing value stops work rather than writing to the wrong board.
