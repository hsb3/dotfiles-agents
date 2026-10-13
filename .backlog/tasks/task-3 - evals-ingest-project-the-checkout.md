---
id: TASK-3
title: 'evals ingest: project the checkout'
status: To Do
assignee: []
created_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies:
  - TASK-2
references:
  - checkout
  - ingest
priority: high
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The extender inventory, the seeded doctrine and the mechanical-v1 assessments are what every report and the UI read. ingest projects a dotfiles-agents checkout and data/*.json into frameworks, framework_elements, sources, extenders, files, distributions, frontmatter_dimensions and assessments, then retires vanished extenders. Builds the checkout and ingest components; tests use a synthetic source tree with every case SPEC.md lists.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A synthetic tree with every listed case (each roster type, references/ and scripts/, block-sequence tools, folded description, hook with hook.py, config.json and .sh, an id in roster and externals, standalone and bundle plugins with hooks/_lib, commands/ and .mcp.json links) is projected exactly as The projection section states, including file roles, languages, distributions kind and members, frontmatter dimensions and mechanical verdicts and evidence
- [ ] #2 A second ingest of the unchanged tree plans 0 create / 0 update in every collection; a removed roster entry is listed as retired and comes back un-retired when it returns; a file that left the tree is deleted from files
- [ ] #3 `--parse-only` prints planned record counts and warnings without connecting; `--dry-run` writes nothing and prints `to retire` lines; missing roster, externals or marketplace exits 1
- [ ] #4 Nothing is written under --source-root; ingest never writes other assessors, job_coverage, relationships, eval_runs or eval_responses
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 bunx tsc --noEmit && bun run build:ui && bun test
- [ ] #2 Modified files and groma element refs recorded on the task
- [ ] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->
