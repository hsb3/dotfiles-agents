# Distribution — plugins, marketplaces, install/enable mechanics

Skills, subagents, commands, hooks, and MCP servers are authored individually; **plugins** bundle
them and **marketplaces** distribute the plugins. This is how the surfaces reach another user.

## Plugin structure

A plugin is a directory (usually a repo) with a manifest and the surface subdirectories it ships.

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json           # manifest: name (the only required field), version, description, author
├── skills/<name>/SKILL.md    # bundled skills → /<plugin>:<name>
├── agents/<name>.md          # bundled subagents
├── commands/<name>.md        # bundled flat-file skills (legacy form; prefer skills/)
├── hooks/hooks.json          # bundled hooks: the same {"hooks": {...}} block as settings.json
├── hooks/<name>/             # handler scripts, referenced as ${CLAUDE_PLUGIN_ROOT}/hooks/<name>/...
├── .mcp.json                 # bundled MCP servers (optional)
└── .lsp.json                 # bundled LSP servers (optional)
```

A server bundled this way is namespaced by the plugin that carries it: its tools appear as
`mcp__plugin_<plugin>_<server>__<tool>`, not the bare `mcp__<server>__<tool>` a
project-level `.mcp.json` produces. Any permission rule or `allowed-tools` entry naming
such a tool has to use the long form, and the mismatch is silent — the rule simply never
matches.

```jsonc
// .claude-plugin/plugin.json
{
  "name": "my-plugin",         // required; kebab-case; the id users install and the /name: prefix
  "version": "0.1.0",          // optional semver; if set, users only update when you bump it
  "description": "What the bundle provides.",
  "author": { "name": "Author Name" }
}
```

The manifest's `name` is the install id and the skill namespace (`/my-plugin:hello`). `version`
is how an update is recognized — bump it whenever the shipped surfaces change (omit it and a
git source falls back to the commit SHA). Only `plugin.json` goes inside `.claude-plugin/`;
every surface directory sits at the plugin root. `author` is the **sanctioned place for identity**; the
surface *bodies* stay identity-neutral (personalization comes from config/data, not the body).

A plugin ships whichever surfaces it contains — a plugin can be a single skill, or a full set of
skills + agents + hooks + an MCP server. The surfaces inside a plugin use the same contracts as
their standalone forms (`surfaces.md`); the plugin just packages and versions them together.

## Marketplace registration

A **marketplace** is a directory/repo with a manifest listing the plugins it offers. One
marketplace serves many plugins; a user adds the marketplace once, then installs plugins by name.

```jsonc
// .claude-plugin/marketplace.json
{
  "name": "my-marketplace",
  "owner": { "name": "Owner Name" },
  "plugins": [
    {
      "name": "my-plugin",
      "source": "./plugins/my-plugin",   // relative path, or {source: github|url|git-subdir|npm|archive|command, ...}
      "description": "What the bundle provides.",
      "version": "0.1.0",
      "author": { "name": "Author Name" }
    }
  ]
}
```

Keep the marketplace entry's `name`/`version`/`description` consistent with the plugin's own
manifest. If a build step generates the marketplace from a source-of-truth manifest, regenerate it
rather than hand-editing — a generated distribution surface should be deterministic and
drift-checked, not maintained by hand.

## Install / enable mechanics

- **Add a marketplace:** `/plugin marketplace add <owner/repo | url | path>` — registers the
  source so its plugins are discoverable.
- **Install a plugin:** `/plugin install <plugin-name>@<marketplace-name>` — pulls that plugin's
  surfaces into the session.
- **Enable in settings (non-interactive):** `settings.json` `enabledPlugins` is an **object**,
  `{ "<plugin-name>@<marketplace-name>": true }`, and `extraKnownMarketplaces` registers the
  marketplace source; both apply only after each user trusts the folder.
- **Develop locally:** `claude --plugin-dir ./my-plugin` (repeatable), `/reload-plugins` after
  edits, `claude plugin validate ./my-plugin` before publishing.
- **Update:** bump the plugin `version` at the source; users re-pull to get the new surfaces.

## Standalone vs. bundled

The same skill body can ship two ways: inside a multi-surface **bundle**, or as a **one-skill
plugin** installed on its own. A skill is eligible to ship standalone only when it is
self-contained — no bundled companion agent, no MCP/hook requirement it cannot carry alone, and no
reference to a sibling skill by path. If a build system generates a one-skill wrapper plugin per
catalogued skill, keep the skill body the single source and let the wrapper be generated — never
fork the body per distribution form.

## Naming and namespacing

- A plugin's install id must be **unique within its marketplace**; a one-skill wrapper's plugin id
  is typically the skill id — keep it from clashing with any bundle id so
  `/plugin install <id>@<marketplace>` is unambiguous.
- Surface `name`s are lowercase-kebab; reserved marketplace names (`claude-plugins-official`,
  `anthropic-plugins`, …) are refused.
