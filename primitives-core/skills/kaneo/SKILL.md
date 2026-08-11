---
name: kaneo
description: Work tasks on a Kaneo board (live project tracker) - claim tasks, update status, log decisions. Use whenever a session works against a Kaneo board, picks up / claims / completes tracked tasks, or must record a decision. The board replaces in-repo task files (backlog.md, TODO lists).
---

# Kaneo agent workflow

The board tracks committed work. Create a task when the work needs planning,
decisions, or handoff notes; skip it for questions and trivial mechanical edits.
Never create backlog.md or TODO files — file tasks on the board instead.

Before creating a task, search the board for an existing one. Write task bodies
so a future agent can act on them with no conversation context.

MCP tools, REST endpoints, required fields, and gotchas: `references/api.md` (in
this skill's directory). When anything 404s, `GET /openapi` for the full spec.

## Config (env vars, all mandatory)

- `KANEO_API_URL` — API base, e.g. `https://<host>/api` (no fallback)
- `KANEO_API_KEY` — your agent's key; REST calls carry `x-api-key: $KANEO_API_KEY`
- `KANEO_MCP_TOKEN` — Bearer token for the `kaneo` MCP server
- `KANEO_PROJECT_ID` — the board to work
- `KANEO_AGENT_NAME` — identity for claim/close comments

The owner supplies the URL, the agent key, and the project id — an agent account
cannot be created from here, since that needs owner credentials and the
instance's workspace id. Given the agent key, mint the MCP token yourself with
the script this skill ships:

```
MINT_KEY=<this repo's agent key> \
  "${CLAUDE_PLUGIN_ROOT}/skills/kaneo/scripts/mint-mcp-token.sh" <base-url>
```

Put the result in this repo's `.claude/settings.local.json` (gitignored — the
key is a credential). The token expires after 30 days and has no refresh; on a
401 from a kaneo MCP tool, re-mint, update the file, and **fully quit and relaunch
the process** — headers expand once at process start, so `/reload-plugins` and a
resumed session both keep the old token.

Tool names: the plugin-shipped server surfaces as `mcp__plugin_kaneo_kaneo__<tool>`;
a directly-registered server named `kaneo` surfaces as `mcp__kaneo__<tool>`. The
plugin hook handles both; agent `tools:` grants must use the form your repo
actually has (plugin-shipped unless you registered it yourself).

**If you are calling `mcp__kaneo__*` and nobody registered it deliberately, stop and
check `whoami`.** A direct registration outranks the plugin's, and a headerless one
makes Claude Code fall back to interactive OAuth — which authenticates the *owner*,
silently, with every tool still working. `references/configuration.md` has the fix.

Any missing → ask the owner; never guess or create a project. Use the agent
identity you were assigned, never an owner key. Confirm identity:
`GET /auth/get-session` (REST) or the MCP `whoami` tool → your userId.

## Adopting a repo that already has a backlog

Never migrate an existing tracker by creating tasks one tool call at a time, and never
fan that out across subagents — it is bulk data movement, so it gets a script:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/kaneo/scripts/onboard_repo.py" \
  --workspace <id> discover --repo . --project-id <id>     # read-only, run this first
```

`discover` is mandatory before `apply`, which will not create a project for you. The
duplicate-board mistake happens when nothing looks first. `apply` is a dry run until
`--yes`, records every created task in `--state` so an interrupted run resumes, and
verifies by re-exporting rather than trusting the import summary.

## MCP first, claim ritual on REST

Board reads, comments, task creation, labels, and relations go through the
kaneo MCP tools. Use REST for the claim ritual and for anything the tool set
doesn't cover. The ritual stays on REST at image 2.16.4 because MCP's only
assignee path is full-object `update_task`, whose read-merge-write can silently
revert the GitHub integration's status transition; it moves to MCP once the
2.17.1 pin bump (board task 5) lands `update_task_assignee`.

## Levels

- Root session — claims tasks; all board tools plus REST.
- Subagent managers (L2) — reads, `create_task_comment`, `create_task`; exact set
  in `references/api.md`. No claiming, no status changes. Dispatch them as
  `kaneo-manager`, whose `tools:` list is that set; a repo's own manager
  definitions copy it.
- Workers (L3) — no board tools; report findings upward.

MCP comments and task creations are stamped with agent and session by the
`kaneo-mcp-policy` hook, so managers must not hand-stamp them. That hook is also
what denies a subagent the claim-authority tools, and `kaneo-bash-tripwire` denies
the naive REST detour around it — the level model above is those two hooks, not
prose. REST is not stamped, which is why the claim comment below carries its stamp
by hand. What the enforcement does and does not guarantee:
`references/access-model.md`.

## Claim ritual (mandatory order, REST, root session only)

1. `GET /task/{id}` — assignee set and not you → back off, next task.
2. `PUT /task/assignee/{id}` `{"userId":"<you>"}`
3. Re-read. Assignee not you → you lost the race, back off. (No atomic claim
   exists; this re-read is the only protection.)
4. `PUT /task/status/{id}` `{"status":"in-progress"}`
5. `POST /comment/{taskId}` `{"content":"claimed by $KANEO_AGENT_NAME, session <id>"}`

Claim ONE task at a time. Work you discover outside the task's description gets
a comment or a new task, never silent expansion of the claimed one.

Finish: status `done` + closing comment naming what changed and how it was
verified (test run, command output, exercised behavior) — never from code
presence or intent alone. Blocked: comment why, leave in-progress.

## Linked GitHub repos

If the dev repo is linked to the project (GitHub integration), name work branches
`<project-slug>-<taskNumber>[-suffix]`, lowercase (e.g. `sbx-4-retry-logic`).
Status then moves itself: push → in-progress, PR open → in-review, merge → done —
don't set those statuses by hand for branch-driven work; comments are still on you.

## Decisions

A decision is a task: label `decision`, description has Context / Decision /
Consequences, status `done` when settled, approvals as comments. Check existing
decision tasks before contradicting one. Never claim a decision task (or any
task blocked on an owner ruling) to settle it yourself — those are the owner's;
back off and pick buildable work.
