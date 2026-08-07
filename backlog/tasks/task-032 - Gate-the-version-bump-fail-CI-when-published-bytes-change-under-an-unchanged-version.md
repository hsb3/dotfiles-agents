---
id: TASK-032
title: >-
  Gate the version bump: fail CI when published bytes change under an unchanged
  version
status: Done
assignee: []
created_date: '2026-08-06 19:17'
updated_date: '2026-08-07 01:25'
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
- [x] #1 A gate fails when any plugin's dereferenced published bytes differ from origin/main while its version is unchanged
- [x] #2 The gate requires the bump in both plugin.json and the marketplace.json entry, and fails when the two disagree
- [x] #3 A dual-homed edit (one primitives-core skill body published under two plugins) is caught for every plugin that ships it, proven by a test
- [x] #4 A plugin present on dev but absent from origin/main does not trigger a false failure
- [x] #5 __pycache__ and *.pyc are excluded so a dereferenced walk produces no false positives
- [x] #6 Where the gate runs (make ci vs the CI job) is decided and written down, with the network-access reason stated
- [x] #7 Tests are stdlib-only with tempdir fixtures, and CI job names are unchanged
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
scripts/check_version_bump.py + tests/test_check_version_bump.py (40 tests), wired as one step at .github/workflows/ci.yml:44-45 inside the existing drift-guards job per the owner ruling. Eight comment lines above the step record the placement reasoning so the ruling survives without the card.

Red proof is against the LIVE repo, not a fixture: with published versions pinned to current (simulating 'the release forgot to bump'), the gate named all three genuinely-changed plugins with their unmoved versions and the specific changed files, exit 1. The green on the unmodified tree is also real rather than blind — atelier's bytes genuinely differ from origin/main and it passes only because its version already moved 0.8.0 to 0.9.0, verified by comparing blob hashes directly. Full lifecycle run against real git in a throwaway shallow clone: clean, edit a shared body, red, bump, green.

Every test proved capable of failing. Seven mutations of the finished script were run in memory and each behavior had tests that noticed: no pycache pruning (5 tests), one-direction comparison (3), no symlink dereferencing (17), first-offender-only reporting (2), new plugin treated as violation (1), version ignored (11), hard-fail instead of skip when offline (3).

Mechanism: a single 'git ls-tree -r -z' over the published tree, compared by git blob object id, with the local side hashing dereferenced bytes under the same 'blob <len>\0' rule — exact byte equality with one git call. Published plugin.json is read via cat-file only for plugins already showing a diff.

Three degradation paths, all deliberate and tested. Fetch fails with a cached ref: compares against the cache and warns, because a stale ref can only be BEHIND main, so it over-reports rather than under-reports, and a wrongly-demanded bump is harmless while a missed violation is not. No reachable ref at all: skips clean with exit 0 — proved with real git by planting a genuine violation first, so the test fails if the skip ever starts reporting. git missing or timing out (120s cap): same clean skip.

Two judgment calls: --depth=1 is passed only when the repo is ALREADY shallow, so a read-only gate never shallow-marks a contributor's complete clone (verified the test clone stays shallow=true rather than being deepened); and git's multi-line fetch stderr is collapsed to one 200-char line so the CI notice stays readable.

Deliberately not duplicated: check_catalog.py already holds plugin.json and marketplace.json versions in parity and runs in the SAME drift-guards job, so this gate takes plugin.json as the single version source. Together they satisfy AC#2 — a bump proven here must also appear in marketplace.json or the catalog guard goes red. Written into the docstring's 'Deliberately NOT covered' block along with version ordering, file modes, and plugins deleted on dev.

Grounded against publish.yml:47-57 to confirm no conflict: the lift is 'cp -RL plugins' then 'git add -A' under dev's .gitignore, landing dereferenced regular files at the same paths — exactly what the gate computes in process, which is why the prune lists mirror the ignore rules (cp -RL copies them, git add drops them, so leaving them in would produce phantom diffs).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:09
---
Owner ruling 2026-08-07: the gate runs as a STEP INSIDE THE EXISTING 'drift guards' CI job — not as a new CI job, and not in make ci.

Reasoning that produced the ruling: the check must diff each plugin's dereferenced bytes against origin/main, which needs network access, so it cannot live in make ci (offline by design, and a zero-install invariant). It also cannot be a new job: dev's branch protection pins required checks by job NAME, so introducing one would strand every open PR on a check that never reports. Riding the existing drift-guards job satisfies both constraints at once.

This resolves AC#6 ('where the gate runs is decided and written down, with the network-access reason stated'). The remaining ACs are mechanical and unblocked.
---

author: @claude
created: 2026-08-07 01:25
---
Follow-up for whoever owns scripts/: scripts/README.md has a 'Gate checkers (all in make ci)' table that this script does not fit — it is the first gate deliberately running OUTSIDE make ci, so it needs a short section stating the network reason rather than a table row that would make the heading a lie. Noted while building: that table is already incomplete (check_catalog.py and check_backlog_labels.py are both missing from it) and nothing enforces it, so the heading's 'all' is itself an unguarded claim.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CI now fails when a plugin's published bytes change under an unchanged version — the gap that let an edit to one dual-homed skill body change every plugin shipping it while CI stayed green and consumers kept serving the cached copy. Runs as a step in the existing drift-guards job per the owner ruling, which satisfies both hard constraints: the check needs network to reach origin/main so it cannot live in the offline make ci, and branch protection pins required checks by job name so it cannot be a new job. Verified by a red run against the live repo catching all three genuinely-changed plugins, a full clean-to-red-to-green lifecycle against real git, and seven mutations confirming each test can actually fail. Offline behavior is a clean skip, proved with a planted violation so a silent pass would fail the test.
<!-- SECTION:FINAL_SUMMARY:END -->
