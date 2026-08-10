---
name: plugin-enablement-needs-per-project-install
description: "An enabledPlugins entry is inert without an install record for THIS projectPath, and `claude plugin list` reports another project's record"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:02:16.095Z
---

Claude Code resolves plugins by **install record keyed on `projectPath`**, not by `enabledPlugins`
alone. Both must line up: a record for this exact path in
`~/.claude/plugins/installed_plugins.json`, **and** `enabledPlugins: {"<id>@<marketplace>": true}`
in settings.

Two traps found here 2026-08-06:

- **`claude plugin list` lies by omission** — it reported `Status: ✔ enabled` when the only
  install record was for `projectPath: /Users/henry/dotfiles`. Verify against the JSON, not the CLI.
- **A lone `enabledPlugins` entry does nothing.** `code-desk@dotfiles-agents: true` sat in
  `.claude/settings.local.json` with no record for this path; its skills never loaded, nothing warned.

Fix: `claude plugin install <id>@<marketplace> --scope local` from inside the repo (writes both),
**then restart the session** — skills and agents resolve at startup, and `/reload-skills` does not
close the gap (verified: still "Unknown skill" after a reload). Prefer `--scope local`;
`.claude/settings.json` is tracked repo policy that deliberately disables the product plugins for
dev sessions, and changing it is an owner call.
