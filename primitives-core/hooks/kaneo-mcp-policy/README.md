# kaneo-mcp-policy

Keeps claim authority on a Kaneo board in the root session, and stamps who did what.
A subagent calling a claim-authority tool is denied; a subagent's comment or new task is
appended with its agent type and session id before it lands. The allowlist is the
authority rather than the calling agent's own `tools:` grant, so a misconfigured agent
fails closed instead of quietly inheriting the right to claim work.

## When it fires

`PreToolUse` on any kaneo MCP tool — both live prefixes
(`mcp__plugin_kaneo_kaneo__*` for the plugin-registered server,
`mcp__kaneo__*` for a directly registered one).

## Configuration

The L2 allowlist is fixed in the handler; tools added by a future image bump default to
denied. Three variables gate every non-diagnostic call — unset any one and the hook denies,
naming the missing variable:

| Env var | Default | Meaning |
|---|---|---|
| `KANEO_API_KEY` | none — required | Denies with `KANEO_API_KEY` named when unset |
| `KANEO_PROJECT_ID` | none — required | Denies with `KANEO_PROJECT_ID` named when unset |
| `KANEO_AGENT_NAME` | none — required | Denies with `KANEO_AGENT_NAME` named when unset |

## The ceiling

Sound for MCP calls only. Both credentials live in the shared process environment, so a
subagent holding Bash can reach the board over REST regardless — the companion
`kaneo-bash-tripwire` catches the naive path and nothing more. Do not describe this as
containment; the kaneo skill's `references/access-model.md` states the limit precisely.

## Install

```
claude plugin install kaneo@dotfiles-agents
```
