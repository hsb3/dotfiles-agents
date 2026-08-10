---
id: TASK-048
title: >-
  Migrate the stranded .claude/agent-memory/ content into the tracked memory
  store
status: Done
assignee: []
created_date: '2026-08-07 02:37'
updated_date: '2026-08-10 02:05'
labels:
  - governance
milestone: m-2
dependencies: []
priority: low
type: chore
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
One-time migration, not a recurring sweep. The source that produced these files is closed: no agent definition carries a 'memory:' frontmatter key as of 2026-08-07 (removed from reviewer.md under TASK-037), and that key is what made the Claude Code runtime create the directory in the first place. So this is a finite pile to clear rather than an ongoing hazard.

WHAT IS STRANDED — three untracked, gitignored files under .claude/agent-memory/foreman-kit-reviewer/ (0 tracked; git ls-files returns nothing):
- MEMORY.md — a two-line index over the other two, in the same shape as the project store's own index.
- verify-live-tree-probe-cleanup.md — when a brief says 'prove nothing was written to the real repo', git status --porcelain alone is NOT sufficient evidence, because gitignored artifacts hide from it. Snapshot the filesystem too. Its own recorded provenance: probing config-custody against a worktree created logs/config-custody.jsonl on the exception path while porcelain stayed empty.
- verify-subprocess-env-harness.md — when a probe harness shells out to verify env-var behavior, assert the variable actually reached the child before trusting any verdict. Its recorded provenance: an env dict was built but subprocess.run was called without env=, so every probe 'passed' while silently exercising the fallback path.

WHY THIS IS A MIGRATION AND NOT A DELETION. Both files are real, transferable verification lessons with concrete provenance, and both are directly relevant to how this repo works — session 9's own reviewer used filesystem snapshotting rather than porcelain for exactly the reason the first file gives. They are already written in the project-memory format (name/description/metadata.type frontmatter, a Why, a How to apply). Deleting them loses knowledge that was earned by hitting the failure.

WHERE THEY GO. The tracked project store is .claude/memory/, indexed by .claude/memory/MEMORY.md — see the project-memory skill for the taxonomy and the promotion rule. Both files are type 'feedback' by that taxonomy (guidance on how work should be done, with the why included). Judge each on the store's own bar before promoting: a memory earns a place only if it is not derivable from the repo itself. If one does not clear that bar, drop it and say so rather than promoting both by default.

CLEANUP. After promotion, remove .claude/agent-memory/ entirely. Sweep the specific path only — never a whole-dir removal of the root .claude/, which holds HANDOFF.md and the tracked memory store (see project memory 'subagent-agent-memory-litter').
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the two content files is either promoted into .claude/memory/ as its own file with a MEMORY.md pointer line, or explicitly dropped with the reason recorded
- [x] #2 Any promoted memory follows the store's existing frontmatter shape and links related memories with [[name]] where one applies
- [x] #3 .claude/agent-memory/ no longer exists, removed by targeted path and not by a whole-dir sweep of .claude/
- [x] #4 The project memory 'subagent-agent-memory-litter' is re-checked and narrowed or retired, since the frontmatter key that caused the litter is gone and it currently reads as an ongoing hazard
- [x] #5 make ci is green
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Deviation from AC1: the two stranded lessons were promoted as ONE merged file, .claude/memory/probe-harness-hygiene.md, not two. Both are the same failure mode (a probe that reports success while testing nothing) and each was ~4 sentences of substance; two files would have been two index lines for one idea. Both provenance stories are preserved verbatim in the merged file.

AC3 was already satisfied on arrival — .claude/agent-memory/ does not exist (ls: No such file or directory); the untracked copies had been moved to .claude/memory/ in a prior session and were consumed by this merge.

AC4: subagent-agent-memory-litter.md rewritten 42 -> ~20 lines. It now leads with the root cause (the memory: frontmatter key) and states the source is closed, so it reads as a recognition guide rather than an ongoing hazard.

Done as part of a wider ponytail-ultra pass over AGENTS.md and .claude/memory (17 topic files -> 11, 493 -> 282 lines).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both stranded verification lessons now live in the tracked store as one merged memory, .claude/memory/probe-harness-hygiene.md, indexed from MEMORY.md; .claude/agent-memory/ is gone; subagent-agent-memory-litter.md was narrowed to a recognition guide now that the memory: frontmatter key that caused the litter is removed. Verified: index links all resolve (MEM-04 script check, no dangling entries, no unindexed files), .claude/agent-memory/ absent on disk, and make ci exits 0.
<!-- SECTION:FINAL_SUMMARY:END -->
