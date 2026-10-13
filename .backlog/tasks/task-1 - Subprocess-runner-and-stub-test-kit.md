---
id: TASK-1
title: Subprocess runner and stub test kit
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:09'
labels: []
milestone: m-0
dependencies: []
references:
  - subprocess
modified_files:
  - .gitignore
  - .groma/systems/harness/containers/agent-harness-cli/components/subprocess.md
  - bun.lock
  - package.json
  - results.jsonl
  - SOP-FEEDBACK.md
  - src/subprocess.ts
  - test/helpers/stubs.ts
  - test/subprocess.test.ts
priority: high
type: feature
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every child process the harness starts (agent CLIs, grader, check.py, --version, codex plugin installs) must run with a list-form argv, stdin from /dev/null, its own process group and a timeout that SIGKILLs the whole group while keeping the stdout captured so far (SPEC.md Non-functional). The test suite never runs a real CLI, so it also needs a reusable stub kit: stub `claude`/`opencode`/`codex`/`python3` executables first on PATH that record argv, cwd and env and replay an Appendix A stream with a given exit code. Builds groma component subprocess. Also brings package.json in line with the Stack section (exact devDependencies) and ships the empty results.jsonl with runs/ and campaign-logs/ git-ignored.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A child runs without a shell, with stdin from /dev/null, in its own process group, and its stdout, stderr and exit code are returned
- [x] #2 On timeout the whole process group is SIGKILLed, the stdout captured so far is kept and the result says it timed out; a test proves a sleeping descendant of a hanging stub is gone afterwards
- [x] #3 A missing executable is reported distinctly from a non-zero exit
- [x] #4 Test helpers provide stub executables that record argv, cwd and environment and print a given fixture stream with a given exit code and stderr
- [x] #5 package.json lists typescript 7.0.2 and @types/bun 1.4.2 as exact devDependencies; results.jsonl ships empty; runs/ and campaign-logs/ are git-ignored
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. package.json: move typescript to exact devDependencies, bun install; ship empty results.jsonl; git-ignore runs/ and campaign-logs/.
2. src/subprocess.ts: runProcess(argv, {cwd, env, timeoutMs}) resolving the executable by bare name on the child PATH (Bun.which), Bun.spawn with detached:true (own process group), stdin ignore (/dev/null), async capture of stdout/stderr; on timeout SIGKILL -pid and keep partial stdout; distinct notFound result.
3. test/helpers/stubs.ts: stub kit writing bun-shebang executables (absolute process.execPath) driven by a JSON rules file: record argv/cwd/env to calls.jsonl, print fixture stream or text, stderr, exit code, optional hang and sleeping descendant.
4. test/subprocess.test.ts: normal run, stdin is /dev/null, missing executable, non-zero exit with stderr, timeout keeps partial stdout and kills a sleeping descendant.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Evidence: `bunx tsc --noEmit && bun test` -> 4 pass, 0 fail (test/subprocess.test.ts: argv/stdout/stderr/exit capture, stdin /dev/null and own process group, missing executable, timeout group kill with sleeping descendant gone and partial stdout kept). Mutation check: with detached:false the group and timeout tests fail. `groma scan` matched 1, `groma accept subprocess`, rescan clean, `groma lint` no findings.
Product calls: after a normal exit the runner also SIGKILLs the rest of the group so no straggler outlives a trial; output draining is capped at 2 s after the group kill so a process that escaped the group cannot stall a run. Scaffold drift fixed: typescript moved from peerDependencies to an exact devDependency (spec Stack section).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/subprocess.ts (runProcess: bare-name lookup on the child PATH, no shell, stdin /dev/null, own process group, group SIGKILL on timeout keeping partial stdout, distinct notFound) and the stub CLI kit in test/helpers/stubs.ts used by every later test. package.json now pins typescript 7.0.2 and @types/bun 1.4.2 as devDependencies; empty results.jsonl shipped; runs/ and campaign-logs/ git-ignored. Verified by the gate (4 tests) and a mutation check.
<!-- SECTION:FINAL_SUMMARY:END -->
