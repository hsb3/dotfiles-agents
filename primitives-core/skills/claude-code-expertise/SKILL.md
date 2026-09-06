---
name: claude-code-expertise
description:
  Expert map of Claude Code's extension surfaces for authoring and debugging extenders —
  skills, subagents, hooks, commands, plugins, marketplaces, MCP servers, and
  settings/permissions contracts. Use to decide which surface fits a need, to look up a
  surface's frontmatter or config contract, to author or debug a skill, subagent, hook,
  command, or plugin, or to answer how any Claude Code extension surface works. Not for
  changing settings, permissions, or hook wiring in a project - that is claude-code-config.
metadata:
  version: 0.1.0
  verified: 2026-09-06
---

# Claude Code Expertise

Claude Code is extensible through a small set of **distinct surfaces**, each with its own
contract, file location, and trigger model. The hardest part of extending it is usually not
authoring — it is picking the *right* surface for a need. This skill is the **map**: which
surface, which contract, what's idiomatic. It complements the official skill-authoring and
plugin-authoring builders (they scaffold and validate a chosen surface); it does not restate
their job — reach for a builder once this map has told you which surface you're building.

Claude Code moves quickly. Treat contracts below as accurate to the `verified` date; when a
field is rejected or a path is ignored, check the current official docs before assuming a bug.

## Surface-selection decision table

Start here. Match the need to the surface, then open the matching reference for the contract.

| You want to… | Surface | Why this one, not the others |
|---|---|---|
| Give the model reusable know-how / a procedure it pulls in **on demand** when a task matches | **Skill** | Model-invoked by description match; loads only when relevant. Not a command (no user keystroke) and not an agent (same context, no separate tool budget). |
| Run **deterministic code** automatically at a lifecycle moment (before/after a tool, on session start, on stop) | **Hook** | Only surface that executes on an event without the model choosing to. A skill can't fire on an event; a command needs a user to type it. |
| Offload a **bounded sub-task to a fresh context** with its own tool set and model tier | **Subagent (agent)** | Separate context window + independent tool/model selection. A skill runs in the *same* context; a hook can't reason. |
| Give the user a **typed slash shortcut** that expands to a prompt/workflow | **Command** (now a skill) | Commands were merged into skills: `.claude/commands/x.md` and `.claude/skills/x/SKILL.md` both create `/x`. Write new ones as skills; `disable-model-invocation: true` makes a skill user-only. |
| Connect an **external tool or data source** (API, DB, service) as callable tools | **MCP server** | The protocol for external tools/resources. Not a hook (hooks gate/observe existing tools; they don't add tool servers). |
| **Package and distribute** several of the above as one installable unit | **Plugin** | The bundling unit. Contains skills/agents/commands/hooks/MCP together. |
| Let users **discover and install** your plugins by name | **Marketplace** | The registry a plugin is installed *from*. One marketplace lists many plugins. |
| **Gate tool use, set defaults, or wire the above on** for a project or user | **Settings / permissions** | `settings.json` is where permissions, enabled plugins, hooks, env, and model live. |

Two frequent confusions, resolved:

- **Skill vs. subagent.** Both carry expertise. A **skill** injects knowledge into the *current*
  agent's context (no isolation, no separate tool budget). A **subagent** runs the work in a
  *separate* context with its own tools and model — choose it when the sub-task is large, noisy,
  or needs a different tool/tier than the main thread. See `references/subagents.md`.
- **Hook vs. skill vs. command.** A **hook** is the only surface that fires on an *event* without
  anyone choosing to run it; use it for guardrails, telemetry, and automation. A **skill** fires
  when the model judges a task relevant *or* when a user types `/<name>`; a legacy **command**
  file is the same thing with fewer features (no supporting files, no invocation control).

## Surface map (one-line contracts)

| Surface | Canonical artifact | Lives (project · user) | Trigger | Reference |
|---|---|---|---|---|
| Skill | `SKILL.md` + optional `references/`, `scripts/`, `assets/` | `.claude/skills/<name>/` · `~/.claude/skills/<name>/` | model, by description match | `references/surfaces.md` |
| Subagent | one `.md` with frontmatter | `.claude/agents/<name>.md` · `~/.claude/agents/<name>.md` | model (auto) or explicit request | `references/subagents.md` |
| Hook | handler script + config | `settings.json` `hooks` block (user, project, local, managed) · plugin `hooks/hooks.json` · skill/agent frontmatter | lifecycle event | `references/surfaces.md` |
| Command (legacy) | one `.md`, body is the prompt | `.claude/commands/<name>.md` (a user-scope commands dir is no longer documented; use `~/.claude/skills/`) | user types `/<name>` | `references/surfaces.md` |
| MCP server | server entry in `.mcp.json` / `~/.claude.json` | `.mcp.json` (project) · `~/.claude.json` (user and local scopes, not `settings.json`) | model calls the server's tools | `references/surfaces.md` |
| Plugin | `.claude-plugin/plugin.json` + surface dirs | a plugin repo/dir | installed, then its surfaces load | `references/distribution.md` |
| Marketplace | `.claude-plugin/marketplace.json` | a marketplace repo/dir | `/plugin marketplace add`, then install | `references/distribution.md` |
| Settings/permissions | `settings.json` | `.claude/settings.json` (+ `.local`) · `~/.claude/settings.json` | always in effect | `references/surfaces.md` |

## Authoring principles (apply to every surface)

- **Description quality is the trigger.** For skills and subagents the `description` is what the
  model matches on. Say *what it does AND when to use it*, name the concrete situations, and
  keep it free of angle-bracket tags (the docs say Claude Code escapes them; the older claim that a
  tag makes a skill fail to load is unverified). A vague description means the surface never
  fires. See `references/authoring.md`.
- **Progressive disclosure.** Keep the entry file lean; push depth into `references/*.md` the
  entry file *points to*. The model reads the pointer first and pulls a reference only when
  needed — this keeps context small and relevance high.
- **Least privilege.** Grant a subagent only the tools it needs; scope permissions with `allow` /
  `ask` / `deny`. Broad tool access dilutes intent and raises risk.
- **Validate before shipping.** Frontmatter present and well-formed, the directory name is the
  `/name` you expect (`name` is optional and only a display label for project/user skills),
  relative links resolve inside the folder, no machine-specific paths baked in.
  `claude plugin validate <dir>` checks plugin and marketplace manifests plus skill, agent, and
  command frontmatter.

## Read next (progressive disclosure)

- `references/surfaces.md` — every surface with its frontmatter/config contract, a minimal
  working example, and where files live (skills, hooks, commands, MCP, settings/permissions).
- `references/subagents.md` — authoring subagents end to end: scaffold, tool selection, model /
  tier choice, and writing the when-to-use description that makes delegation fire.
- `references/authoring.md` — frontmatter contracts, description/triggering quality, progressive
  disclosure, and a validation + common-failure checklist.
- `references/distribution.md` — plugin structure, marketplace registration, versioning, and the
  enable / install mechanics that ship the above to a user.
