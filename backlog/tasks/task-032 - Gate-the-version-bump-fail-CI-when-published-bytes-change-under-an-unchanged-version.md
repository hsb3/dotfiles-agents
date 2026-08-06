---
id: TASK-032
title: >-
  Gate the version bump: fail CI when published bytes change under an unchanged
  version
status: To Do
assignee: []
created_date: '2026-08-06 19:17'
updated_date: '2026-08-06 21:33'
labels:
  - gates
milestone: m-1
dependencies: []
references:
  - .github/workflows/publish.yml
  - scripts/check_catalog.py
  - CLAUDE.md
priority: high
type: feature
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Consumers cache plugins by version, so changed published content under an unchanged version never reaches an installed machine. The repo states this rule in CLAUDE.md and the handoff, and every release satisfies it **by hand**. No gate enforces it.

Found 2026-08-06 by an adversarial review during TASK-031. Two reproductions on the current tree:

- `grep -n "version" scripts/*.py` returns nothing. No guard reads a version field at all.
- Setting `plugins/dataviz/.claude-plugin/plugin.json` to `"version": "9.9.9"` while its `marketplace.json` entry stays `0.0.1` passes `make ci` clean. (TASK-031 adds a parity check for this half; the harder half below is still open.)

The expensive failure mode is the dual-homed one. Edit a skill body under `primitives-core/` and the published bytes of **every plugin that skill is a member of** change — a `pptx-themes` edit changes what ships under both `pptx-themes` and `code-desk`. Bump neither and `make ci` is green, the publish workflow runs, and no installed machine ever receives the fix. The failure is silent on both ends: nothing fails locally, and the consumer simply keeps the old version.

## What makes this tractable

`main` is a filtered parented assembly whose tip commit is `publish: dev@<sha>`, so the published delta is computable: dereference the symlink assemblies (`cp -RL plugins`) and diff against `git show origin/main:plugins/<id>/<path>` in both directions. A reviewer did exactly this by hand during TASK-031 and correctly identified the three changed plugins, so the procedure is known to work; it needs to become a script.

Prune `__pycache__`/`*.pyc` before comparing — they are a known false-positive source in a dereferenced walk.

## Scope

A gate that, for each plugin, compares its dereferenced published bytes against `origin/main` and requires a version bump in both `plugins/<id>/.claude-plugin/plugin.json` and the `marketplace.json` entry when they differ. Needs a decision on where it runs: it requires network access to `origin/main`, which the offline-friendly local gates currently do not, so it may belong in CI (the PR job) rather than in `make ci`.

## Constraints

- CI job names are pinned by branch protection — a new check must ride an existing job or the protection setting changes first.
- Stdlib-only, deterministic, no clocks or randomness.
- Must not fire on a first-release plugin absent from `main`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A gate fails when any plugin's dereferenced published bytes differ from origin/main while its version is unchanged
- [ ] #2 The gate requires the bump in both plugin.json and the marketplace.json entry, and fails when the two disagree
- [ ] #3 A dual-homed edit (one primitives-core skill body published under two plugins) is caught for every plugin that ships it, proven by a test
- [ ] #4 A plugin present on dev but absent from origin/main does not trigger a false failure
- [ ] #5 __pycache__ and *.pyc are excluded so a dereferenced walk produces no false positives
- [ ] #6 Where the gate runs (make ci vs the CI job) is decided and written down, with the network-access reason stated
- [ ] #7 Tests are stdlib-only with tempdir fixtures, and CI job names are unchanged
<!-- AC:END -->
