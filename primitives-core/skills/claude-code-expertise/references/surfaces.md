# Claude Code extension surfaces — contracts + minimal examples

Each surface below lists: where files live, the frontmatter/config contract, a minimal working
example, and the trigger model. Subagents get their own reference (`subagents.md`); plugins and
marketplaces get theirs (`distribution.md`).

Paths use `.claude/` for the **project** scope and `~/.claude/` for the **user** (personal)
scope. Plugins carry the same surfaces in their own subdirectories (see `distribution.md`).

## 1. Skills — model-invoked knowledge/procedure

Location: `.claude/skills/<name>/SKILL.md` (project) · `~/.claude/skills/<name>/SKILL.md` (user).
The folder may also hold `references/`, `scripts/`, and `assets/`. `<name>` matches the folder.

```markdown
---
name: my-skill                # required; lowercase-kebab; must equal the folder name
description: >                 # required; what it does AND when to use it — the trigger
  Do X for Y. Use when the user asks to <plain-language situations>, or when a task
  involves <concrete cues>.
allowed-tools: Read, Grep      # optional; restrict the tools available while the skill is active
---

# My Skill

Instructions the model follows once the skill activates. Keep this lean; point to
`references/deep-dive.md` for depth (progressive disclosure).
```

Trigger: the model reads all skill `description`s and activates one when a task matches. There is
no user keystroke. Because activation is description-driven, description quality is decisive
(see `authoring.md`). Keep `description` free of angle-bracket/XML tags — a bracketed tag there
can prevent the skill from loading.

## 2. Hooks — deterministic code on a lifecycle event

Hooks are the only surface that runs **without the model choosing to**. Configure them in
`settings.json` under a `hooks` block, keyed by event, with a matcher and a command. Use a
committed handler *script*, never inline shell — this is non-negotiable, not a style preference,
so the logic stays testable and reviewable.

Events (by lifecycle): `PreToolUse`, `PostToolUse` (fire around a tool call; `PreToolUse` can
block) · `UserPromptSubmit` (before a prompt is processed) · `Notification` · `Stop`,
`SubagentStop` (a main/sub agent finished a turn) · `PreCompact` (before context compaction) ·
`SessionStart`, `SessionEnd`.

```jsonc
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",                       // tool name / pattern this rule applies to
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-bash/hook.py\"" }
        ]
      }
    ]
  }
}
```

Hook I/O contract: the handler receives the event payload as JSON on **stdin** and signals
outcome via **exit code** — `0` is success; `2` is a **blocking** error (stderr is fed back to
the agent and the action is blocked, where the event supports blocking); any other non-zero is a
**non-blocking** error (surfaced to the user, but the action proceeds) — and/or a JSON object on
**stdout** for structured control. Keep handlers fast and side-effect aware — they run inline on
the lifecycle.

Required layout: a **hook directory** — `hooks/<name>/` holding the handler (e.g. `hook.py`)
plus any config — rather than raw shell embedded in `settings.json`. A directory is versionable,
unit-testable, and portable into a plugin (a plugin ships hooks the same way; see
`distribution.md`). Keep handlers dependency-light so they run anywhere.

## 3. Commands — user-typed slash shortcuts

Location: `.claude/commands/<name>.md` (project) · `~/.claude/commands/<name>.md` (user).
Subdirectories namespace a command (`.claude/commands/git/sync.md` → `/git:sync`).

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
(all args) and `$1`, `$2`, … (positional); `` !`cmd` `` injects a shell command's output;
`@path` includes a file's contents. Use a command when a **human** must initiate the action; use
a skill when the **model** should decide to.

## 4. MCP servers — external tools and data

MCP (Model Context Protocol) servers expose external tools/resources the model can call. Declare
them in a project `.mcp.json` (or in user settings); a plugin can bundle its own `.mcp.json`.

```jsonc
// .mcp.json (project)
{
  "mcpServers": {
    "files": {                                   // stdio server: a local process over stdio
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
      "env": { "LOG_LEVEL": "info" }
    },
    "api": {                                      // remote server: HTTP/SSE transport
      "type": "http",
      "url": "https://mcp.example.com",
      "headers": { "Authorization": "Bearer ${API_TOKEN}" }
    }
  }
}
```

An MCP server's tools appear to the model as callable tools (typically namespaced by server).
Reach for MCP when you need to *add* capabilities/data; reach for a **hook** when you need to
*gate or observe* the tool calls that already exist.

## 5. Settings & permissions — the control plane

Precedence (narrowest wins): `.claude/settings.local.json` (project, personal, git-ignored) →
`.claude/settings.json` (project, shared) → `~/.claude/settings.json` (user). Settings wire the
other surfaces on and constrain them.

```jsonc
// .claude/settings.json
{
  "permissions": {
    "allow": ["Read", "Grep", "Bash(git status:*)", "Bash(git diff:*)"],
    "ask":   ["Bash(git push:*)"],
    "deny":  ["Read(./.env)", "Bash(rm -rf:*)"],
    "defaultMode": "acceptEdits"
  },
  "enabledPlugins": ["my-plugin@my-marketplace"],
  "hooks": { /* see §2 */ },
  "env": { "SOME_FLAG": "1" },
  "model": "sonnet"
}
```

Permission rules match `Tool(pattern)`: `allow` runs without prompting, `ask` prompts, `deny`
blocks outright (`deny` wins over `allow`). Scope tightly — a permission is the guardrail that
lets a subagent or hook run unattended safely. This is also where you turn plugins on
(`enabledPlugins`) and register `hooks`.

## Cross-references

- Subagents (the sixth surface) — `subagents.md`.
- Description/triggering quality, frontmatter validation, common failures — `authoring.md`.
- Bundling surfaces into a plugin and shipping via a marketplace — `distribution.md`.
