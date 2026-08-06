---
name: plugin-enablement-needs-per-project-install
description: "An enabledPlugins:true entry does nothing unless the plugin is also installed for THIS projectPath; `claude plugin list` reports another project's record"
metadata: 
  node_type: memory
  type: reference
  originSessionId: b7761739-1e8a-43fe-86a0-f300de141b5a
  modified: 2026-08-06T06:19:54.552Z
---

Claude Code resolves plugins by **install record keyed on `projectPath`**, not by the
`enabledPlugins` map alone. Both must line up for a plugin's skills/agents to load:

1. an install record for this exact project path in
   `~/.claude/plugins/installed_plugins.json`, and
2. `enabledPlugins: {"<id>@<marketplace>": true}` in settings (`--scope local` →
   untracked `.claude/settings.local.json`; `project` → tracked `.claude/settings.json`).

Two traps found 2026-08-06 in this repo:

- **`claude plugin list` lies by omission.** It printed `foreman-kit@dotfiles-agents …
  Status: ✔ enabled` while the only install record was for `projectPath:
  /Users/henry/dotfiles`. Verify with the JSON, not the CLI:
  `python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));print(d['plugins']['<id>@<mk>'])"`
- **A lone `enabledPlugins` entry is inert.** `code-desk@dotfiles-agents: true` sat in
  `.claude/settings.local.json` with no install record for this path — its skills never
  loaded and nothing warned.

Fix: `claude plugin install <id>@<marketplace> --scope local` from inside the repo (adds
both the record and the enable flag). **Then restart the session** — skills and agents are
resolved at startup, so an in-flight session still cannot see them. `/reload-skills` does
**not** close the gap (verified 2026-08-06: both `foreman` and `foreman-kit:foreman` still
returned "Unknown skill" after a reload); it refreshes already-loaded sources, not
newly-installed plugins.

Prefer `--scope local` here: `.claude/settings.json` is tracked repo policy (it
deliberately disables the product plugins for dev sessions) and changing it is an
owner-sign-off matter, not a session convenience.
