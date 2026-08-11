# kaneo-bash-tripwire

Denies a subagent's Bash command that reaches the Kaneo board host directly instead of
going through the board's MCP tools. It catches the naive path — a `curl` at the instance,
or a command naming the URL variable — and leaves an audit trail.

**It is a tripwire, not containment.** Both credentials live in the shared process
environment, so a subagent with Bash can still reach the board through a python one-liner
or a script it writes first. No string guard closes that. The only sound configuration for
an untrusted level is no Bash at all, which code-writing workers cannot have. The kaneo
skill's `references/access-model.md` states the ceiling in full; the companion
`kaneo-mcp-policy` is the hard half, for MCP calls.

## When it fires

`PreToolUse` on `Bash`, subagents only. No-op when `KANEO_API_URL` is unset — which is
every repo that does not use a board. The cost there is one hook process per Bash call.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `KANEO_API_URL` | unset | The instance base URL. Unset stands the tripwire down; set, its hostname becomes the thing to watch for. |

## Install

```
claude plugin install kaneo@dotfiles-agents
```
