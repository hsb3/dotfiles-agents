# Claude Code extension surfaces — contracts + minimal examples

Each surface below lists: where files live, the frontmatter/config contract, a minimal working
example, and the trigger model. Subagents get their own reference (`subagents.md`); plugins and
marketplaces get theirs (`distribution.md`).

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

Hooks are the only surface that runs **without the model choosing to**. Configure them in a
`settings.json` (user, project, local, or managed) under a `hooks` block, keyed by event, with a
matcher and a command; plugins ship the same block in `hooks/hooks.json`, and a skill or agent can
carry a `hooks:` frontmatter map. Use a committed handler *script*, never inline shell — this is
non-negotiable, not a style preference, so the logic stays testable and reviewable.

Events (the commonly used subset; the reference lists 30+): `PreToolUse`, `PostToolUse`,
`PostToolUseFailure` (around a tool call; `PreToolUse` can block) · `PermissionRequest` ·
`UserPromptSubmit` (before a prompt is processed; can block) · `Notification` · `Stop`,
`SubagentStart`, `SubagentStop` · `PreCompact`, `PostCompact` · `SessionStart`, `SessionEnd` ·
`ConfigChange`, `FileChanged`, `InstructionsLoaded`, `WorktreeCreate`, `WorktreeRemove`.
Hook `type` is one of `command`, `http`, `mcp_tool`, `prompt`, `agent`. The `matcher` is a tool
name or regex for tool events (`Edit|Write`, `mcp__.*`); empty matches everything.

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

Hook I/O contract: a command handler receives the event payload as JSON on **stdin** and signals
outcome via **exit code** — `0` is success; `2` is a **blocking** error (stderr is fed back to
the agent and the action is blocked, where the event supports blocking; it cannot be overridden
by JSON); any other non-zero is a **non-blocking** error (the action proceeds) — and/or a JSON
object on **stdout** for structured control (`hookSpecificOutput`, `systemMessage`,
`additionalContext`, `updatedInput`). Handlers see `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`,
and `CLAUDE_PLUGIN_DATA`. Keep handlers fast and side-effect aware — they run inline on the
lifecycle.

Required layout: a **hook directory** — `hooks/<name>/` holding the handler (e.g. `hook.py`)
plus any config — rather than raw shell embedded in `settings.json`. A directory is versionable,
unit-testable, and portable into a plugin (a plugin ships hooks the same way; see
`distribution.md`). Keep handlers dependency-light so they run anywhere.

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

MCP (Model Context Protocol) servers expose external tools/resources the model can call. Declare
them in a project `.mcp.json` (project scope, shared via git); user and local scopes are stored in
`~/.claude.json` by `claude mcp add`, not in `settings.json`. A plugin can bundle its own
`.mcp.json` (or inline `mcpServers` in `plugin.json`).

```jsonc
// .mcp.json (project)
{
  "mcpServers": {
    "files": {                                   // stdio server: `type` optional (default)
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
      "env": { "LOG_LEVEL": "info" }
    },
    "api": {                                      // remote: `type` REQUIRED with a url
      "type": "http",                             // http (sse is deprecated; ws also accepted)
      "url": "https://mcp.example.com",
      "headers": { "Authorization": "Bearer ${API_TOKEN}" }   // ${VAR} and ${VAR:-default}
    }
  }
}
```

An MCP server's tools appear to the model as `mcp__<server>__<tool>` (plugin-bundled:
`mcp__plugin_<plugin>_<server>__<tool>`).
Reach for MCP when you need to *add* capabilities/data; reach for a **hook** when you need to
*gate or observe* the tool calls that already exist.

## 5. Settings & permissions — the control plane

Precedence (highest first): managed settings → `claude --settings` CLI → `.claude/settings.local.json`
(project, personal, git-ignored) → `.claude/settings.json` (project, shared) →
`~/.claude/settings.json` (user). Settings wire the other surfaces on and constrain them.

```jsonc
// .claude/settings.json
{
  "permissions": {
    "allow": ["Read", "Grep", "Bash(git status:*)", "Bash(git diff:*)"],
    "ask":   ["Bash(git push:*)"],
    "deny":  ["Read(./.env)", "Bash(rm -rf:*)"],
    "defaultMode": "acceptEdits"
  },
  "enabledPlugins": { "my-plugin@my-marketplace": true },   // object, not an array
  "hooks": { /* see §2 */ },
  "env": { "SOME_FLAG": "1" },
  "model": "sonnet"
}
```

Permission rules match `Tool(pattern)`: `allow` runs without prompting, `ask` prompts, `deny`
blocks outright. Rules are evaluated **deny, then ask, then allow** — the first match wins and
specificity does not reorder them, so a broad deny cannot carry allow exceptions. `Bash(git status *)`
and `Bash(git status:*)` are equivalent trailing-wildcard forms. `defaultMode` accepts `default`
(`manual`), `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`; `auto` and
`bypassPermissions` are ignored from project/local files. Scope tightly — a permission is the
guardrail that lets a subagent or hook run unattended safely. This is also where you turn plugins
on (`enabledPlugins`) and register `hooks`.

## Cross-references

- Subagents (the sixth surface) — `subagents.md`.
- Description/triggering quality, frontmatter validation, common failures — `authoring.md`.
- Bundling surfaces into a plugin and shipping via a marketplace — `distribution.md`.
