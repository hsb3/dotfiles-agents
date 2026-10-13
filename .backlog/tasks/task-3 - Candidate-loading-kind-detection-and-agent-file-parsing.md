---
id: TASK-3
title: 'Candidate loading: kind detection and agent file parsing'
status: To Do
assignee: []
created_date: '2026-10-13 03:07'
labels: []
milestone: m-0
dependencies: []
references:
  - candidate
  - candidate-extender
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
- [ ] #1 Kind is skill when SKILL.md is a file, plugin when .claude-plugin/plugin.json is a file (name defaulting to the dir base name, version to 0.0.0), agent when a top-level *.md other than README.md (case-insensitive) exists, checked in that order
- [ ] #2 A flat .md file is copied into a fresh temp dir that becomes the candidate dir and is removed when the command exits
- [ ] #3 Agent files sort by filename and parse frontmatter, name, description (else first body line cut to 200 chars) and body per the spec, stripping leading and trailing quote characters from field values
- [ ] #4 Errors carry the spec messages: no such candidate path, not a directory or a flat agent .md file, not recognizable as skill / agent / plugin, duplicate agent name
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
