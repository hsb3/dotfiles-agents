# Configuration

Five env vars, all mandatory. There is no fallback for any of them: a missing value
stops work rather than writing to the wrong board, and `SKILL.md` tells the agent to
ask the owner instead of guessing.

| Variable | What it is | Where it comes from |
|---|---|---|
| `KANEO_API_URL` | API base, including `/api`. No trailing slash. | your instance's host — **owner** |
| `KANEO_API_KEY` | **this repo's agent key** — never an owner key | **owner** — created against the instance, out of band (see below) |
| `KANEO_MCP_TOKEN` | Bearer token for the MCP server, minted *from* the agent key | `scripts/mint-mcp-token.sh`, shipped with this skill — mint it yourself |
| `KANEO_PROJECT_ID` | the board this repo works — project **id**, not slug | `list_projects`, or read it out of the board URL |
| `KANEO_AGENT_NAME` | identity written into claim and close comments | the agent account the key belongs to |

An owner key would hand this repo owner rights over every workspace and misattribute
every claim comment to the owner. Use the agent identity you were assigned.

Two concurrent sessions on the same repo use **separate** key/name pairs — a shared
identity breaks the board's claim-race protection, which is the only protection there is.

## What you mint, and what the owner hands you

Only one of the five is yours to produce. Given the agent key, mint the MCP token with
the script this skill ships:

```
MINT_KEY=<this repo's agent key> \
  "${CLAUDE_PLUGIN_ROOT}/skills/kaneo/scripts/mint-mcp-token.sh" https://<your-instance-host>
```

It needs nothing but that argument, `$MINT_KEY`, and `curl`/`openssl`/`python3`. The token
goes to stdout, progress to stderr.

**Creating the agent account and its key cannot ship with this plugin**, and no script here
will do it. That flow authenticates as the *owner*, needs the instance's workspace id, and
writes the resulting credentials into whatever store the instance keeps them in — all three
are properties of a specific deployment, not of the plugin. So if `KANEO_API_KEY` is unset,
that is the owner's step, not a missing tool: ask for an agent key and the account name it
belongs to. Never create one by signing up as the owner, and never fall back to an owner key.

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

Call the MCP `whoami` tool. It returns the user the token authenticated as. If that is the
**owner** account rather than an agent account, stop — every claim comment would be
attributed to the owner, and the board's claim-race protection is defeated.

There are two causes, and **the second is far more likely than the first**:

1. The wrong key is wired — an owner key sitting in `KANEO_API_KEY`.
2. **A direct `kaneo` MCP server registration is shadowing the plugin's.** See below.

Check 2 first. It presents identically to 1 while the key is perfectly correct, which is
what makes it eat an afternoon.

## The registration that steals your identity

The plugin's server is defined in its own `.mcp.json` and carries
`Authorization: Bearer ${KANEO_MCP_TOKEN}`. A server *also* named `kaneo`, registered
directly in `~/.claude.json` (by `claude mcp add`, or by a past session), **outranks it**.

If that direct registration has no `Authorization` header, the Kaneo instance answers with
`WWW-Authenticate`, Claude Code runs its own interactive OAuth, and the browser consent
authenticates **whoever is logged into the browser** — the human owner. The tools all work.
Nothing errors. The identity is just silently wrong.

Tell the two apart by the tool names: the plugin's server surfaces as
`mcp__plugin_kaneo_kaneo__<tool>`, a direct one as `mcp__kaneo__<tool>`. If you are calling
`mcp__kaneo__*` and did not register it deliberately, that is the shadow.

```sh
claude mcp list                     # what is actually registered
claude mcp remove kaneo -s local    # or -s user, depending on the scope it landed in
```

Then **fully quit the process** (below) and relaunch. The `kaneo-preflight` hook checks for
this at session start, so a fresh session tells you before you claim anything — but only a
headerless one, since a direct registration carrying its own valid header works fine and is
supported.

## Restarting actually means quitting

Several things here say "restart the session". That means **fully quitting the Claude Code
process and launching a new one**. It does not mean:

- `/reload-plugins` — reloads hooks and skills, and does **not** respawn MCP servers.
- resuming or continuing a session — the MCP connection and its headers are inherited.
- `/mcp` reconnect — reconnects, but does not re-expand `${KANEO_MCP_TOKEN}` from a
  changed settings file.

Server auth headers expand **once, at process start**. An edited token does nothing until
the process is gone. Three restart cycles were burned on this on 2026-08-11.

## The 401 you will eventually hit

The MCP token expires after 30 days and has no refresh. On a 401 from any kaneo MCP
tool: re-run `scripts/mint-mcp-token.sh` above (the agent key does not expire, so this
needs nothing from the owner), update `.claude/settings.local.json`, and fully quit and
relaunch. A "broken install" that appeared overnight is almost always this.
