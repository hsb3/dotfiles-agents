---
name: publish-to-main
description: >
  Publish this repo's dev branch to main so consumers can install the updated plugins — the
  full promotion runbook: local gates (make ci), PR into dev, entry-gate floor green, merge,
  then the sanctioned publish workflow dispatch. Use when the user says "publish", "release
  the plugins", "promote dev to main", "make the skills available", or after merging a change
  that consumers should receive. main is publish-only (ADR 0007) — never commit, merge, or
  push to it directly.
---

# Publish dev → main

`dev` integrates; `main` is the published distributable surface consumers install from
(ADR 0007 governance; ADR 0008 payload). The publish workflow
(`.github/workflows/publish.yml`) **assembles a filtered tree** from `dev` — the Claude Code
marketplace shape at the root (per the lift map in the workflow; `dist/opencode/` publishes
as `opencode/` once the lane exists) — and commits it to `main` **with the previous main as
parent**: append-only, one commit per publish recording the source `dev` SHA and plugin
versions. The workbench (`harness/`, `evals/`, `_meta/`, `.claude/`, `.agents/`) never
publishes. A `pr-target-guard` workflow hard-fails any PR that targets `main`. Nothing lands
on `main` any other way — a change is "available" only after this runbook completes.

## 1. Land the change on dev

1. Branch off `dev` (`<type>/<short-name>`); source edits go in `primitives-core/` + the
   rosters (`primitives-core.yaml`, `plugins.yaml`) — **never hand-edit the generated
   artifacts** (`plugins/`, `.claude-plugin/marketplace.json`, `PLUGINS.md`); they are
   generated. Bump the affected plugin's `version:` in `plugins.yaml`.
2. Regenerate and gate locally — the same checks CI runs, so a red here is a red there:

   ```sh
   make build   # regenerate the marketplace artifacts from source
   make ci      # all gates: floor (identity · tests · provenance · hook-layout) + drift guards + flow
   ```

3. Commit, push, open the PR **into `dev`**:

   ```sh
   gh pr create --base dev --title "..." --body "..."
   ```

4. Watch CI to green (`gh pr checks <n> --watch`). Required checks are pinned **by job
   name** in dev's branch protection — renaming a CI job strands the PR on a check that
   never reports. Address review findings, re-push, re-check until clean.
5. Merge the PR into `dev`.

## 2. Promote dev to main

The publish workflow is manual (`workflow_dispatch`), typed-confirmation guarded, and
re-runs `make ci` on the dev tip before assembling:

```sh
gh workflow run publish.yml --ref dev -f confirm=publish
gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

If the surface didn't change (docs-only merge), the run succeeds with "nothing to publish".
The `reset=orphan` input restarts `main` with no parent — it was used once at the ADR 0008
cutover to drop the pre-0008 whole-tree snapshots from consumer clones; do not use it again
without an owner ruling (it rewrites main history).

## 3. Verify the publish

Not done until proven:

```sh
git fetch origin
git ls-tree --name-only origin/main          # distributable surface ONLY (no workbench dirs)
git rev-parse origin/dev:plugins origin/main:plugins   # SAME tree hash twice
git log --oneline -1 origin/main             # "publish: dev@<sha>" naming the tip you merged
```

Optionally confirm the consumer surface: the changed plugin's `version` appears in
`.claude-plugin/marketplace.json` at `origin/main`.

## Gotchas

- **`main` is an assembled subset, not a snapshot of dev.** Never diff `dev` against `main`
  whole-tree; compare the lifted paths' tree hashes (above).
- **Consumers pull from `main`.** Installed marketplaces pick up the change on their next
  plugin update — publishing here does not auto-update machines.
- **A local checkout sitting on `main` is disposable.** Work from `dev`-based branches;
  `main` history is append-only publish commits, useless for development.
- **The lift map lives in publish.yml.** Adding a new distributable artifact means adding it
  to the assemble step AND to `flow.yaml` — `make flow` fails a tree the DAG doesn't claim.
