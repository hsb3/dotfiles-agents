# Access model

How board authority is split across agent levels, and exactly how far the
enforcement goes. The design record behind these choices is a `decision` task on
the KANEO board; this file is the part you need to operate the plugin.

## Enforcement ceiling — read this first

Enforcement is **sound only for MCP-tool calls, by agents whose network access is
MCP tools.** Tool allowlists are hard-enforced by the harness, and the hook
floor-deny is hard for MCP calls.

Both credentials live in the shared process environment (`KANEO_API_KEY` for root
REST ops and minting; `KANEO_MCP_TOKEN`, which also authenticates REST), so any
subagent with Bash can reach the board via `curl "$KANEO_API_URL/..."`, a
python/node one-liner, or a written script. No string guard can close that. The
Bash guard is an **advisory tripwire**: it catches the naive path and leaves an
audit trail, nothing more.

The only sound configuration for an untrusted level is *no Bash*, which
code-writing workers cannot have. For a single-owner self-hosted instance this
ceiling is accepted — but do not describe this plugin as containment.

## Levels

| Level | Gets | Why |
|---|---|---|
| Root session | all board tools + REST via Bash | claim authority lives here |
| L2 managers | the L2 set below | append-only or read-only, race-free |
| L3 workers | no board tools (frontmatter) | report upward |

**L2 set** (allowed to subagents): `whoami`, `list_workspaces`, `list_projects`,
`get_project`, `list_tasks`, `get_task`, `list_task_comments`,
`create_task_comment`, `create_task`, `list_workspace_labels`,
`get_task_relations`.

**Claim-authority set** (root only — the hook's subagent deny set): everything
else, including `update_task`, `update_task_status`, `move_task`,
`update_task_comment`, `delete_task_comment`, `create_project`, `update_project`,
and all label and task-relation mutations. The hook is allowlist-based, so tools
added by a future image bump default to denied.

**Honest limit (L2 vs L3):** the hook sees only "subagent vs main"
(`agent_id`/`agent_type` presence), not which level an agent name is. It therefore
grants the L2 set to *any* subagent; keeping L3 at none rests on per-repo
frontmatter alone. `agents/kaneo-manager.md` is a reference L2 agent — consuming
repos' own definitions carry the real allowlists.

## Hook policy

- **Floor deny** (hard, MCP calls only): subagent context + a tool outside the L2
  set → `permissionDecision: "deny"` with a reason.
- **Stamping** (MCP `create_task_comment` and `create_task` only): appends
  `— [<agent_type or root>, session <session_id>]` to content/description,
  idempotently so retries don't double-stamp. Stated precisely: **MCP comments and
  task creations are always stamped.** REST-path mutations and non-stamped MCP
  tools are attributed by Kaneo's own per-identity user attribution, not by stamps.
  Because `updatedInput` requires an explicit allow, these two append-only tools
  are auto-approved — accepted in the design.
- **Bash tripwire** (advisory): denies subagent Bash commands containing the
  instance host or the strings `KANEO_API_URL` / `KANEO_CLIENT_URL`. No-op when the
  env is unset. Costs one hook process per Bash call in enabled repos.

Hook matchers are regex — `mcp__kaneo__.*`, never `mcp__kaneo__*`, which is a
glob-looking regex that matches by accident. The live tool prefix is pinned:
a plugin-registered server surfaces `mcp__plugin_kaneo_kaneo__<tool>`, a directly
registered one `mcp__kaneo__<tool>`. A wrong prefix fails open, and silently.

## Claim ritual stays on REST at 2.16.4

MCP's only assignee path is full-object `update_task` (read-merge-write). Racing
the GitHub integration's push-driven status transition, a stale snapshot would
silently revert it — the exact thing `SKILL.md` forbids. So the claim ritual
(assignee + status + claim comment) stays the REST sequence in `SKILL.md`, root
session only, and its claim comment is stamped by hand because REST is not
hook-stamped. Everything else is MCP-first. When the 2.17.1 bump lands
`update_task_assignee`, the ritual moves to MCP field-scoped tools.
