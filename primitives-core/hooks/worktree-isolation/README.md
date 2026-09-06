# worktree-isolation

`PreToolUse` on the `Agent` tool. When the project's activation file turns it on, a dispatch that
would put a **writing** worker in the orchestrator's own checkout is rewritten to carry
`isolation: "worktree"`, so the worker gets its own git worktree instead of sharing the working
tree and index the session is using.

It fails open on every error path and never denies a dispatch — forcing a worktree is a
correction, not a refusal.

## Why

`builder` and `manager` edit files, and a subagent inherits the parent session's working directory
by default. Two writers in one wave, or one writer alongside a strategist who is mid-edit, share an
index and a tree; the cross-contamination is invisible until integration. The delegation skill has
always *asked* for isolation on write-waves, but a request in prose is honoured only when the
dispatching session remembers it.

## What it deliberately does not isolate

A git worktree is a clean checkout of a ref, so **uncommitted and untracked files in the parent
checkout do not exist inside it**. A `scout` sent to inventory the working diff, or a `reviewer`
sent to re-derive a claim from files the session has not committed, would silently read a different
tree and report on nothing. Read-only roles stay in the parent checkout, which is also where they
are cheapest.

`scout`, `reviewer`, `Explore`, `Plan`, and `fork` are never rewritten, even when named explicitly
in an `isolate:` list. `fork` is excluded for a second reason: it inherits the conversation, so its
premise is continuity with the caller.

## Activation

Shared with the other atelier hooks: `<project>/.claude/atelier.local.md`, YAML frontmatter, parsed
by a small tolerant reader (stdlib only, no PyYAML).

```markdown
---
enforce: strict
isolate: writers
---
```

This hook reads only `isolate:`. Two forms:

| `isolate:` | Effect |
|---|---|
| absent, `off`, any other scalar, or an unparseable file | inert |
| `writers` | isolates `builder`, `manager`, `general-purpose` |
| a list (block or `[a, b]` inline) | isolates exactly those agent types |
| an empty list, or a bare `isolate:` with no items | inert — an empty set is an empty intent, not a request for the built-ins |

A plugin-namespaced type matches its bare form, so `atelier:builder` is covered by `builder`. A
dispatch with no `subagent_type` resolves to `general-purpose`, which carries the full tool set, so
absence counts as a writer.

## Inert paths

Beyond an unarmed activation file, the hook stands down when:

- the dispatch already sets `isolation` (including `remote`, which it must not downgrade);
- the dispatch sets `cwd`, documented as mutually exclusive with `isolation: "worktree"`;
- the agent type is in the never-isolate set above;
- the project is not a git repository. This one is not cosmetic: Claude Code raises
  `Cannot create agent worktree: not in a git repository`, so forcing isolation there would turn a
  guardrail into a hard failure on every dispatch.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/worktree-isolation plugins/atelier/hooks/worktree-isolation`
3. Add a roster row to `primitives-core.yaml` (id `worktree-isolation`, type `hook`, source
   `primitives-core/hooks/worktree-isolation`, origin `authored`, disposition `qualified`, targets
   `[claude-code]`) — `make ci` reconciles the roster against disk and requires every field,
   `targets` included.
4. Add the `PreToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/worktree-isolation/hook.py\"",
            "statusMessage": "Checking worker isolation...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "Agent"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | set by Claude Code | Anchor for the activation file and the git check; falls back to the payload `cwd` |
| `ATELIER_ACTIVATION_FILE` | `$CLAUDE_PROJECT_DIR/.claude/atelier.local.md` | Activation file location |
| `WORKTREE_ISOLATION_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/worktree-isolation.jsonl` | Ledger override |

## Ledger

One row per armed dispatch, appended to the `worktree-isolation` stream once the activation file
is on. Nothing is logged while the hook is inert (unarmed, `isolation`/`cwd` already set, or no
resolvable project dir) — those paths exit before the logger is even opened.

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/worktree-isolation.jsonl
```

Each row carries the identity envelope (`v`, `plugin`, `harness`, `stream`, `ts`, `project`) plus
`session_id`, `agent_type`, `mode`, `isolated` (bool), and `reason` (`null` when isolated, else
`"agent type not armed"` or `"project dir is not a git repo"`). A row written from the fail-open
error path also carries `error` and a truncated `traceback`.

## Design notes

- **Rewrite, never deny.** `hookSpecificOutput.updatedInput` (PreToolUse only) replaces the tool
  input in place, so the dispatch proceeds with isolation added rather than bouncing back for the
  model to retry. Verified by live probe against Claude Code 2.1.220: the subagent landed in
  `.claude/worktrees/agent-<id>`.
- **Announced, not silent.** The rewrite moves the worker to a checkout where the session's
  uncommitted work does not exist. That is worth one line of `systemMessage`, so a surprised reader
  can trace the behaviour to this hook rather than to the harness.
- **Fail-open, always.** Every path exits 0. An un-isolated worker is the pre-hook status quo and
  merely risky; a hook that crashes on every dispatch is an outage.
- **The activation parser is duplicated, on purpose.** Each hook directory is copied and symlinked
  on its own, so a shared module would be a cross-hook import path that breaks the moment one hook
  is installed without the other.
- **Base ref is a separate setting.** A new worktree branches from `origin/<default-branch>` unless
  the project sets `{"worktree": {"baseRef": "head"}}` in settings.json (values `fresh`, the
  default, or `head`). Where the default branch is a publish-only surface, `head` is the one that
  gives workers the branch the session is actually on.
- **No restart needed to change policy.** The activation file is read on every dispatch, so edits
  take effect on the next one. Only a change to `hooks.json` requires restarting the session.
