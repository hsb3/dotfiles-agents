# obsidian-api-basics

Foundational patterns for building Obsidian plugins: the plugin lifecycle
(`onload`/`onunload`), settings persistence (`loadData`/`saveData`), command registration,
ribbon icons, vault file operations, the metadata cache, and the esbuild release setup. Use
it to get a new plugin's skeleton right the first time — correct lifecycle hooks, safe vault
access, and a distributable `main.js`/`manifest.json` — instead of reverse-engineering the
API from scratch.

## When it triggers

Use it when asked to create an Obsidian plugin, wire up the plugin lifecycle, add persisted
settings, register a command or ribbon icon, read or modify vault files, or work with
`onload`, `onunload`, `saveData`, or `loadData`.

## Install

```
claude plugin install obsidian-toolkit@dotfiles-agents
```

Ships in the `obsidian-toolkit` bundle. For chat sidebars, follow up with
`obsidian-chat-ui`.
