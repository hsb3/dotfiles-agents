# Configuration

Five env vars, all mandatory. There is no fallback for any of them: a missing value
stops work rather than writing to the wrong board, and `SKILL.md` tells the agent to
ask the owner instead of guessing.

| Variable | What it is | Where it comes from |
|---|---|---|
| `KANEO_API_URL` | API base, including `/api`. No trailing slash. | your instance's host |
| `KANEO_API_KEY` | **this repo's agent key** — never an owner key | `mint-agent.sh` in the instance ops repo; the value also lands in that instance's variable store as `AGENT_<NAME>_KEY` |
| `KANEO_MCP_TOKEN` | Bearer token for the MCP server, minted *from* the agent key | `MINT_KEY=<agent key> mint-mcp-token.sh <base-url>` |
| `KANEO_PROJECT_ID` | the board this repo works — project **id**, not slug | `list_projects`, or read it out of the board URL |
| `KANEO_AGENT_NAME` | identity written into claim and close comments | the agent account the key belongs to |

An owner key would hand this repo owner rights over every workspace and misattribute
every claim comment to the owner. Use the agent identity you were assigned.

Two concurrent sessions on the same repo use **separate** key/name pairs — a shared
identity breaks the board's claim-race protection, which is the only protection there is.

## Where the values go

The credentials belong in the consuming repo's `.claude/settings.local.json`, which is
gitignored. An agent key is a credential; it never gets committed.

```json
{
  "env": {
    "KANEO_API_URL": "https://<your-instance-host>/api",
    "KANEO_API_KEY": "<agent key>",
    "KANEO_MCP_TOKEN": "<minted bearer token>",
    "KANEO_PROJECT_ID": "<project id>",
    "KANEO_AGENT_NAME": "<agent account name>"
  }
}
```

The plugin ships the MCP server definition (`.mcp.json` at the plugin root), which
expands `${KANEO_API_URL}` and `${KANEO_MCP_TOKEN}` from that env — so the server
travels with the plugin while the credentials stay local to the repo.

## Verify it took

Call the MCP `whoami` tool. It returns the user the key belongs to. If that is the
**owner** account rather than an agent account, the wrong key is wired and every claim
comment will be attributed to the owner. Fix it before claiming anything.

## The 401 you will eventually hit

The MCP token expires after 30 days and has no refresh. On a 401 from any kaneo MCP
tool: re-mint, update `.claude/settings.local.json`, and **restart the session** —
headers expand at session start, so an edited token does nothing until the harness
restarts. A "broken install" that appeared overnight is almost always this.
