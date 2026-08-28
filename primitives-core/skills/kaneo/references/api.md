# Kaneo API reference

Base: `$KANEO_API_URL` (mandatory, no fallback). REST calls carry
`x-api-key: $KANEO_API_KEY`; `Origin` header additionally required on `/auth/*`
mutations. MCP calls go to `$KANEO_API_URL/mcp` with
`Authorization: Bearer $KANEO_MCP_TOKEN` — the plugin's `.mcp.json` wires that up,
so use the kaneo MCP tools (`mcp__plugin_kaneo_kaneo__*`; `mcp__kaneo__*` if
directly registered) rather than calling the endpoint by hand.

## MCP tools

**36 tools** as last counted, each a thin proxy onto the REST API. `tools/list` has the
parameters — and is the authority. This table has been wrong before, which is how
sessions ended up hand-rolling REST for tools that existed; enumerate rather than trust
it if a tool you want is missing here. The tool surface grows with the instance's image,
so treat any absence here as a claim to re-check, never as a fact.

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
| `move_task` | move a task to another **project** (`destinationProjectId` required, `destinationStatus` optional) — never a lane change within a project; that is `update_task_status` | |
| `update_task_status` | status only | |
| `list_task_comments` | comments on a task | yes |
| `create_task_comment` | add a comment | yes |
| `update_task_comment` | edit your own comment | |
| `delete_task_comment` | delete your own comment | |
| `list_workspace_labels` | labels in a workspace | yes |
| `create_label` | create a label, optionally attached | |
| `delete_label` | delete a label row — **cascades, see below** | |
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

**Two gaps as last checked**, both with REST endpoints below: **column writes**
(create/update/delete/reorder a lane) and **bulk import/export**. Confirm against
`tools/list` before working around either — assignee-only update, member discovery, task
delete, search and column *read* were all listed as gaps here once, and all shipped.

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
PUT  /task/{id}                       full-object REPLACE; body must carry title, description,
                                      status, priority, position, projectId (see Gotchas)
PUT  /task/status/{id}                status = the target column's slug (see below)
PUT  /task/assignee/{id}              {"userId": ...}
POST /comment/{taskId}                {"content": ...}
GET  /project?workspaceId=...         projects
GET  /column/{projectId}              the board's lanes, ordered by `position`
POST /column/{projectId}              create a lane; {name, icon?, color?, isFinal?}
PUT  /column/{id}                     rename/recolour; {name, icon?, color?, isFinal?}
PUT  /column/reorder/{projectId}      {"columns":[{"id","position"}]} — whole set at once
DELETE /column/{id}                   delete a lane
GET  /task/export/{projectId}         {project, tasks:[...]} — labels yes, id/number NO
GET  /task/tasks/{projectId}          identity-bearing read: id, number, position, labels
POST /task/import/{projectId}         bulk CREATE (never updates); {"tasks":[{title, status, ...}]}
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

## Bulk import and export

**Import always creates, never updates.** There is no upsert: `POST /task/import/{projectId}`
mints a new id and a new number for every element, so running the same payload twice
gives you two copies.

`GET /task/export/{projectId}` returns `{project, tasks:[...]}` and each task carries
`title`, `description`, `status`, `priority`, `startDate`, `dueDate`, `userId`, `labels` —
and **no `id`, no `number`, no `position`**. That is the same payload the UI's download
button produces, which is why a downloaded file has nothing to key a task by. Export is a
content dump, not a snapshot you can write back from. When identity matters, read
`GET /task/tasks/{projectId}`: it has `id`, `number`, `position`, hydrated `labels` and
`externalLinks`, grouped by column, plus separate `archivedTasks` and `plannedTasks`
buckets that no column contains.

`POST /task/import/{projectId}` accepts `{"tasks":[{...}]}` where only `title` and
`status` are required, and the accepted fields are `title`, `description`, `status`,
`priority`, `startDate`, `dueDate`, `userId`. It answers with
`{importedAt, project, results:{total, successful, failed, tasks:[...]}}` — the per-task
entries hold the new ids, which is the only place to get them without re-reading.

Three silent losses, all verified live:

- **`labels` are discarded**, though export emits them. `"failed": 0`, and the tasks come
  back with `labels: []`. So an export → import round-trip looks lossless and is not.
- **An unknown `status` is coerced to `planned`** rather than rejected. The task is
  created, counted as successful, and lands in the `plannedTasks` bucket where **no lane
  shows it**. A single typo'd slug hides a task from the board with no error anywhere.
- **`priority` defaults to `low`** when omitted, not to `medium`.

So a migration is: import the bodies, read `results.tasks` (or re-read
`/task/tasks/{projectId}`) for the new ids, attach labels as a second pass with
`POST /label` including `taskId`, then verify against `/task/tasks` — never against the
import summary, which reports success for tasks it has just buried.

## Labels are row-groups, and a definition delete takes the group

A label name is not one row. Each name has at most one **definition row** (`taskId: null`
— the workspace palette entry) and one **attachment row** per task carrying it.
`GET /label/workspace/{workspaceId}` returns both kinds mixed together; `taskId` is the
only thing that tells them apart.

