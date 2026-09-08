# opencode-expertise

Expert reference knowledge of opencode — every extension surface (config, agents, skills,
commands, custom tools, plugins, MCP, rules), the TypeScript constraint, and the
Claude-Code-to-opencode translation mapping.

## When it triggers

Use it when configuring opencode, authoring or migrating an extender for it, designing an
opencode distribution target for a Claude Code skill collection, or answering how any
opencode extension surface works. Reference content, not an installer — it does not itself
translate or port anything.

## References

- `extension-surfaces.md` — the seven surfaces, numbered, each verified against the live docs.
- `configuration.md` — the config file, its precedence, and which keys are re-verified.
- `cc-to-opencode-mapping.md` — the Claude Code → opencode translation table.
- `distribution.md` — laying a bundle down as an opencode install.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
