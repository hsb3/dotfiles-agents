---
id: TASK-050
title: 'atelier: opt-in hook forcing worktree isolation for writer subagents'
status: Done
assignee: []
created_date: '2026-08-07 05:46'
updated_date: '2026-08-07 05:54'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: high
type: feature
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Atelier's builder and manager agents inherit the parent session's checkout, so a dispatched writer edits the same working tree the orchestrator is using. Observed live in another project: a subagent ran in the main checkout.

Claude Code supports two levers (both verified against 2.1.220 by live probe): agent-frontmatter 'isolation: worktree', and a PreToolUse hook on the Agent tool that rewrites tool_input via hookSpecificOutput.updatedInput.

Blanket forcing is wrong: a worktree is a clean checkout from a ref, so uncommitted and untracked files in the parent are invisible inside it (verified by probe - a worktree agent got 'No such file or directory' for a file present in the parent). Scout and reviewer must keep seeing the live working tree.

Owner ruling 2026-08-07: ship the hook, opt-in per project via .claude/atelier.local.md, scoped to writer agent types only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new primitives-core/hooks/worktree-isolation/ hook dir exists with hook.py + config.json + README.md, stdlib-only and Python 3.9 compatible
- [x] #2 The hook injects isolation:worktree via hookSpecificOutput.updatedInput for writer agent types (builder, manager, general-purpose) only
- [x] #3 Read-only and context-inheriting types (scout, reviewer, Explore, Plan, fork) are never rewritten, so they keep seeing uncommitted work
- [x] #4 The hook is inert when the activation file is absent or does not enable it, the dispatch already sets isolation, a cwd param is present, or the project is not a git repository
- [x] #5 The hook fails open on every error path and never blocks a dispatch
- [x] #6 Activation is documented in the delegation skill references/activation.md alongside the existing enforce/protected/handoff keys
- [x] #7 tests/test_worktree_isolation.py covers the rewrite, every inert path, and fail-open behavior; make ci passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built as primitives-core/hooks/worktree-isolation/ (hook.py + config.json + README.md), symlinked into plugins/atelier/hooks/, registered in hooks.json as a second PreToolUse entry with matcher 'Agent', and rostered in primitives-core.yaml.

Mechanism verified by live probe against Claude Code 2.1.220 before any code was written: PreToolUse fires with tool_name 'Agent' carrying the full dispatch, and hookSpecificOutput.updatedInput is honoured. Agent frontmatter also accepts an 'isolation' key (resolution order in the binary is explicit param ?? agentDefinition.isolation); the hook was chosen over frontmatter so activation stays per-project rather than shipping always-on to every consumer.

End-to-end proof with the shipped hook, three runs in a throwaway repo:
- general-purpose, no isolation param, isolate: writers armed -> ran in .claude/worktrees/agent-a11b867ac109effbe
- Explore, same conditions -> stayed in the parent checkout and read an uncommitted file
- general-purpose with the activation file removed -> stayed in the parent checkout

22 unit tests in tests/test_worktree_isolation.py; make ci exits 0 (413 tests).

Docs: activation.md in the delegation skill, plugins/atelier/README.md (component table, frontmatter example, key table), and the hook's own README. Root README catalog row bumped 7 -> 8 hooks, which the catalog gate caught.

Also surfaced while reading the binary, not fixed here: worktreeBaseRef ('fresh' default | 'head') controls the base ref for new worktrees. 'fresh' branches from origin/<default-branch>, which root-causes the recorded gotcha about worktree crews in this repo landing on a published main commit. Documented in both READMEs; changing this repo's setting is left as a separate decision.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ships worktree-isolation, an opt-in PreToolUse hook on the Agent tool. With 'isolate: writers' in .claude/atelier.local.md, a dispatch to builder, manager, or general-purpose is rewritten to carry isolation:worktree, so a writing worker gets its own checkout instead of sharing the strategist's working tree and index. scout, reviewer, Explore, Plan, and fork are never rewritten, because a worktree is a clean checkout of a ref and cannot see uncommitted work — isolating a reviewer would point it at a tree missing the diff it was sent to read. The hook rewrites, never denies, and fails open on every path.
<!-- SECTION:FINAL_SUMMARY:END -->
