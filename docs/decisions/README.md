# Decisions (ADRs)

_One Architecture Decision Record per decision that shapes the build — what was decided,
why, and what it affects — so a choice made once isn't silently re-litigated._

Status: active

> **2026-08-11:** this directory is back at `docs/decisions/` — it lived under
> `backlog/decisions/` between 2026-08-06 and the Backlog.md retirement, and came home when
> the tracker moved to the Kaneo board. It holds both series side by side: the numbered ADR
> mirrors (`NNNN-*.md`, conventions below) and the rulings carried over from the backlog
> (`decision-N - *.md`, now plain files — the CLI that managed them is gone). One home for
> every decision; the ADR conventions below apply to the `NNNN` series only.

## Convention

- One file per decision: **`NNNN-kebab-title.md`** (zero-padded, sequential). Start from
  [`0000-template.md`](0000-template.md).
- **Append-only.** Never renumber or delete an ADR. Two distinct mechanisms, by what changed:
  - **Supersession** — the *decision* changed: write a new ADR, set the old one's status to
    `Superseded-by-NNNN`, leave its text for provenance.
  - **Correction (erratum)** — a *factual premise* was wrong (the decision may still stand):
    add a dated `> **Correction (YYYY-MM-DD):** …` callout at the top citing the evidence,
    strike the false sentence inline (`~~…~~`) with a pointer to the callout. Status reads
    `Accepted (corrected YYYY-MM-DD)`. A falsified claim is never left readable as current
    truth.
- **Status lifecycle:** `Proposed` → `Accepted` / `Rejected` / `Superseded-by-NNNN`.
  A `Proposed` ADR is a ballot — it states the recommendation and the open question.

## Log

These are mirrors carried into the clean-room rebuild from the pre-rebuild tree (now
preserved at `dev-legacy`) — kept **verbatim**, numbers and titles unchanged, per D7. The
numbering has intentional gaps: **0004** and **0005** existed pre-rebuild but are not carried
(below).

| ADR | Decision | Status | Raised by |
|---|---|---|---|
| [0001](0001-skills-over-commands.md) | Skills over commands: command intent folds into skills or retires | [Superseded by decision-010](decision-010%20-%20Commands-become-a-fourth-primitive-type.md) | CANON 3; backfill #40 |
| [0002](0002-hooks-as-script-plus-config.md) | Hooks as script + config, never inline in settings.json | Accepted | dotfiles convention + gate H4; backfill #40 |
| [0003](0003-externals-tracked-not-vendored.md) | Externals tracked-and-cloned (upstream + pinned ref), never vendored | Accepted; narrowed by [decision-6](decision-6%20-%20Externals-materialization-pinned-vendored-copy-not-clone-at-install.md) | CANON 11/16; backfill #40 |
| [0006](0006-meta-tracked-by-default.md) | `_meta/` tracked by default; targeted ignores only (operations/, caches, litter) | [Superseded by decision-8](decision-8%20-%20Repo-structure-future-state-backlog-absorbs-docs-hooks-removed.md) | #99 owner ruling 2026-07-13 |
| [0007](0007-distribution-restructure-dev-main.md) | Distribution restructure: `dev` integrates, `main` publishes — build on `dev`, never `main` | Accepted | DEV-31/#115; mirrors old-desk ADR 0014 |
| [0008](0008-vendor-dist-lanes-and-filtered-publish.md) | Vendor dist lanes under `dist/`, filtered append-only publish, flow.yaml as standing structural guard | Superseded-by-0017 (flow guard survives) | opencode lane planning; owner ruling 2026-07-22; restores old-desk 0014 §3 |
| [0015](0015-self-authored-primitives-only.md) | `primitives-core/` is self-authored only; third-party material by reference in `externals.yaml`, never vendored | Accepted; vendoring exception in [decision-6](decision-6%20-%20Externals-materialization-pinned-vendored-copy-not-clone-at-install.md) | mirrors the old-desk composition decision (0005·0007); backfilled 2026-07-22 per #203 |

The jump from 0008 to 0015 is the same verbatim-number preservation as the 0004/0005 gaps:
0015 is the old-desk number of the self-authored-only decision, carried in unchanged. The
intervening old-desk numbers (0009–0014) have no in-repo mirror.

### Deliberately not carried

- **0004** (`rules-and-memory-translation-policy`) — governed rules/auto-memory behavior
  *when translating to opencode*. The clean-room rebuild dropped the multi-vendor translation
  surface entirely (Claude-Code-only, charter G1); the decision has no target to bind.
- **0005** (`frontend-stack`) — `Proposed` status, conditional on a UI surface entering scope
  ("binds only when a deliverable actually has a UI"). No deliverable in the 0007 lineup has
  a UI surface, so it never bound and isn't carried. Revisit if that changes.

Both remain readable at their original path on `dev-legacy` if a future UI or cross-vendor
surface needs to re-open them.

## Native (decided in this repo, post-rebuild)

| ADR | Decision | Status | Raised by |
|---|---|---|---|
| [0016](0016-marketplace-lineup-recomposition.md) | Marketplace lineup recomposition — exec-desk folded into code-desk; 15 named plugins | Accepted | estate-restructure rebuild; owner ruling 2026-07-22 |
| [0017](0017-pointer-based-marketplace.md) | Pointer-based marketplace: symlink plugin assemblies, no tracked dist; READMEs travel with their skill | Accepted | backlog decision-2; owner ruling 2026-08-03; task-1 |

## Carried-over rulings (`decision-N`)

These IDs are a separate series, not aliases for the four-digit ADRs. Preserve the
original spelling (including unpadded 1–8); there is no decision-7 in this tree.
Accepted records can contain later amendments or partially implemented decisions:
read the dated notes before treating a historical mechanism as current guidance.

