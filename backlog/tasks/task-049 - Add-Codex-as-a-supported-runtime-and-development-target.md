---
id: TASK-049
title: Configure Codex as a repository coding agent
status: To Do
assignee: []
created_date: '2026-08-07 02:57'
updated_date: '2026-08-07 02:58'
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

A developer can use Codex safely and predictably as a coding agent while working in this repository. The setup is repository-local developer configuration that sits alongside .claude/; it is not a new marketplace, catalog-distribution, or consumer-install target.

## Current state and evidence

- The root AGENTS.md is already the Codex-native repository instruction file. CLAUDE.md is a Claude pointer to AGENTS.md, so Codex does not need a duplicate instruction document.
- There is no checked-in .codex/ layer today. The tracked Claude settings in .claude/settings.json configure the no-main-checkout PreToolUse hook plus Claude-specific local marketplace, enabled-plugin, and worktree settings.
- The existing .claude/hooks/no-main-checkout/hook.py is compatible with Codex PreToolUse: it reads tool_input.command and emits the supported permissionDecision deny JSON shape. Codex registration must invoke it through the repository root rather than the Claude-project-directory environment variable.
- Codex project configuration belongs in .codex/config.toml and .codex/hooks.json and loads only after the project is trusted. Personal login, provider, notification, telemetry, and personal model defaults belong in ~/.codex, not in the repository.
- Codex can use the existing root AGENTS.md directly. Any optional repo-local skills must use its native .agents/skills discovery path and remain thin links to canonical sources rather than copied content.

## Scope

- Add and document the minimal checked-in .codex configuration required for this repository: on-request approvals, workspace-write sandboxing, and any instruction-fallback behavior that is useful during the Claude-to-Codex transition.
- Register and verify the no-main-checkout guard for Codex.
- Provide a short developer workflow for logging in, trusting the repository configuration and hook, launching Codex from the repository, and verifying active instructions and hooks.
- If a repo-local development skill surface is needed, add only a thin .agents/skills assembly over existing canonical sources and verify it from both the repository root and a nested directory.

## Explicitly out of scope

- Publishing, packaging, or installing this catalog as a Codex plugin or marketplace entry.
- Adding .codex-plugin manifests, a Codex marketplace, a Codex consumer installer, or a codex target to primitives-core.yaml and its distribution gates.
- Translating catalog agents or defining a harness-neutral agent profile; TASK-034 owns that work.
- Moving or replacing the existing .claude/ configuration.

## Constraints

- Keep the root AGENTS.md as the single source of repository rules; do not duplicate policy text into .codex.
- Preserve the existing branch and publish model: branch from dev, PR to dev, and never check out or commit directly to main.
- Keep credentials and personal preferences out of tracked files.
- Keep changes surgical and run the repository gate before handoff.

## References

- AGENTS.md
- CLAUDE.md
- .claude/settings.json
- .claude/hooks/no-main-checkout/hook.py
- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/config-file/config-basic
- https://learn.chatgpt.com/docs/hooks
- https://learn.chatgpt.com/docs/build-skills
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A trusted repository has a checked-in .codex/config.toml that uses on-request approval and workspace-write sandboxing without committing personal authentication, provider, notification, telemetry, or model preferences
- [ ] #2 Codex uses the existing root AGENTS.md as the repository instruction source, with no duplicate repository-policy text introduced in .codex
- [ ] #3 The no-main-checkout guard is registered as a Codex PreToolUse hook, blocks checkout, switch, and branch creation targeting main, and remains fail-open on malformed hook input
- [ ] #4 Developer documentation explains login, trusting the project configuration and hook, launching Codex from the repository, and verifying loaded instructions and hooks
- [ ] #5 If a repo-local .agents/skills surface is added, it contains only thin links to canonical sources and discovery is verified from both the repository root and a nested directory
- [ ] #6 The change does not add a Codex marketplace or consumer distribution path, .codex-plugin manifests, catalog-target roster changes, or an agent-format translation
- [ ] #7 make ci passes
<!-- AC:END -->
