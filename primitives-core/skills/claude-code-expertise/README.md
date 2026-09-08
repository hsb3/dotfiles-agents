# claude-code-expertise

Expert map of Claude Code's extension surfaces — skills, subagents, hooks, commands, plugins,
marketplaces, MCP servers, and settings/permissions — for authoring and debugging extenders.

## When it triggers

Use it to decide which surface fits a need, to look up a skill's or command's frontmatter
contract, or to answer how any Claude Code extension surface triggers. It is the *map* (which
surface, which trigger model, what's idiomatic) — it complements the official skill- and
plugin-authoring builders rather than duplicating them, and it does not itself scaffold or
install anything. For hooks, MCP, and settings/permissions it covers the selection question only
("which surface, and why") and defers their configuration contract to `claude-code-config` —
`references/surfaces.md` says so in its own header, so a reader who lands there directly is not
promised a contract it no longer carries. Plugin-bundled MCP tool naming stays here, in
`references/distribution.md`, because it is a fact about bundling rather than about wiring.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
