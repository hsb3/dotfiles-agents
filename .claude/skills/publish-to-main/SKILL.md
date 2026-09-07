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
marketplace shape at the root (per the lift map in the workflow: the `plugins/` symlink
assemblies dereferenced, plus the root `marketplace.json`; opencode is an install-time
laydown since #230 and publishes no lane) — and commits it to `main` **with the previous main as
parent**: append-only, one commit per publish recording the source `dev` SHA and plugin
versions. The workbench (`harness/`, `evals/`, `docs/`, `.claude/`) never
publishes. A `pr-target-guard` workflow hard-fails any PR that targets `main`. Nothing lands
on `main` any other way — a change is "available" only after this runbook completes.

## 1. Land the change on dev

1. Branch off `dev` (`<type>/<short-name>`); source edits go in `primitives-core/`, the
   roster (`primitives-core.yaml`), and the symlink assemblies under `plugins/`
   (ADR 0017 — the assemblies ARE the marketplace; the `dist/` lanes were retired
   in #229). Bump the affected plugin's `version:` in BOTH
   `plugins/<id>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` —
   the version-keyed consumer cache makes the bump the release step.

   **Which digit, when a primitive is dual-homed** (decision-017). One skill body can be
   symlinked into several assemblies, so one edit changes the published bytes of every
   plugin that ships it. Run `make members` to derive which bundles a given primitive edit
   implicates — never bump on faith. Then grade each bundle **from the consumer's view of
   that bundle**, never from which plugin the work was filed under:

   - **owning bundle → minor** — it gained the capability;
   - **carrying bundle → patch** — the shared primitive improved, the bundle itself does
     nothing new;
   - **both minor** when the shared change is genuinely new capability in both;
   - **never "incidental" for a breaking change** — a break is a break in every bundle
     that ships it.

   `scripts/check_version_bump.py` proves only that the version MOVED; it has no semver
   semantics and is not being taught any, because a gate would have to infer capability to
   grade a digit. This rule is convention enforced by review, so its green says nothing
   about the digit.
2. Gate locally — the same checks CI runs, so a red here is a red there:

   ```sh
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
git log --oneline -1 origin/main             # "publish: dev@<sha>" naming the tip you merged
```

No tree-hash equality with dev exists — the workflow dereferences the symlink
assemblies, so published `plugins/` are regular files while dev's are symlinks
(the `dist/` lanes that once allowed a rev-parse compare retired in #229). Instead
confirm the consumer surface: the changed plugin's `version` appears in
`.claude-plugin/marketplace.json` at `origin/main`.

## Gotchas

- **A re-run hides itself, and its metadata lies about what shipped.** Re-running a publish
  dispatch from the Actions UI reuses the original run id AND its `created_at`, so
  `gh run list --workflow=publish.yml` still shows the ORIGINAL timestamp as the newest row —
  watching for a fresh run means watching for one that by design never appears (only
  `updated_at` and `run_attempt` reveal it). Worse, `head_sha` is fixed at dispatch while the
  re-run checks out `dev` fresh, so it names a commit that is NOT what got published. Observed
  2026-08-11: dispatched on `dev@ad24b47`, re-run 2h22m later, published `dev@eeb87f5`.
  **Audit a publish by the commit on `main`** (`publish: dev@<sha>`, append-only), never by the
  run. And because a re-run ships whatever `dev` is at execution time, dispatch-and-walk-away
  can publish a later tip than intended.
- **`main` is an assembled subset, not a snapshot of dev.** Never diff `dev` against `main`
  whole-tree; compare the lifted paths' tree hashes (above).
- **Consumers pull from `main`.** Installed marketplaces pick up the change on their next
  plugin update — publishing here does not auto-update machines.
- **A local checkout sitting on `main` is disposable.** Work from `dev`-based branches;
  `main` history is append-only publish commits, useless for development.
- **The lift map lives in publish.yml.** Adding a new distributable artifact means adding it
  to the assemble step AND to `flow.yaml` — `make flow` fails a tree the DAG doesn't claim.
