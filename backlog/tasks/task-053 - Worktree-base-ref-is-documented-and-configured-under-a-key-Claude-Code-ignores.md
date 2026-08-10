---
id: TASK-053
title: Worktree base ref is documented and configured under a key Claude Code ignores
status: To Do
assignee: []
created_date: '2026-08-10 02:45'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/292'
priority: high
type: bug
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The setting that decides which ref a new worktree branches from is nested — `{"worktree": {"baseRef": "head"}}`. Three places in this repo write it flat as `"worktreeBaseRef": "head"`, which Claude Code silently ignores.

Measured against the binary at `~/.local/share/claude/versions/2.1.220`: `worktreeBaseRef` appears there only as the `/config` menu widget id. The handler reads `r?.worktree?.baseRef ?? "fresh"` and writes `_i("userSettings", {worktree: {baseRef: j}})`. The flat spelling is a UI label, never a settings key.

Consequences, in order of who is hurt:

1. Shipped docs are wrong. `primitives-core/hooks/worktree-isolation/README.md:124` and `plugins/atelier/README.md:148` both tell a consumer to set the flat key. A consumer follows the instruction, gets no error, and their isolated writers keep branching from `origin/<default-branch>`.
2. This repo was itself misconfigured. `.claude/settings.json` carried the flat key from `8ea83ba`, so worktree crews here have been branching from publish-only `main` the whole time the handoff claimed the fix was applied. Corrected in-session on 2026-08-09 along with the stale claims in `.claude/HANDOFF.md` and `.claude/memory/worktree-isolation.md`; the two published READMEs are what remains.

Both README edits change published bytes, so this needs the version bump on every plugin shipping the changed primitive — `make members` maps primitive to plugins.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Both READMEs document the nested `worktree.baseRef` key, with the value shown in a settings.json snippet a reader can paste without editing
- [ ] #2 No file in the repo names the flat `worktreeBaseRef` key except as deliberate history in backlog cards
- [ ] #3 Every plugin whose published bytes change carries a version bump in both its plugin.json and the root marketplace.json
- [ ] #4 The claim that the setting takes effect is verified against a real worktree creation, not against the settings file alone
<!-- AC:END -->
