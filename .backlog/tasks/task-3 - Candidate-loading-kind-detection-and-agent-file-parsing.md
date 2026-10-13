---
id: TASK-3
title: 'Candidate loading: kind detection and agent file parsing'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:12'
labels: []
milestone: m-0
dependencies: []
references:
  - candidate
  - candidate-extender
modified_files:
  - .groma/systems/harness/containers/agent-harness-cli/components/candidate.md
  - src/candidate.ts
  - test/candidate.test.ts
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every command except --report starts from a candidate: a skill, a plugin or a set of agent files, or one flat agent .md file. Kind detection, the agent frontmatter rules and the exit-2 errors are specified in SPEC.md Candidates and cases, and opencode and codex injection depend on the parsed name, description, body, model and tools. Builds groma component candidate.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Kind is skill when SKILL.md is a file, plugin when .claude-plugin/plugin.json is a file (name defaulting to the dir base name, version to 0.0.0), agent when a top-level *.md other than README.md (case-insensitive) exists, checked in that order
- [x] #2 A flat .md file is copied into a fresh temp dir that becomes the candidate dir and is removed when the command exits
- [x] #3 Agent files sort by filename and parse frontmatter, name, description (else first body line cut to 200 chars) and body per the spec, stripping leading and trailing quote characters from field values
- [x] #4 Errors carry the spec messages: no such candidate path, not a directory or a flat agent .md file, not recognizable as skill / agent / plugin, duplicate agent name
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/candidate.ts: loadCandidate(name, path) -> Candidate {name, dir, kind, skillName, plugin {name, version}, agents, cleanup}; throws Error with the spec message on bad input (callers map loader errors to exit 2).
2. Flat .md file copied into a mkdtemp dir (keeping its file name), removed by cleanup() and on process exit.
3. Kind order skill > plugin > agent; agent files = top-level *.md other than README.md (case-insensitive), sorted by filename.
4. parseAgent(file, text): frontmatter regex, field rule with quote stripping, name/description/body rules, model and tools kept for opencode/codex.
5. test/candidate.test.ts covering each kind, defaults, flat file temp dir, the scout example, every error message.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 16 pass, 0 fail; test/candidate.test.ts covers kind order, plugin defaults, agent file selection/sorting, the spec scout example, quote stripping and fallbacks, flat-file temp dir and cleanup, and all four error messages. groma: matched 1, accepted candidate and candidate -> candidate-extender, lint clean.
Product calls: the `.md` extension test is case-sensitive while the README exclusion is case-insensitive (as the spec words it); an unreadable or non-object plugin.json still marks a plugin and its name/version take the defaults; the duplicate-name message names the two files by file name within the candidate dir; the loader throws plain Errors and its caller maps them to exit 2.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/candidate.ts: loadCandidate (kind detection skill > plugin > agent, flat .md copied to a temp dir removed on exit, spec error messages) and parseAgent (frontmatter, field, name, description, body, model, tools). Verified by 6 candidate tests in the gate.
<!-- SECTION:FINAL_SUMMARY:END -->
