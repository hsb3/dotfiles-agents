# kaneo-preflight

Says loudly, at session start, that the Kaneo board tools will not be there — and why.

The companion `kaneo-mcp-policy` hook can only fire on a board tool call, so it cannot catch
the case where the tools never loaded. That case is the dangerous one: the kaneo skill still
loads, still says the board holds the tracked work, and still forbids `TODO.md`. An agent
that finds no board tools does not stop, it improvises.

Checks three causes, each invisible on its own: the repo is unconfigured, someone ran
`/mcp disable` for this project, or plugin MCP discovery is switched off by env.

## When it fires

`SessionStart`, on `startup` and `clear` only — never `resume` or `compact`, where the
session already carries the warning. Silent whenever the board is reachable.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `KANEO_PREFLIGHT_DISABLED` | unset | Any non-empty value stands the check down |
| `KANEO_API_URL`, `KANEO_MCP_TOKEN` | unset | The two the MCP server expands; either missing means no connection is attempted |
| `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS` | unset | Harness-level switch; honoured together with its `..._EXCEPT` allowlist |

Reads `~/.claude.json` for the per-project `/mcp disable` state, because that is the only
place that toggle persists. Writes nothing, and fails open and silent on every error path.

## Install

```
claude plugin install kaneo@dotfiles-agents
```
