# Kaneo API reference

Base: `$KANEO_API_URL` (mandatory, no fallback). REST calls carry
`x-api-key: $KANEO_API_KEY`; `Origin` header additionally required on `/auth/*`
mutations. MCP calls go to `$KANEO_API_URL/mcp` with
`Authorization: Bearer $KANEO_MCP_TOKEN` — the plugin's `.mcp.json` wires that up,
so use the kaneo MCP tools (`mcp__plugin_kaneo_kaneo__*`; `mcp__kaneo__*` if
directly registered) rather than calling the endpoint by hand.

## MCP tools

**36 tools on image 2.19.1** (verified live 2026-08-17), each a thin proxy onto the
REST API. `tools/list` has the parameters — and is the authority. This table has been
wrong before, which is how sessions ended up hand-rolling REST for tools that existed;
enumerate rather than trust it if a tool you want is missing here.

Names below. "L2" = available to subagent managers; the rest are root-session only
(the plugin hook denies them in any subagent context).

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
| `update_task_assignee` | assignee only, no read-merge-write | |
| `update_task_due_date` | due date only | |
| `delete_task` | delete a task | |
| `search` | search across the board | yes |
| `list_workspace_members` | members, for assignee ids | yes |
| `list_project_columns` | the board's lanes (read only) | yes |
| `list_task_activity` | a task's activity trail | yes |
| `list_notifications` | your notifications | yes |
| `create_time_entry` / `update_time_entry` | time tracking | |
| `get_time_entry` / `list_task_time_entries` | time tracking, read | yes |

**Only two gaps remain at 2.19.1**, both with REST endpoints below: **column writes**
(create/update/delete/reorder a lane) and **bulk import/export**. Everything the older
version of this file listed as missing — assignee-only update, member discovery, task
delete, search, column *read* — shipped between 2.16.4 and 2.19.1.

Do not build a parallel CRUD layer for those two gaps. `curl` covers them, and the
`board-triage` skill's `scripts/kaneo_board.py` already does snapshot → changeset →
apply over REST. Writing to Postgres directly is worse than either: the API publishes
the events that drive the Telegram and GitHub integrations, the activity trail, and
workflow rules, so a direct row write lands silently with no notification and no audit.

## REST endpoints

The claim ritual runs here (see SKILL.md); everything else prefers the tools above.

```
GET  /auth/get-session                your identity → userId
GET  /task/tasks/{projectId}          board; shape {"data":{"columns":[{"tasks":[...]}]}}
GET  /task/{id}                       single task (check assignee before claiming)
POST /task/{projectId}                create; title/description/status/priority ALL required
PUT  /task/status/{id}                status = the target column's slug (see below)
PUT  /task/assignee/{id}              {"userId": ...}
POST /comment/{taskId}                {"content": ...}
GET  /project?workspaceId=...         projects
GET  /column/{projectId}              the board's lanes, ordered by `position`
POST /column/{projectId}              create a lane; {name, icon?, color?, isFinal?}
PUT  /column/{id}                     rename/recolour; {name, icon?, color?, isFinal?}
PUT  /column/reorder/{projectId}      {"columns":[{"id","position"}]} — whole set at once
DELETE /column/{id}                   delete a lane
GET  /task/export/{projectId}         {project, tasks:[...]} — INCLUDES labels
POST /task/import/{projectId}         bulk create; {"tasks":[{title, status, ...}]}
GET  /label/workspace/{workspaceId}   labels (workspace-scoped, not per-project)
GET  /openapi                         full spec when anything 404s
```

## Statuses are column slugs, not a fixed vocabulary

There is no global status enum. A task's `status` is the **slug of a column in its own
project**, so the valid set is whatever `GET /column/{projectId}` returns. Boards in the
wild carry lanes like `to-do`, `up-next`, `in-progress`, `documents` — a board with a
`Documents` lane accepts `"status":"documents"` and no other board does.

Read the columns before writing a status. Guessing from another project's board, or from
a remembered four-slug list, writes tasks into lanes that do not exist on the target.

**A lane's name and its slug drift independently** — renaming a lane does not re-slug it.
Live examples: a lane named `Documents` whose slug is `decisions`, and one named
`Document` whose slug is `documents`. Match lanes on **name**, then write back the `slug`
you read. Never derive one from the other.

Provision lanes with `POST /column/{projectId}`; `isFinal` marks the terminal lane.

## Bulk import silently drops labels

`POST /task/import/{projectId}` takes the whole array in one call and is the right tool
for a migration — but its accepted fields are only `title`, `description`, `status`,
`priority`, `startDate`, `dueDate`, `userId`. **Send `labels` and they are discarded
without comment**: the response still reports `"failed": 0`, and the tasks come back with
`labels: []`.

Since `GET /task/export/{projectId}` *does* emit labels, an export → import round-trip
looks lossless and is not. Re-attach labels afterwards as a second pass
(`PUT /label/{id}/task`, or `POST /label` with the task id), and verify by re-exporting
rather than by trusting the import summary.

## Gotchas

- Missing task → 400 "Workspace ID could not be determined" (treat as 404).
- Omit `priority` on create → validation error; default to "medium" only when
  you genuinely can't judge — an honest "medium" beats a fabricated rank.
- `/api/mcp` rejects `x-api-key` directly (it is OAuth 2.1 Bearer only), but a
  token minted from an agent key via `scripts/mint-mcp-token.sh` is accepted.
  That same token also authenticates REST.
