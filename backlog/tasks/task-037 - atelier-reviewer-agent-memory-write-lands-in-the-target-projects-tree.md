---
id: TASK-037
title: 'atelier reviewer: agent-memory write lands in the target project''s tree'
status: Done
assignee: []
created_date: '2026-08-06 23:49'
updated_date: '2026-08-07 01:15'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/254'
priority: low
type: bug
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #254: a reviewer dispatched with the standard report-only brief ('you never edit files', 'no scratch files') finished its verification and then wrote .claude/agent-memory/foreman-kit-reviewer/ inside the target project's working tree, and self-reported the write as if it were compliant. In this repo .claude/agent-memory/ happens to be gitignored, so no harm; in a repo without that ignore line the write dirties git status mid-review and risks being swept into a later commit. Checked #260 (foreman-kit -> atelier rename + doctrine rewrite, config-custody + worker-context hooks): grepped worker-context, config-custody, and every agent body for 'agent-memory' -- zero hits, so this is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reviewer's agent-memory writes are pointed at a session/scratch location outside the target repo, or are opt-in per dispatch rather than automatic
- [ ] #2 If project-tree memory is kept intentionally, the plugin ships .claude/agent-memory/ gitignore guidance and the reviewer's self-description explicitly carves the memory write out of its 'report-only' contract
- [x] #3 Reviewer's stated contract and its actual filesystem behavior agree -- no undisclosed writes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause was FRONTMATTER, not agent behavior: primitives-core/agents/reviewer.md:5 carried 'memory: project' — the only agent in the repo with a memory: key.

Established from the shipped Claude Code runtime (~/.local/share/claude/versions/2.1.220): the schema is memory: enum([user, project, local]).optional(), described as the scope for auto-loading agent memory files, and the resolver maps 'project' to join(cwd, '.claude', 'agent-memory', agentType). The directory list is derived solely from the agent's memory field — no field, no directory.

Decisive live evidence: .claude/agent-memory/atelier-reviewer/ existed in this repo with mtime 2026-08-06 20:45:05 and ZERO entries. An empty directory cannot have been written by an agent, which proves the runtime mkdir's it from the frontmatter alone. That is why every brief saying 'report-only, no scratch files' failed to prevent it — no prose instruction could.

Fix: removed the memory: key. The enum has no 'off' value and the field is optional, so omission is the only correct setting. translation.yaml and gen_opencode.py reference no memory key, so the opencode target is unaffected. The plugins/atelier/agents/reviewer.md symlink picks the fix up with no second edit.

Contract text also tightened: the old 'ONE exception to report-only' paragraph is replaced with an explicit no-trace rule naming .claude/agent-memory/ by name, plus the owner's tmp-dir escape hatch for long reports (mktemp -d, resolving under TMPDIR or /tmp, never under the working tree). The description line now reads 'never edits, fixes, or writes into the repo under review' so the contract is visible at dispatch time rather than only in the body.

Honest limit, recorded rather than papered over: the enforceable half is now correct — with no memory: key the runtime cannot create anything. The remaining half is prose-governed only, since reviewer holds Bash and could still write if it ignores its body. Closing that would need a tool-permission or hook-level restriction, outside this card.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed at the root. The agent-memory directory was created by the Claude Code runtime from reviewer.md's 'memory: project' frontmatter key, not by the agent writing files — proven by an empty such directory found in this repo, and by the runtime's own schema and path resolver. Removing the key is the only off switch, since the enum has no 'off' value. AC#1 is met by disabling the write entirely rather than relocating it; AC#2 is moot because project-tree memory was not kept; AC#3 now holds — the stated contract and actual filesystem behavior agree, with the residual prose-only limit recorded explicitly. The owner's tmp-dir escape hatch for over-long reports is in the body.
<!-- SECTION:FINAL_SUMMARY:END -->
