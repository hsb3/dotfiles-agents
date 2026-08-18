# Custom config and plugins

`--config <file>` at create time copies a file to `/root/.config/opencode/opencode.jsonc`
inside the instance, on a host bind mount. That means it is the one part of an instance you
can still edit from the host after creation — everything else lives in named volumes.

## What the config actually controls

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "small_model": "anthropic/claude-haiku-4-5",
  "enabled_providers": ["anthropic"],
  "mcp": {
    "docs": { "type": "remote", "url": "https://example.com/mcp" },
    "local-tool": { "type": "local", "command": ["node", "/workspace/tool.js"] }
  },
  "plugin": ["some-npm-plugin", "./plugins/local.ts"]
}
```

`model` and `small_model` take `provider/model`. `provider` lets you define or override a
provider outright, and `enabled_providers`/`disabled_providers` narrow what the instance
will consider.

**There is no `theme` key.** Theming belongs to the TUI, not the server config, so setting
it in an instance's `opencode.jsonc` does nothing. Do not offer it as a reason to pass
`--config`.

## MCP servers the instance itself connects to

The `mcp` block is the instance acting as an MCP *client* — not to be confused with the
bridge that exposes the instance to Claude Code. `local` servers run a command inside the
container, so the command has to exist in there; `remote` servers need outbound network
from the container.

## Plugins

`plugin` accepts npm package specifiers or local paths. Paths resolve relative to the
config file, so a plugin placed next to `opencode.jsonc` in the bind-mounted config
directory works and stays host-editable. Anything under `plugin/` or `plugins/` in a config
directory is auto-loaded with no declaration at all.

Two consequences worth stating before a user tries this:

**npm plugins need network at container start.** Every config directory gets an
unconditional npm install of `@opencode-ai/plugin` on boot, and declared npm plugins are
installed into that directory's `node_modules` the same way. Failures are logged and
non-fatal, so a network-isolated instance boots fine and simply has no plugin — the symptom
is silence, not an error.

**A plugin path inside `/workspace` is a one-shot.** The workspace is a named volume with
no host path, so such a plugin can only get there via `--seed` at create time or
`docker cp` afterward. Prefer the config directory.

## Changing config after creation

Edit the file on the host, then restart that instance's backend:

```
cd ~/.local/state/opencode-sandbox/<name>
COMPOSE_PROJECT_NAME=ocsbx-<name> docker compose -f compose.yml restart opencode
```

The CLI has no `restart` subcommand — this is the manual equivalent.
