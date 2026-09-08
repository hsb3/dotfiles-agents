# Claude Code extension surfaces — contracts + minimal examples

Each surface below lists what you need to **choose** it: where files live and the trigger
model, with the contract and a worked example where authoring it is this skill's job. Hooks,
MCP servers, and settings/permissions are covered here only far enough to pick one — their
config contracts, wiring, and examples belong to `claude-code-config`. Subagents get their own
reference (`subagents.md`); plugins and marketplaces get theirs (`distribution.md`).

Paths use `.claude/` for the **project** scope and `~/.claude/` for the **user** (personal)
scope. Plugins carry the same surfaces in their own subdirectories (see `distribution.md`).

## 1. Skills — model-invoked knowledge/procedure

Location: `.claude/skills/<name>/SKILL.md` (project) · `~/.claude/skills/<name>/SKILL.md` (user) ·
`<plugin>/skills/<name>/SKILL.md` (plugin). Project skills also load from parent directories up to
the repo root; nested `.claude/skills/` below the cwd load when Claude touches files there. The
folder may also hold `references/`, `scripts/`, and `assets/`. The **folder name is the `/name`**
the user types; frontmatter `name` is only a display label for project/user skills (for plugin
skills it sets the last segment of `/plugin:name`).

```markdown
---
name: my-skill                # optional; display label (keep it equal to the folder by convention)
description: >                 # recommended; what it does AND when to use it — the trigger
  Do X for Y. Use when the user asks to <plain-language situations>, or when a task
  involves <concrete cues>.
allowed-tools: Read, Grep      # optional; PRE-APPROVES these tools for the invoking turn (no prompt)
disallowed-tools: Write        # optional; removes tools from the pool while the skill is active
disable-model-invocation: true # optional; user-only (/name); default false
user-invocable: false          # optional; model-only (hidden from the / menu); default true
context: fork                  # optional; run in a forked subagent (with optional agent: <type>)
paths: "src/**/*.ts"           # optional; auto-activate only when working on matching files
metadata: { version: 0.1.0 }   # optional; free-form map, ignored by Claude Code
---

# My Skill

Instructions the model follows once the skill activates. Keep this lean; point to
`references/deep-dive.md` for depth (progressive disclosure).
```

Trigger: the model reads all skill `description`s and activates one when a task matches, **or**
the user types `/<name>` (skills replaced custom commands; if a skill and a `.claude/commands/`
file share a name, the skill wins). Because auto-activation is description-driven, description
quality is decisive (see `authoring.md`). `description` + `when_to_use` are truncated at 1,536
characters in listings. Keep `description` free of angle-bracket/XML tags — the docs say Claude
Code escapes them; whether an unescaped tag can still prevent loading is unverified.

## 2. Hooks — deterministic code on a lifecycle event

Hooks are the only surface that runs **without the model choosing to** — deterministic code fires
on a lifecycle event (a tool call, a prompt, session start, etc.), regardless of what the model
decides. They can live in `settings.json`, in a plugin's `hooks/hooks.json`, or inline as a
`hooks:` frontmatter map on a skill or agent.

Trigger: the configured lifecycle event fires; there is no model judgment in the loop. Reach for
a hook when the requirement is "always do X on event Y" — the full event list, wiring format, and
I/O contract are covered in `claude-code-config`.

## 3. Commands — user-typed slash shortcuts

Location: `.claude/commands/<name>.md` (project; legacy). Custom commands were **merged into
skills**: `.claude/commands/deploy.md` and `.claude/skills/deploy/SKILL.md` both create `/deploy`,
the skill wins on a name clash, and a user-scope commands directory is no longer documented (use
`~/.claude/skills/`). A command file takes the same frontmatter as a skill except `name` and
`paths`. The command name is the **file name only** — subdirectories do not namespace it
(`.claude/commands/git/sync.md` → `/sync`). Namespacing exists for *nested skills*
(`apps/web/.claude/skills/deploy/SKILL.md` → `/apps/web:deploy` on a clash) and for plugins
(`/plugin:name`).

```markdown
---
description: Sync the current branch with its upstream and summarize what changed
argument-hint: [branch]        # optional; shown in the UI as the expected argument
allowed-tools: Bash(git:*)     # optional; scope the tools the command may use
model: sonnet                  # optional; pin a model for this command
---

Sync branch $ARGUMENTS with upstream. Current state: !`git status -sb`.
Follow the conventions in @docs/branching.md.
```

Trigger: the user types `/<name>`. The body is a prompt template. Substitutions: `$ARGUMENTS`
(all args) and `$ARGUMENTS[N]` / `$N` (positional, **0-based**: `$0` is the first argument);
`` !`cmd` `` injects a shell command's output; `@path` includes a file's contents;
`${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}` expand. For a
human-only trigger write a skill with `disable-model-invocation: true`; for a model-only one,
`user-invocable: false`.

## 4. MCP servers — external tools and data

MCP (Model Context Protocol) servers expose external tools/resources the model can call, adding
new capability rather than changing how existing tools are used. A plugin can bundle its own
server too.

Trigger: the model calls an MCP tool like any other tool, whenever its description matches the
task — no lifecycle event required. Reach for MCP when you need to *add* capabilities/data; reach
for a **hook** when you need to *gate or observe* the tool calls that already exist. Where servers
are declared, scoped, and registered is covered in `claude-code-config`.

## 5. Settings & permissions — the control plane

Settings files (managed, project, project-local, and user, layered by precedence) wire every
other surface on and constrain what the agent may do — which tools run without asking, which are
denied outright, which plugins are enabled, and what hooks/env/model apply.

Trigger: settings apply continuously, not on a discrete event — they are the layer every other
surface's behavior is read through. Reach for settings when the ask is "always allow/deny/ask
this tool", "turn a plugin on", or "set this for every session". File precedence, the permission
rule grammar, and default modes are covered in `claude-code-config`.

## Cross-references

- Subagents (the sixth surface) — `subagents.md`.
- Description/triggering quality, frontmatter validation, common failures — `authoring.md`.
- Bundling surfaces into a plugin and shipping via a marketplace — `distribution.md`.
- Actually wiring a hook, an MCP server, or a permission rule once you have chosen it —
  `claude-code-config`, which owns those contracts.
