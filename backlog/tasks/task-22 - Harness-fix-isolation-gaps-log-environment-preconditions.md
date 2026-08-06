---
id: TASK-22
title: 'Harness: fix isolation gaps + log environment preconditions'
status: Done
assignee: []
created_date: '2026-08-04 00:44'
updated_date: '2026-08-06'
labels:
  - harness
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/172'
priority: medium
type: bug
ordinal: 1400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Work item for GH bug #172 (stays open as the report; close on fix). Symmetric runner isolation, log runtime self-installs as preconditions, --keep-workspaces for campaigns, resolve agent candidates without a staged temp dir. Source: W3 adversarial review 3.4-3.8.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both runners load only intended plugins
- [x] #2 --keep-workspaces preserves passing-trial workspaces
- [x] #3 make harness-eval resolves flat agent candidates
- [x] #4 GH #172 closed on merge
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-08-06 (lead-driven build, session-verified). (1) claude adapter now isolates symmetrically to opencode: env-scrub tuple + throwaway HOME/XDG/CLAUDE_CONFIG_DIR + `--setting-sources ""` + `--strict-mcp-config`; the old silent fallback to the operator's config on OSError is now a loud RuntimeError (adapters/claude.py). Live-proven: a real trial's init event showed zero user plugins/agents/hooks vs 7 plugins + user hooks in the host config. (2) New preconditions.py records cli_version/model/auth-env-names/self-install detections into both the ledger row and the run log header. (3) --keep-workspaces preserves passing-trial workspaces (filesystem-asserted tests). (4) Flat agent resolution moved in-package (candidate.py resolved_candidate_dir context manager); the Makefile's shell staging removed. Harness suite 102 -> 139 tests, make ci green. Deferred, tracked separately: scratch-ledger/--dry-run mode (eval runs append to the tracked results.jsonl), W3 item 3.7 (vision-grader assertion recording) was never in this task's Done-when.
<!-- SECTION:NOTES:END -->
