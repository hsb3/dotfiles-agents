---
name: kenn-forge
description: Triage pull requests and issues, inspect diffs and CI checks, set local review workflow state, manage the daemon/repos/docs folders, and hand off work to a coding agent — via the kenn-forge MCP companion (agent workflows) or the kenn-forge CLI (scripts, shell, humans). Use when the user wants to find PRs/issues worth reviewing, check what's waiting on them, look at a diff or stack context, mark something reviewing/waiting/merged, spawn a coding-agent workspace, or run any `kenn-forge` subcommand. Read-only unless a tool/command below is explicitly a write.
compatibility: Requires a running kenn-forge daemon (`kenn-forge daemon status`). MCP tools additionally need [mcp].enabled = true in ~/.kenn/forge/config.toml and the server registered with the client (claude mcp add --transport http kenn-forge http://127.0.0.1:8092/mcp).
---

# kenn-forge

Maintainer workflows over the running kenn-forge daemon's cached repository, activity,
and workspace data — reachable two ways. **MCP tools** (`kenn_forge_*`) are for an agent
driving its own triage loop. **The `kenn-forge` CLI** is for shell/scripts/humans and
relays to the same daemon API (`kenn-forge api list` shows every underlying route).
Neither forces a provider sync unless stated. The only writes are
`kenn_forge_set_item_workflow_state` (MCP) and the daemon/repo/docs-folder management
commands below (CLI) — everything else is read-only.

## Setup check

If `kenn_forge_*` tools aren't available: confirm the daemon is running
(`kenn-forge daemon status --json`), confirm `mcp_listen_addr` is present in that
output (means `[mcp].enabled = true` took effect), and confirm the client has the
server registered (`claude mcp list` should show `kenn-forge` connected at
`http://127.0.0.1:8092/mcp`). After editing `[mcp]` in config, `kenn-forge daemon restart`
is required — it isn't hot-reloaded. `[mcp]` must be its own top-level TOML table;
adding it mid-file above other bare keys silently absorbs them into the table.

Loopback-only. No bearer token needed unless `[api].require_auth = true`, in which case
read the token from `~/.kenn/forge/auth_token` (mode 0600), never paste it into shared config.

## Tools

| User intent | Tool |
| --- | --- |
| Discover tracked repos, get stable IDs to reference elsewhere | `kenn_forge_list_repos` — call first, always |
| "What's worth reviewing right now" | `kenn_forge_find_review_candidates` |
| Recent cached activity feed | `kenn_forge_list_activity` |
| Full-text search, including quiet items outside recent activity | `kenn_forge_search_items` |
| Items already marked reviewing/waiting/etc | `kenn_forge_list_items_by_workflow_state` |
| Read a PR/issue's cached body, events, checks | `kenn_forge_get_item_context` |
| Look at a PR's diff (summary first, full file on request) | `kenn_forge_get_item_diff` |
| Check if a PR is part of a stack before claiming it | `kenn_forge_get_stack_context` |
| Mark local review status (reviewing/waiting/merged/etc) | `kenn_forge_set_item_workflow_state` — the only write tool |
| List available coding-agent launch targets | `kenn_forge_list_agent_targets` |
| Hand a PR/issue/branch off to a coding agent | `kenn_forge_spawn_workspace_with_agent` |
| Check a workspace's live agent sessions | `kenn_forge_list_workspace_agent_sessions` |

## CLI

Global flags on every command: `-o/--output json|yaml|jsonl` (default json; `jsonl` is
streaming-friendly for arrays), `--server` (target a non-default daemon), `--timeout`.
Most subcommands also take `--config` (default `~/.kenn/forge/config.toml`).

### Read

| Intent | Command |
| --- | --- |
| List/filter PRs and MRs | `kenn-forge pulls --repo owner/name --state open --kanban <state> --q <search> --starred --limit N` |
| One PR/MR detail record | `kenn-forge pulls get PROVIDER OWNER NAME NUMBER [--host HOST]` |
| List/filter issues | `kenn-forge issues --repo owner/name --state open --q <search> --starred --limit N` |
| One issue detail record | `kenn-forge issues get PROVIDER OWNER NAME NUMBER [--host HOST]` |
| Recent activity feed | `kenn-forge activity --since <RFC3339> --limit N` |
| Configured repos | `kenn-forge repos` |
| Per-repo summaries | `kenn-forge repo-summaries` |
| Detected PR stacks | `kenn-forge stacks` |
| Provider rate-limit status | `kenn-forge rate-limits` |
| Sync progress | `kenn-forge sync status` |
| Workspaces / one workspace | `kenn-forge workspaces` / `kenn-forge workspaces get ID` |
| A config value | `kenn-forge config read KEY` |
| Build info | `kenn-forge version` |

`--repo` on `pulls`/`issues`/`activity` takes `owner/name` or a provider-aware key from
`kenn-forge repos`. That's a **different shape** than `archive`'s `--repo`, which wants
`provider|host/repo_path` and can repeat for multiple repos.

### Write / manage

| Intent | Command |
| --- | --- |
| Force a full sync | `kenn-forge sync` |
| Daemon lifecycle | `kenn-forge daemon start\|stop\|restart\|status [--json]` |
| Add/list/remove a docs folder | `kenn-forge docs add-folder PATH --name X [--id X] [--daemon KATA_ID]` / `list-folders` / `remove-folder ID` |
| Pause/start/inspect historical archiving | `kenn-forge archive pause\|start\|status [--repo ... --all]` |
| Render an archive activity report | `kenn-forge archive report --start X --end Y [--repo ...] [--format markdown\|json] [--output FILE]` |
| Install/run/remove agent lifecycle hooks | `kenn-forge agent-hook install\|run\|uninstall [--agent NAME]` |

### Escape hatch

`kenn-forge api list` enumerates every underlying route (339 operations — activity,
docs, archive, settings, workspaces, everything the UI itself uses), each with its
method, path, and query params. `kenn-forge api METHOD PATH [body...]` (or `-d @-` /
`-d @file` for a JSON body) relays one raw request when no dedicated subcommand covers
it. `kenn-forge quickstart` prints this same cheat-sheet from the CLI itself.
`kenn-forge mcp quickstart` prints live MCP connectivity + ready-to-paste client config
— faster than re-deriving it from this doc if the port or auth state has changed.

## Standard triage flow

1. `kenn_forge_list_repos` — get `platform_repo_id` and `repo_path` for filters below.
   Rediscover after any repository rename; route (owner/name) is not stable, the ID is.
2. `kenn_forge_find_review_candidates` with a time window and item types.
3. `kenn_forge_get_item_context` on likely candidates.
4. For PRs: `kenn_forge_get_item_diff` in summary mode first; only request the full
   diff file (`emit_diff_file: true`) if the summary isn't enough. Diff files are
   temporary — capped by `[mcp].diff_cache_mb` (default 128 MiB), oldest evicted first.
5. `kenn_forge_get_stack_context` before claiming a PR that might be stacked.
6. `kenn_forge_set_item_workflow_state` to claim it. Pass `expected_status` so a stale
   agent doesn't clobber someone else's concurrent update; use `force: true` only for a
   deliberate override.

## Coding-agent handoff

1. `kenn_forge_list_agent_targets` to see what's available.
2. `kenn_forge_spawn_workspace_with_agent` with either a `source.item` (PR/issue) or
   `source.adhoc` (repo + optional branch), an `agent_target` key, and one
   `initial_message`. Creates or reuses a workspace and submits exactly one message —
   it does not clean up on a later failure, and does not retry.
3. Read `stage` and `initial_message.state` in the response as the authoritative
   evidence the handoff landed, not just tool success.
4. `kenn_forge_list_workspace_agent_sessions` to check live sessions afterward.

## Troubleshooting

- Nothing works: `kenn-forge daemon status --json` first — confirms the daemon is up
  and, if MCP is enabled, shows `mcp_listen_addr`.
- 401: `[api].require_auth` is on and the bearer token is missing/wrong.
- 403: request didn't arrive as a direct same-origin loopback call.
- MCP endpoint unreachable: confirm `[mcp].enabled = true`, `kenn-forge daemon restart`
  (config changes are not hot-reloaded), recheck `daemon status --json` for the listener.
- `kenn-forge repos` returns `[]`: no repos are tracked yet — add them in Settings, or
  in TOML under `[[repos]]` (see `docs/configuration.md` in the forge repo for
  multi-provider / self-hosted host setup), then `kenn-forge sync`.