| ID | Decision | Status and later context |
|---|---|---|
| [decision-1](decision-1%20-%20Backlog.md-is-the-task-system-GitHub-issues-are-bug-reports-only.md) | Backlog.md is the task system; GitHub issues are bug reports only | Superseded by [decision-011](decision-011%20-%20Kaneo-board-is-the-task-system-Backlog.md-retired.md), then [decision-014](decision-014%20-%20Kata-board-is-the-task-system-Kaneo-retired.md) |
| [decision-2](decision-2%20-%20One-repo-serves-both-Claude-Code-and-opencode-via-pointer-based-distribution.md) | One repo serves both Claude Code and opencode via pointer-based distribution | Accepted; formalized by ADR 0017 |
| [decision-3](decision-3%20-%20functionform-asmbl-stays-parked-do-not-merge-do-not-archive.md) | functionform-asmbl stays parked: do not merge, do not archive | Accepted; historical parked-work ruling |
| [decision-4](decision-4%20-%20Publish-model-main-as-fast-forward-release-gate.md) | Publish model: main as fast-forward release gate | Accepted, amended 2026-08-06: filtered parented assembly; never merge into main |
| [decision-5](decision-5%20-%20evals-and-harness-extraction-both-but-deferred-dev-is-the-workbench.md) | evals/ and harness/ extraction: both, but deferred (dev is the workbench) | Accepted; extraction deferred |
| [decision-6](decision-6%20-%20Externals-materialization-pinned-vendored-copy-not-clone-at-install.md) | Externals materialization: pinned-vendored-copy, not clone-at-install | Accepted; narrow vendoring exception to ADRs 0003/0015; license review still required |
| [decision-8](decision-8%20-%20Repo-structure-future-state-backlog-absorbs-docs-hooks-removed.md) | Repo structure future-state — backlog absorbs docs/, _meta removed | Partly superseded by [decision-011](decision-011%20-%20Kaneo-board-is-the-task-system-Backlog.md-retired.md)/[decision-014](decision-014%20-%20Kata-board-is-the-task-system-Kaneo-retired.md): docs returned here and kata owns tasks |
| [decision-009](decision-009%20-%20Agent-profile-stays-Claude-Code-native-harness-neutrality-lives-in-a-declared-capability-matrix.md) | Agent profile stays Claude-Code-native; harness-neutrality lives in a declared capability matrix | Accepted; current Codex support is documented in the compatibility guide |
| [decision-010](decision-010%20-%20Commands-become-a-fourth-primitive-type.md) | Commands become a fourth primitive type | Accepted |
| [decision-011](decision-011%20-%20Kaneo-board-is-the-task-system-Backlog.md-retired.md) | Kaneo board is the task system; Backlog.md retired | Superseded by [decision-014](decision-014%20-%20Kata-board-is-the-task-system-Kaneo-retired.md); bug-intake rule survives |
| [decision-012](decision-012%20-%20starting-conditions-ships-in-code-desk-and-rig-builder-stays-a-distinct-agent.md) | starting-conditions ships in code-desk and rig-builder stays a distinct agent | Accepted |
| [decision-013](decision-013%20-%20Release-history-cuts-at-publish-time-with-no-tracked-CHANGELOG.md) | Release history cuts at publish time with no tracked CHANGELOG | Accepted |
| [decision-014](decision-014%20-%20Kata-board-is-the-task-system-Kaneo-retired.md) | kata board is the task system; Kaneo board retired | Accepted |
| [decision-015](decision-015%20-%20README-currency-is-derived-from-git-and-acknowledged-by-touching-the-README.md) | README currency is derived from git and acknowledged by touching the README | Accepted |
| [decision-016](decision-016%20-%20GitHub-label-set-is-a-closed-vocabulary-enforced-by-a-CI-gate.md) | GitHub label set is a closed vocabulary enforced by a CI gate | Accepted |
| [decision-017](decision-017%20-%20Dual-homed-primitives-bump-the-owning-bundle-minor-the-carrying-bundle-patch.md) | Dual-homed primitives bump the owning bundle minor and the carrying bundle patch | Accepted; [decision-020](decision-020%20-%20the-topical-plugin-owns-a-skill-and-solo-skills-drops-it.md) later removes dual membership |
| [decision-018](decision-018%20-%20comm-skills-unify-on-one-engine-and-the-vendored-pptx-base-retires.md) | comm skills unify on one engine and the vendored pptx base retires | Accepted; consolidation/retirement incomplete, see dated implementation note |
| [decision-019](decision-019%20-%20dev-focus-retires-and-the-scope-hammer-moves-into-planning-desk.md) | dev-focus retires and the scope hammer moves into planning-desk | Accepted |
| [decision-020](decision-020%20-%20the-topical-plugin-owns-a-skill-and-solo-skills-drops-it.md) | The topical plugin owns a skill and solo-skills drops it | Accepted; membership sweep implemented |
| [decision-021](decision-021%20-%20retired-primitives-are-sunset-by-decision-record-tag-and-deletion.md) | retired primitives are sunset by decision record, tag, and deletion (applied to kaneo) | Accepted; retirement history, not a current plugin inventory |
| [decision-022](decision-022%20-%20dependency-assumption-and-default-metadata-are-inline-token-lists-in-the-roster.md) | dependency, assumption and default metadata are inline token lists in the roster | Accepted; migration incomplete, see record |
| [decision-023](decision-023%20-%20kata-labels-are-the-triage-system-and-title-prefixes-are-not.md) | kata labels are the triage system and title prefixes are not | Accepted; board and GitHub vocabularies remain distinct |

Return to [current documentation](../README.md).
