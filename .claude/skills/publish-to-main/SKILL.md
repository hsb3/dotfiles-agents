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

`dev` integrates; `main` is the published marketplace surface consumers install from
(ADR 0007, `docs/decisions/0007-distribution-restructure-dev-main.md`). `main` is rebuilt
**exclusively** by the `publish` workflow, which force-pushes `dev`'s tree to `main`
(`.github/workflows/publish.yml`). A `pr-target-guard` workflow hard-fails any PR that
targets `main`. Nothing lands on `main` any other way — a change is "available" only after
this runbook completes.

## 1. Land the change on dev

1. Branch off `dev` (`<type>/<short-name>`); source edits go in `primitives-core/` + the
   rosters (`primitives-core.yaml`, `plugins.yaml`) — **never hand-edit `plugins/` or
   `.claude-plugin/marketplace.json`**; they are generated. Bump the affected plugin's
   `version:` in `plugins.yaml`.
2. Regenerate and gate locally — the same checks CI runs, so a red here is a red there:

   ```sh
   make build   # regenerate plugins/ + marketplace.json + PLUGINS.md from source
   make ci      # all gates: floor (identity · tests · provenance · hook-layout) + drift guards
   ```

3. Commit, push, open the PR **into `dev`**:

   ```sh
   gh pr create --base dev --title "..." --body "..."
   ```

4. Watch CI to green (`gh pr checks <n> --watch`). Required: the entry-gate floor and the
   drift guards. Address review findings, re-push, re-check until clean.
5. Merge the PR into `dev`.

## 2. Promote dev to main

The publish workflow is manual (`workflow_dispatch`) and typed-confirmation guarded:

```sh
gh workflow run publish.yml --ref dev -f confirm=publish
gh run watch $(gh run list --workflow=publish.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

## 3. Verify the publish

Not done until proven:

```sh
git fetch origin
git rev-parse origin/dev origin/main   # must print the SAME hash twice
```

Optionally confirm the consumer surface: the new/changed skill appears under `plugins/` at
that commit on `main`, and `.claude-plugin/marketplace.json` carries the bumped version.

## Gotchas

- **The publish is a whole-tree force push.** `main` becomes a byte-identical snapshot of
  `dev` — workbench dirs (`harness/`, `evals/`) included, and any main-only history is
  discarded. Publish only from a green, merged `dev` tip.
- **Consumers pull from `main`.** Installed marketplaces pick up the change on their next
  plugin update — publishing here does not auto-update machines.
- **A local checkout sitting on `main` goes stale silently** (its history may be rewritten by
  the next publish). Work from `dev`-based branches; treat local `main` as disposable.
