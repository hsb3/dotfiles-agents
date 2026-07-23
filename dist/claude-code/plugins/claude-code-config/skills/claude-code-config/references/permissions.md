# Permissions

The `permissions` key decides what the agent may do without asking, what it must ask about, and
what it may never do. The governing principle is **narrowest scope that works**: grant the least
that unblocks the task, in the most local file that covers it.

## Shape

```json
{
  "permissions": {
    "allow": ["Bash(npm run test:*)", "Read(src/**)"],
    "ask":   ["Bash(git push:*)"],
    "deny":  ["Read(.env)", "Bash(rm -rf:*)"],
    "defaultMode": "default",
    "additionalDirectories": ["../shared-lib"]
  }
}
```

- **`allow`** — permitted without a prompt.
- **`ask`** — permitted only after an interactive confirmation.
- **`deny`** — never permitted, and not promptable.
- **`defaultMode`** — how tool calls that match *no* rule are handled (see modes below).
- **`additionalDirectories`** — extra paths the agent may read/operate in beyond the project root.

A validatable copy is in `references/examples/permissions.settings.json`.

## Rule grammar

A rule is a tool name, optionally with a parenthesized specifier that narrows *which* uses of
that tool it covers:

```
ToolName                     every use of the tool
ToolName(specifier)          only uses matching the specifier
```

| Rule | Matches |
|---|---|
| `Bash(npm run test:*)` | any Bash command beginning `npm run test` (the `:*` means "any continuation") |
| `Bash(git diff:*)` | any `git diff …` command |
| `Bash(git push:*)` | any `git push …` command (good candidate for `ask`, not `allow`) |
| `Read(src/**)` | reading any file under `src/` (gitignore-style path glob) |
| `Edit(docs/**)` | editing any file under `docs/` |
| `Read(.env)` | reading the `.env` file (a good `deny`) |
| `WebFetch(domain:example.com)` | fetching from that domain only |
| `mcp__server-name` | any tool from that MCP server |
| `mcp__server-name__tool-name` | one specific MCP tool |

Path specifiers follow gitignore semantics — a leading `//` anchors an absolute path and `~`
means home; a bare pattern is relative to the project. Bash specifiers match the command
**prefix**; append `:*` to allow any arguments after the matched prefix, or omit it to match the
exact command only.

## Evaluation order

For a given tool call, rules are checked in this precedence: **`deny` wins, then `ask`, then
`allow`.** A call that matches no rule falls through to `defaultMode`. So a broad `allow` never
overrides a matching `deny`, and you can safely `allow(Bash(git:*))` while keeping
`deny(Bash(git push --force:*))`.

## Default modes

`defaultMode` sets the behavior for unmatched calls:

| Mode | Unmatched tool call is… |
|---|---|
| `default` | prompted for (the standard interactive behavior) |
| `acceptEdits` | auto-accepted for file edits, still prompted for others |
| `plan` | plan-only; the agent proposes but does not execute |
| `bypassPermissions` | run without prompts — dangerous; reserve for sandboxes you trust |

Prefer explicit `allow`/`deny` rules over loosening the default mode. A broad default mode is
the widest possible grant.

## Moving a rule between scopes

A rule "lives" wherever you put the `permissions` block. To move one:

1. **Decide the target scope** — narrowest that covers the need (project-local, project-shared,
   or user). A machine-specific or personal relaxation belongs in `.claude/settings.local.json`,
   never in the committed `.claude/settings.json`.
2. **Add the rule to the target file's `permissions` block** (create the block if absent).
3. **Remove it from the old file** so there is one source of truth and no confusing override.
4. **Validate both files** (`python3 -m json.tool < FILE`) and **verify** with `/permissions`.

Remember precedence across files: a `deny` in a higher-precedence file (managed policy, or
project-local) will override an `allow` you add lower down. If a rule "won't take", check whether
a higher file contradicts it.

## Narrowest-scope-that-works, in practice

- Prefer `Bash(npm run test:*)` over `Bash(npm:*)` over `Bash(*)` over a bare `Bash`.
- Prefer `Read(config/**)` over `Read(**)`.
- Put a broad convenience allow in your **user** file only if you truly want it everywhere;
  otherwise keep it project-local.
- Encode the dangerous cases as **`deny`** (they cannot be prompted past), not as reminders.
- When you must widen a rule to unblock a task, widen the *specifier*, not the tool — and put it
  in the narrowest file.
