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

## GitHub CLI (`gh`)

Neither container ships `gh`: the opencode backend (Debian bookworm) and the MCP bridge
(Alpine) are both built without it. `docker exec ocsbx-<name>-opencode-1 gh --version`
fails on a freshly created instance.

To use it anyway, install it by hand after `create` — this does **not** persist across
`destroy`/recreate, so it has to be repeated every time:

```
docker exec ocsbx-<name>-opencode-1 sh -c 'apt-get update && apt-get install -y gh'
```

**Do not follow that with `gh auth login`.** That logs the sandbox in as the operator's
own GitHub account, handing it a token scoped to everything the operator can reach —
every repo, every org. That inverts the isolation this skill provides: the isolation
protects the host from the instance, not the instance's *reach* from the instance.
`project-context.md`'s credential policy — nothing goes in, nothing needs to reach out
with a token — is not optional just because `gh` happens to be installed.

If an instance genuinely needs to call the GitHub API, scope what it gets instead of
handing over what the operator has. Two candidates, neither shipped by this skill:

- A fine-grained personal access token limited to one repository and to the
  `contents` + `pull-requests` permissions, exported as `GH_TOKEN` inside the container
  (`gh` reads that variable directly, with no `login` step).
- A GitHub App installation token scoped to one repository, minted per instance and
  short-lived.

Whether to mint scoped tokens per instance at all — and which of the two mechanisms —
is an open decision about how far this skill's isolation guarantee should extend.
Neither is built; this section only names the candidates so a future change starts
from the right two options instead of `gh auth login`.
