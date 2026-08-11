# Kaneo API reference

Base: `$KANEO_API_URL` (mandatory, no fallback). REST calls carry
`x-api-key: $KANEO_API_KEY`; `Origin` header additionally required on `/auth/*`
mutations. MCP calls go to `$KANEO_API_URL/mcp` with
`Authorization: Bearer $KANEO_MCP_TOKEN` — the plugin's `.mcp.json` wires that up,
so use the kaneo MCP tools (`mcp__plugin_kaneo_kaneo__*`; `mcp__kaneo__*` if
directly registered) rather than calling the endpoint by hand.

## MCP tools

24 tools on image 2.16.4, each a thin proxy onto the REST API. Names below;
`tools/list` has the parameters. "L2" = available to subagent managers; the rest
are root-session only (the plugin hook denies them in any subagent context).

| Tool | Purpose | L2 |
|---|---|---|
| `whoami` | current session and user | yes |
| `list_workspaces` | workspaces you can access | yes |
| `list_projects` | projects in a workspace | yes |
| `get_project` | one project by id | yes |
| `create_project` | create a project | |
| `update_project` | patch project metadata | |
| `list_tasks` | tasks for a project, filtered/sorted | yes |
| `get_task` | one task by id | yes |
| `create_task` | create a task in a project | yes |
| `update_task` | full-object update (read-merge-write) | |
| `move_task` | move a task to another project/column | |
| `update_task_status` | status only | |
| `list_task_comments` | comments on a task | yes |
| `create_task_comment` | add a comment | yes |
| `update_task_comment` | edit your own comment | |
| `delete_task_comment` | delete your own comment | |
| `list_workspace_labels` | labels in a workspace | yes |
| `create_label` | create a label, optionally attached | |
| `delete_label` | delete a label (task-attached only) | |
| `attach_label_to_task` | attach an existing label | |
| `detach_label_from_task` | detach a label | |
| `create_task_relation` | subtask / blocks / related | |
| `get_task_relations` | relations involving a task | yes |
| `delete_task_relation` | delete a relation by id | |

Missing at 2.16.4 (the 2.17.1 bump closes them): assignee-only update, column and
member discovery, task delete, search. Use REST for those.

## REST endpoints

The claim ritual runs here (see SKILL.md); everything else prefers the tools above.

```
GET  /auth/get-session                your identity → userId
GET  /task/tasks/{projectId}          board; shape {"data":{"columns":[{"tasks":[...]}]}}
GET  /task/{id}                       single task (check assignee before claiming)
POST /task/{projectId}                create; title/description/status/priority ALL required
PUT  /task/status/{id}                status slugs: to-do | in-progress | in-review | done
PUT  /task/assignee/{id}              {"userId": ...}
POST /comment/{taskId}                {"content": ...}
GET  /project?workspaceId=...         projects
GET  /openapi                         full spec when anything 404s
```

## Gotchas

- Missing task → 400 "Workspace ID could not be determined" (treat as 404).
- Omit `priority` on create → validation error; default to "medium" only when
  you genuinely can't judge — an honest "medium" beats a fabricated rank.
- `/api/mcp` rejects `x-api-key` directly (it is OAuth 2.1 Bearer only), but a
  token minted from an agent key via `scripts/mint-mcp-token.sh` is accepted.
  That same token also authenticates REST.
