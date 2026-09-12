# Decisions

Each record explains a decision that shapes the repository.

## Convention

- One file per record: **`decisions-NNN-kebab-title.md`**.
- The filename number and frontmatter `id` (`decision-NNN`) match.
- Add a successor when a decision changes. Correct a false premise with a dated erratum.

## Log

| ID | Decision | Status | Legacy alias |
| --- | --- | --- | --- |
| [002](decisions-002-one-repo-serves-both-claude-code-and-opencode-via-pointer-based-distribution.md) | One repo serves both Claude Code and opencode via pointer-based distribution | Accepted | former decision-2 |
| [003](decisions-003-functionform-asmbl-stays-parked-do-not-merge-do-not-archive.md) | functionform-asmbl stays parked | Accepted |
| [004](decisions-004-publish-model-main-as-fast-forward-release-gate.md) | Publish model | Accepted |
| [005](decisions-005-evals-and-harness-extraction-both-but-deferred-dev-is-the-workbench.md) | evals and harness extraction | Accepted |
| [006](decisions-006-externals-materialization-pinned-vendored-copy-not-clone-at-install.md) | Externals materialization | Accepted |
| [007](decisions-007-distribution-restructure-dev-integrates-main-publishes.md) | Distribution restructure | Accepted |
| [008](decisions-008-repo-structure-future-state-backlog-absorbs-docs-hooks-removed.md) | Repo structure future state | Accepted; partly superseded by decision-014 |
| [009](decisions-009-agent-profile-stays-claude-code-native-harness-neutrality-lives-in-a-declared-capability-matrix.md) | Agent profile | Accepted |
| [010](decisions-010-commands-become-a-fourth-primitive-type.md) | Commands become a fourth primitive type | Accepted |
| [012](decisions-012-starting-conditions-ships-in-code-desk-and-rig-builder-stays-a-distinct-agent.md) | starting-conditions | Accepted |
| [013](decisions-013-release-history-cuts-at-publish-time-with-no-tracked-changelog.md) | Release history | Accepted |
| [014](decisions-014-kata-board-is-the-task-system-kaneo-retired.md) | kata board | Accepted | former decision-1 and decision-011 |
| [015](decisions-015-readme-currency-is-derived-from-git-and-acknowledged-by-touching-the-readme.md) | README currency | Accepted |
| [016](decisions-016-github-label-set-is-a-closed-vocabulary-enforced-by-a-ci-gate.md) | GitHub labels | Accepted |
| [017](decisions-017-dual-homed-primitives-bump-the-owning-bundle-minor-the-carrying-bundle-patch.md) | Dual-homed versioning | Accepted |
| [018](decisions-018-comm-skills-unify-on-one-engine-and-the-vendored-pptx-base-retires.md) | Comm skills | Accepted |
| [019](decisions-019-dev-focus-retires-and-the-scope-hammer-moves-into-planning-desk.md) | dev-focus | Accepted |
| [020](decisions-020-the-topical-plugin-owns-a-skill-and-solo-skills-drops-it.md) | Topical plugin ownership | Accepted |
| [021](decisions-021-retired-primitives-are-sunset-by-decision-record-tag-and-deletion.md) | Primitive retirement | Accepted |
| [022](decisions-022-dependency-assumption-and-default-metadata-are-inline-token-lists-in-the-roster.md) | Roster metadata | Accepted |
| [023](decisions-023-kata-labels-are-the-triage-system-and-title-prefixes-are-not.md) | kata labels | Accepted |
| [024](decisions-024-board-desk-owns-board-maintenance-and-references-kata.md) | Board-desk maintenance | Accepted |
| [025](decisions-025-hooks-as-script-plus-config-never-inline.md) | Hooks as script + config | Accepted | former ADR 0002 |
| [026](decisions-026-externals-are-tracked-and-cloned-never-vendored.md) | Externals tracked and cloned | Accepted; amended by decision-006 | former ADR 0003 |
| [027](decisions-027-vendor-dist-lanes-filtered-append-only-publish-and-flow-manifest.md) | Vendor dist lanes | Superseded by decision-030 | former ADR 0008 |
| [028](decisions-028-primitives-core-is-self-authored-only-externals-by-reference.md) | primitives-core provenance | Accepted; amended by decision-006 | former ADR 0015 |
| [029](decisions-029-marketplace-lineup-recomposition-exec-desk-folded-into-code-desk.md) | Marketplace lineup | Accepted | former ADR 0016 |
| [030](decisions-030-pointer-based-marketplace-symlink-plugin-assemblies-no-tracked-dist.md) | Pointer marketplace | Accepted | former ADR 0017 |
| [031](decisions-031-meta-is-tracked-by-default-targeted-ignores-only.md) | `_meta/` tracked by default | Accepted; this repo opts out via decision-008 | former ADR 0006 |