**So the payload scales with labelled tasks, not with the vocabulary**, and the tool's name
("labels in a workspace") reads as though it returns the latter. Measured on a working
workspace: 1,233 rows and ~280 KB for 47 distinct names, only 14 of them definition rows —
about 96% duplication. Through the MCP tool that overflows the result cap and spills to a
file. When what you want is the vocabulary, `jq 'unique_by(.name)'` over the spill, or filter
`taskId == null` for the palette proper.

Writes on a definition row apply to the whole name-group, workspace-wide. Measured live
on image 2.19.1:

| Call | Result |
|---|---|
| `DELETE /label/{definition-row}` | **200**, and every attachment of that name is destroyed |
| `DELETE /label/{attachment-row}` | 200, correctly scoped to that one task |
| `PUT /label/{definition-row}` renaming it | 200, and the whole group is renamed with it |
| `PUT /label/{definition-row}` colour only | 200, attachments untouched — no cascade |
| `PUT /label/{id}` without `name` | 400 schema error; `name` is required even to change a colour |

Two consequences worth internalising:

- **The status code tells you nothing about the blast radius.** A definition delete that
  removes 233 attachments and one that removes zero both answer `200` with the deleted
  row echoed. Verify by re-reading the workspace, never by the response.
- **The 400 comes afterwards, not instead.** `DELETE` on a row that no longer exists
  answers `400 Workspace ID could not be determined` — the same missing-row 400 tasks
  give. Delete a definition row, then try to clean up "its" attachments, and every one of
  those follow-up calls 400s because the cascade already took them. That reads as "the
  delete failed" while the data is already gone.

So: **attachments first, definition last**, and re-read to verify. `scripts/kaneo_labels.py`
does exactly that — `audit` for the workspace's label health, `delete --name X` which
refuses a definition-row delete until `--cascade` acknowledges the attachment count it
printed. Use it rather than hand-rolling the order.

`audit` also reports **attachments with no definition row** — a name live on tasks that the
palette no longer offers, so the UI cannot re-attach it. A long-lived workspace accumulates
these steadily, and names graduate out of the orphan set when someone re-creates the
definition. Run `audit` for the current set rather than carrying a remembered one.

## Unattributed status writes can double-step

On a GitHub-wired board, status moves itself: push → `in-progress`, PR → `in-review`,
merge → `done`. Those are logged with `userId: null`, which is normal — no human made them.

The failure is an unattributed write that puts a task **back** to the status it just left,
seconds after a real transition. The task then sits in a lane nobody chose. It self-heals
on the next event, so it is invisible unless something looks. Confirmed live on the DFA
board: two tasks, one reverted `in-progress` → `in-review` after 3s, the other after 43s.

`scripts/kaneo_status_drift.py --project <id>` scans a board's activity for exactly that
pattern (consecutive `status_changed` entries where the later is unattributed and undoes
the earlier, inside a window) and exits 1 when it finds any. Do not widen it to "any
unattributed write" — that fires on every healthy board.

## Gotchas

- Missing task → 400 "Workspace ID could not be determined" (treat as 404). The same 400
  answers a `DELETE /label/{id}` for a row that is already gone — **and a task id in the
  board's `PROJ-N` display form**, which is the id the UI shows and the one humans hand you.
  The error names the workspace and means the id format. `/task/{id}` and `/comment/{taskId}`
  both want the opaque record id, so build a number → id map once from
  `GET /task/tasks/{projectId}` and work in record ids after that.
- **`PATCH /task/{id}` is not a route** — it answers a bare `404 Not Found` and changes
  nothing. Use `PUT`, which is a **full-object replace, not a merge**: echo a fresh `GET`
  minus `{id, number, createdAt, assigneeName}`, and **omit null keys rather than echoing
  them back**. Two measured 400s:
  - body missing `position` → `Invalid key: Expected "position" but received undefined`.
    `position` is the field a hand-built body forgets; `projectId` is required too, and
    neither is obvious from the update you think you are making.
  - `"userId": null` echoed straight from the `GET` → `Invalid type: Expected string but
    received null`.

  Always re-`GET` immediately before the `PUT`: a stale echo silently reverts whatever
  transitioned in between.
- Reads answer with a `pagination` block — `{total, page, pageSize, totalPages}`. A silent
  clamp to `pageSize: 100`, returning page 1 of a larger board with no error, was reported
  against an earlier image; it did **not** reproduce on a 198-task project, which came back
  whole with accurate pagination and an honoured explicit `limit`. Read
  `pagination.totalPages` anyway: it is the only tell if the clamp returns, and a short
  `tasks` array carries no other warning.
- A busy board can push `list_tasks` past the MCP result cap on shape alone — one long
  description is enough, even with a `status` filter. The result spills to a file under the
  session's `tool-results/`; grep that file rather than paging it. The REST board read is the
  cheaper path when you need to search across lanes.
- Omit `priority` on create → validation error; default to "medium" only when
  you genuinely can't judge — an honest "medium" beats a fabricated rank.
- `/api/mcp` rejects `x-api-key` directly (it is OAuth 2.1 Bearer only), but a
  token minted from an agent key via `scripts/mint-mcp-token.sh` is accepted.
  That same token also authenticates REST.
