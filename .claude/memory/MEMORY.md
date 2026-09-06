# Memory Index

- [Signals that lie](signals-that-lie.md) — `make ci` ✗ lines, mermaid-cli exit 0, Kaneo bulk-write reverts, probe harnesses that test nothing: judge by end state
- [Measure a heuristic against a corpus](measure-a-heuristic-against-a-corpus.md) — a scanner can pass every test and be 79% precise; replay over git history, score against a stdlib parser
- [No unguarded counts in prose](no-unguarded-counts-in-prose.md) — a count needs a gate that checks it, else phrase it so growth can't falsify it
- [Tracker workflow rulings](feedback-tracker-workflow.md) — work the owner's queue on kata; reproduce before building or closing a card; close by hand on the dev merge
- [Use subagents for labor](feedback-use-subagents-for-labor.md) — the session keeps the foreman floor; edit chains, sweeps, and verification get briefs
- [Subagent runtime traps](subagent-runtime-traps.md) — /clear re-homes a running agent (key on agent_id, widen only the settled set); `memory:` frontmatter litters the tree
- [Worktree isolation](worktree-isolation.md) — two levers to force it; nested `worktree.baseRef` key; a worktree never sees uncommitted work
- [Plugin enablement needs a per-project install](plugin-enablement-needs-per-project-install.md) — `enabledPlugins` is inert without an install record; a stale project-scope record pins that repo; marketplace update does not install
- [Identity gate blocks personal-repo installs](identity-gate-blocks-personal-repo-installs.md) — the owner handle is an unconditional ban; `gh search --owner @me` is the only legal shape and only works for the owner
- [Harness claude invocation](harness-claude-invocation.md) — never `--bare` (it strips the Skill tool); per-run apiKeyHelper + fresh CLAUDE_CONFIG_DIR
- [launchd = bash 3.2](launchd-bash32-scripts.md) — verify LaunchAgent scripts with `/bin/bash`, not the interactive shell
- [opencode deferred, not abandoned](opencode-deferred-not-abandoned.md) — keep the opencode targets and generator; card 63nm
