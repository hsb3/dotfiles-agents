# .claude/plugins — local workbench plugins (vendored, not distributed)

These three plugin directories are copies of Anthropic's official Claude Code plugins
(Apache-2.0, author "Anthropic" per each `.claude-plugin/plugin.json`), vendored
2026-07-22 as local workbench tooling for developing this repo's primitives:

- `plugin-dev` — plugin development toolkit
- `skill-creator` — skill creation + eval toolkit
- `mcp-server-dev` — MCP server development skills

They are wired through the file-based `workbench` marketplace
(`.claude-plugin/marketplace.json`) and enabled in `.claude/settings.json`
(`extraKnownMarketplaces` + `enabledPlugins`).

They are **not** part of the distributed marketplace this repo publishes. Per
`flow.yaml`, everything under `.claude/` is local dev tooling, never distributed.
`skill-creator` is additionally recorded by reference in `externals.yaml`.
