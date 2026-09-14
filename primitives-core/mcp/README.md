# mcp

Connection specs for MCP servers a plugin ships. Each file is one `mcpServers` object in
the `.mcp.json` shape, symlinked to `plugins/<id>/.mcp.json` by the assembly that carries
it — so installing the plugin registers the server, and a consuming repo never hand-writes
a `.mcp.json` to make the plugin's own tools appear.

Flat `.json` files, like `agents/` and `commands/`, so this file is the family README
(`README.md` is not discovered as a primitive).

## The rule that makes these shippable

**A spec is neutral or it does not belong here.** Every instance-specific value — host,
token, project, identity — arrives by `${ENV_VAR}` expansion from the consuming repo's own
`.claude/settings.local.json`, never as a literal. A spec carrying a real host ships one
person's deployment to everyone who installs the plugin, and a spec carrying a real token
ships a credential. Declare the variables the spec expands in the roster entry's
`requires:` (`hosted-mcp` or `local-mcp`, plus `env:<name>` per variable) so the dependency
is data rather than folklore.
