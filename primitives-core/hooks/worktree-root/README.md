# worktree-root

Takes over Claude Code's worktree creation so worktrees land under the project's
`checkout-root` instead of `.claude/worktrees/`. One `hook.py` handles three events.
Delivered as a plugin it covers subagent `isolation: worktree` and `EnterWorktree`;
`claude --worktree` creates its worktree before plugin hooks load, so that path stays native.

| Event | What it does |
|---|---|
| `WorktreeCreate` | Creates `<root>/<name>` on branch `worktree-<name>` (`/` becomes `+` in both) and prints the resolved path; a name already registered as a linked worktree is resumed (path printed, tree untouched) |
| `SubagentStop` | Removes an agent's worktree and branch when the tree is clean and the branch holds no commit that no other branch, tag or remote ref has |
| `WorktreeRemove` | Removes a registered worktree inside `<root>` (`ExitWorktree` with remove) and deletes its `worktree-*` branch; any other path exits 1 and is left in place |

## Placement

`<root>` is the `checkout-root:` key of the main checkout's atelier activation file,
read through the shared `_lib/atelier_local.py`. Unset means the native
`<main checkout>/.claude/worktrees`. Both are anchored on the **main** checkout, so a
dispatch from inside a linked worktree never nests.

Creation fails loudly (exit 1, reason on stderr) when the key is invalid (a `$`
variable, a path outside the project or inside `.git`, a symlink that escapes), when the
root resolves outside the main checkout (a committed `.claude` or `.claude/worktrees`
symlink), or when the name is empty, absolute, holds a `..` segment, is a symlink, or
names an existing path that is not a registered worktree. There is no silent fallback to
the native location. A `.worktreeinclude` copy error rolls the new worktree and branch back.

## Parity with native creation

- **Base ref**: `worktree.baseRef: "head"` (settings.local.json, then settings.json,
  then `$CLAUDE_CONFIG_DIR/settings.json` or `~/.claude/settings.json`) branches from the
  session's HEAD. Otherwise, when `origin` exists and `FETCH_HEAD` is missing or older
  than a day, it runs `git fetch origin <default branch>` (15 s cap; failure is a stderr
  note), then uses `origin/HEAD`, else `origin/main`, else HEAD.
- **`.worktreeinclude`**: copies files that are untracked, gitignored, and matched by
  its gitignore-syntax patterns. Tracked files, unignored files and symlinks are never
  copied.
- **Agent cleanup**: the harness keeps every hook-created agent worktree, so
  `SubagentStop` restores native cleanup. It acts only when the stop's `cwd` is
  exactly `<root>/agent-<agent_id>` on branch `worktree-agent-<agent_id>`.

`SubagentStop` always exits 0 and writes nothing to stdout.

## Configuration

| Setting | Where | Meaning |
|---|---|---|
| `checkout-root` | activation file frontmatter | Directory, relative to the main checkout, that holds new worktrees |
| `worktree.baseRef` | Claude Code settings | `head` branches from HEAD; anything else follows origin (see Base ref) |

## Known limits

- **Settings files, not effective settings.** `worktree.baseRef` is read from the files
  above, so `--settings`, `--setting-sources` and managed settings can give the hook a
  different base than native creation would pick (measured live).
- **SubagentStop runs beside other SubagentStop hooks.** When another hook blocks the
  stop, this one may already have removed the clean worktree the subagent keeps using.
- **Native session features are not replicated.** `EnterWorktree` by path only accepts
  worktrees under `.claude/worktrees`, and native `--worktree` sessions git-lock their
  worktree; worktrees created under a `checkout-root` get neither.
- **Ignored files do not count as work.** Clean-agent removal uses `--force`, so ignored
  files the agent wrote are deleted with the worktree.
