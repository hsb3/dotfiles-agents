# Verification and failure modes

An edit that saves is not an edit that applied. Every settings change gets two confirmations:
the file **parses as JSON**, and the change **took effect**. Skipping either is how a config
change silently does nothing.

## Step 1 — JSON validity (before you're done editing)

A single trailing comma, a missing quote, or a stray comment invalidates the whole file, and the
harness responds by **ignoring it entirely with no error**. Always run:

```bash
python3 -m json.tool < .claude/settings.json     # prints the parsed file, or the exact parse error
# or:  jq . .claude/settings.json
```

Do this for every file you touched (`settings.json`, `settings.local.json`, `.mcp.json`). A file
that does not parse is treated as if it were absent.

## Step 2 — confirm it took effect (per change type)

| Change | Confirm with | Needs a fresh session? |
|---|---|---|
| Permission rule (allow/deny/ask) | `/permissions` lists active rules; or attempt the gated action and watch the prompt/deny | No — applies to the next tool call |
| `env` variable | Start a fresh session, then check the variable inside a spawned shell | **Yes** — env is read once at startup |
| Hook | Fresh session, then `/hooks` shows it registered; trigger its event and confirm it fires | **Yes** — the hook set is snapshotted at startup |
| MCP server | `/mcp` lists the server and its connection status | Reconnect via `/mcp`, or a fresh session |
| `model` / other keys | Observe the next session; some apply live | Usually next session |

When in doubt, **start a fresh session and re-verify** — it is the one reliably clean state, and
it is mandatory for env and hook changes.

## The silent failure modes

| Symptom | Root cause | Fix |
|---|---|---|
| "My setting did nothing at all" | JSON syntax error → entire file ignored, no warning | Validate with `json.tool`/`jq` on every save |
| Change works for you but not a teammate (or vice-versa) | Written to the wrong scope (`settings.local.json` vs shared `settings.json`, or user vs project) | Move it to the correct file per precedence |
| A rule "won't take" no matter what | A higher-precedence file overrides it (managed policy, or a project-local `deny`) | Check the precedence chain; resolve the conflict at the right level |
| Agent is over-permissioned | Rule too broad — a bare tool name or `Bash(*)` | Replace with the narrowest specifier that works |
| Hook is "installed" but never runs | Wrong event/matcher, JSON invalid, or a directly-invoked script without the exec bit | Match event to trigger; validate JSON; `chmod +x` + shebang, or invoke via `python3` |
| Hook breaks the session | Script raises instead of failing open | Catch everything, exit `0` unless blocking is intended |
| Secret ended up in git | A credential or machine path was written into the committed `settings.json` | Move to `.claude/settings.local.json`; reference secrets as `${VAR}`, never inline literals |
| "Always do Y" happens only sometimes | Encoded as an instruction/memory rather than a hook | Implement it as a hook — only the harness guarantees "every time" |
| MCP tools unavailable | Server declared in `.mcp.json` but not enabled | Approve it (`enableAllProjectMcpServers` or `enabledMcpjsonServers`); check `/mcp` |

## The discipline in one line

Right file, narrowest scope, valid JSON, verified effect, fresh session when the change type
demands it. Every settings edit passes all five before it is considered done.
