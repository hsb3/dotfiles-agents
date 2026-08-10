---
id: TASK-049
title: Configure Codex as a repository coding agent
status: To Do
assignee: []
created_date: '2026-08-07 02:57'
updated_date: '2026-08-10 02:27'
labels:
  - harness
milestone: m-2
dependencies:
  - TASK-034
references:
  - AGENTS.md
  - CLAUDE.md
  - .claude/settings.json
  - .claude/hooks/no-main-checkout/hook.py
  - 'https://learn.chatgpt.com/docs/agent-configuration/agents-md'
  - 'https://learn.chatgpt.com/docs/config-file/config-basic'
  - 'https://learn.chatgpt.com/docs/hooks'
  - 'https://learn.chatgpt.com/docs/build-skills'
priority: medium
type: task
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Outcome

A developer can use Codex safely and predictably as a coding agent in this repository. This is repo-local developer configuration that sits alongside `.claude/` — not a new marketplace, catalog-distribution, or consumer-install target.

## Current state and evidence

- `AGENTS.md` is already Codex's native repository instruction file; `CLAUDE.md` just points to it, so no duplicate instruction doc is needed.
- No `.codex/` layer exists yet. `.claude/settings.json` currently holds the no-main-checkout PreToolUse hook plus Claude-specific marketplace, plugin, and worktree settings.
- `.claude/hooks/no-main-checkout/hook.py` is Codex PreToolUse-compatible (reads `tool_input.command`, emits the supported `permissionDecision` deny shape) but must be invoked via the repo root, not the Claude-project-directory env var.
- Codex project config lives in `.codex/config.toml` and `.codex/hooks.json`, loaded only after the project is trusted. Personal login, provider, notification, telemetry, and model defaults belong in `~/.codex`, not the repo.
- Any optional repo-local skills must use Codex's native `.agents/skills` discovery path as thin links to canonical sources, not copies.

## Scope

- Add and document the minimal checked-in `.codex` config: on-request approvals, workspace-write sandboxing, and any useful instruction-fallback behavior for the Claude-to-Codex transition.
- Register and verify the no-main-checkout guard for Codex.
- Document the developer workflow: login, trusting the repo config and hook, launching Codex, verifying loaded instructions and hooks.
- If a repo-local dev skill surface is needed, add only a thin `.agents/skills` assembly over existing sources, verified from both the repo root and a nested directory.

## Explicitly out of scope

- Publishing or packaging this catalog as a Codex plugin or marketplace entry.
- Adding `.codex-plugin` manifests, a Codex marketplace, a Codex consumer installer, or a codex target in `primitives-core.yaml`/distribution gates.
- Translating catalog agents or defining a harness-neutral agent profile (TASK-034's work).
- Moving or replacing the existing `.claude/` configuration.

## Constraints

- `AGENTS.md` stays the single source of repo rules; don't duplicate policy text into `.codex`.
- Preserve the branch/publish model: branch from `dev`, PR to `dev`, never touch `main` directly.
- No credentials or personal preferences in tracked files.
- Keep changes surgical; run the repo gate before handoff.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A trusted repository has a checked-in .codex/config.toml that uses on-request approval and workspace-write sandboxing without committing personal authentication, provider, notification, telemetry, or model preferences
- [ ] #2 Codex uses the existing root AGENTS.md as the repository instruction source, with no duplicate repository-policy text introduced in .codex
- [ ] #3 The no-main-checkout guard is registered as a Codex PreToolUse hook, blocks checkout, switch, and branch creation targeting main, and remains fail-open on malformed hook input
- [ ] #4 Developer documentation covers login, trusting the project configuration and hook, launching Codex from the repository, and verifying loaded instructions and hooks
- [ ] #5 If a repo-local .agents/skills surface is added, it contains only thin links to canonical sources, verified from both the repository root and a nested directory
- [ ] #6 The change adds no Codex marketplace or consumer distribution path, no .codex-plugin manifests, no catalog-target roster changes, and no agent-format translation
- [ ] #7 make ci passes
<!-- AC:END -->
